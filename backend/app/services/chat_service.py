from typing import List, Dict, Any, Optional
import logging
from app.services.vector_service import vector_service
from app.models.schemas import ChatMessage, ChatResponse, QueryResult
import re
import asyncio

logger = logging.getLogger(__name__)

class ChatService:
    """Enhanced chat service with semantic search and context building"""
    
    def __init__(self):
        self.conversation_context = []
    
    async def process_message(self, message: ChatMessage) -> ChatResponse:
        """Process user message with semantic search and intelligent response"""
        try:
            start_time = asyncio.get_event_loop().time()
            
            user_query = message.message.strip()
            logger.info(f"Processing message: '{user_query}'")
            
            # Perform semantic search
            search_results = await vector_service.semantic_search(
                query=user_query,
                limit=5,
                filter_metadata=message.context_filter
            )
            
            # Build intelligent response
            response = await self._build_response(user_query, search_results)
            
            # Calculate processing time
            processing_time = asyncio.get_event_loop().time() - start_time
            
            # Prepare sources for frontend
            sources = []
            for result in search_results[:3]:  # Top 3 sources
                sources.append({
                    "content": result.content[:200] + "..." if len(result.content) > 200 else result.content,
                    "metadata": result.metadata,
                    "score": round(result.score, 3)
                })
            
            return ChatResponse(
                response=response,
                sources=sources,
                processing_time=round(processing_time, 2)
            )
            
        except Exception as e:
            logger.error(f"Chat processing failed: {e}")
            return ChatResponse(
                response="I encountered an error processing your request. Please try again.",
                sources=[],
                processing_time=0.0
            )
    
    async def _build_response(self, query: str, search_results: List[QueryResult]) -> str:
        """Build intelligent response from search results"""
        try:
            if not search_results:
                return self._get_fallback_response(query)
            
            # Analyze query intent
            query_lower = query.lower()
            
            # Time-based queries
            if any(word in query_lower for word in ['weekend', 'saturday', 'sunday', 'today', 'tomorrow', 'this week']):
                return await self._build_time_based_response(query, search_results)
            
            # Event-specific queries
            if any(word in query_lower for word in ['party', 'birthday', 'celebration']):
                return await self._build_event_response(query, search_results, 'party')
            
            if any(word in query_lower for word in ['football', 'practice', 'training', 'sport']):
                return await self._build_event_response(query, search_results, 'sports')
            
            # What/where/when questions
            if query_lower.startswith(('what', 'where', 'when', 'who', 'how')):
                return await self._build_factual_response(query, search_results)
            
            # General response
            return await self._build_general_response(query, search_results)
            
        except Exception as e:
            logger.error(f"Response building failed: {e}")
            return "I found some relevant information but had trouble organizing it. Please try rephrasing your question."
    
    async def _build_time_based_response(self, query: str, results: List[QueryResult]) -> str:
        """Build response for time-based queries"""
        events = []
        
        for result in results:
            if result.score > 0.3:  # Relevance threshold
                subject = result.metadata.get('subject', 'Event')
                content = result.content
                
                # Extract key information
                events.append({
                    'subject': subject,
                    'content': content,
                    'sender': result.metadata.get('sender', 'Unknown'),
                    'score': result.score
                })
        
        if events:
            response_parts = ["Based on your emails, here's what I found for your query:\n\n"]
            
            for i, event in enumerate(events[:3], 1):
                response_parts.append(f"{i}. **{event['subject']}**")
                
                # Extract key details
                content = event['content']
                time_match = re.search(r'(\d{1,2}[:\.]?\d{0,2}\s*(am|pm|AM|PM))', content)
                location_match = re.search(r'at ([^.\n]+)', content, re.IGNORECASE)
                
                if time_match:
                    response_parts.append(f"   • Time: {time_match.group(1)}")
                if location_match:
                    response_parts.append(f"   • Location: {location_match.group(1).strip()}")
                
                response_parts.append(f"   • From: {event['sender']}")
                response_parts.append("")
            
            return "\n".join(response_parts)
        
        return self._get_fallback_response(query)
    
    async def _build_event_response(self, query: str, results: List[QueryResult], event_type: str) -> str:
        """Build response for specific event types"""
        relevant_results = [r for r in results if r.score > 0.2]
        
        if relevant_results:
            best_result = relevant_results[0]
            content = best_result.content
            metadata = best_result.metadata
            
            response = f"**{metadata.get('subject', 'Event Details')}**\n\n"
            
            # Extract and highlight key information
            lines = content.split('\n')
            for line in lines:
                if line.strip() and not line.startswith('Subject:') and not line.startswith('From:'):
                    response += f"{line.strip()}\n"
            
            response += f"\n*Source: Email from {metadata.get('sender', 'Unknown')}*"
            
            # Add related information from other results
            if len(relevant_results) > 1:
                response += "\n\n**Related information:**\n"
                for result in relevant_results[1:2]:  # Add one more related item
                    response += f"• {result.metadata.get('subject', 'Related event')}\n"
            
            return response
        
        return self._get_fallback_response(query)
    
    async def _build_factual_response(self, query: str, results: List[QueryResult]) -> str:
        """Build response for factual questions"""
        if results and results[0].score > 0.3:
            best_result = results[0]
            
            # Extract relevant part of content
            content = best_result.content
            query_words = query.lower().split()
            
            # Find most relevant sentences
            sentences = content.split('.')
            relevant_sentences = []
            
            for sentence in sentences:
                sentence_lower = sentence.lower()
                if any(word in sentence_lower for word in query_words if len(word) > 2):
                    relevant_sentences.append(sentence.strip())
            
            if relevant_sentences:
                response = "Based on your emails:\n\n"
                response += ". ".join(relevant_sentences[:2]) + "."
                response += f"\n\n*From: {best_result.metadata.get('subject', 'Email')} by {best_result.metadata.get('sender', 'Unknown')}*"
                return response
        
        return self._get_fallback_response(query)
    
    async def _build_general_response(self, query: str, results: List[QueryResult]) -> str:
        """Build general response from search results"""
        if results:
            response = "I found some relevant information:\n\n"
            
            for i, result in enumerate(results[:2], 1):
                if result.score > 0.2:
                    response += f"{i}. **{result.metadata.get('subject', 'Information')}**\n"
                    
                    # Get first meaningful sentence
                    content = result.content.replace('Subject:', '').replace('From:', '').replace('Content:', '')
                    first_sentence = content.split('.')[0].strip()
                    if first_sentence:
                        response += f"   {first_sentence}.\n\n"
            
            return response
        
        return self._get_fallback_response(query)
    
    def _get_fallback_response(self, query: str) -> str:
        """Get fallback response when no good matches found"""
        responses = {
            'weekend': "I didn't find specific weekend plans in your emails. Try connecting more email accounts or syncing recent messages.",
            'party': "I don't see any party invitations in your current emails. Make sure your email accounts are connected and synced.",
            'football': "No football-related activities found in your emails. Check if your sports emails are being synced.",
            'default': f"I understand you're asking about '{query}'. Connect and sync your email accounts to get personalized answers based on your real messages!"
        }
        
        query_lower = query.lower()
        for key, response in responses.items():
            if key != 'default' and key in query_lower:
                return response
        
        return responses['default']

# Global chat service instance
chat_service = ChatService()