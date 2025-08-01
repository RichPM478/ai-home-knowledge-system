from typing import List, Dict, Any, Optional
import logging
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
import uuid
from app.models.schemas import EmailMessage, QueryResult
import os

logger = logging.getLogger(__name__)

class VectorService:
    """Service for vector database operations with semantic search"""
    
    def __init__(self):
        self.client = None
        self.collection = None
        self.embedding_model = None
        self.is_initialized = False
        
    async def initialize(self):
        """Initialize ChromaDB and embedding model"""
        try:
            logger.info("Initializing vector database service...")
            
            # Initialize ChromaDB client
            chroma_path = os.getenv('CHROMA_DB_PATH', './data/chroma')
            os.makedirs(chroma_path, exist_ok=True)
            
            self.client = chromadb.PersistentClient(
                path=chroma_path,
                settings=Settings(anonymized_telemetry=False)
            )
            
            # Get or create collection for emails
            self.collection = self.client.get_or_create_collection(
                name="home_emails",
                metadata={"description": "Family email messages for semantic search"}
            )
            
            # Initialize embedding model (lightweight but effective)
            logger.info("Loading embedding model...")
            self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            
            self.is_initialized = True
            logger.info("Vector database service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize vector service: {e}")
            raise
    
    async def add_emails(self, emails: List[EmailMessage]) -> int:
        """Add emails to vector database with embeddings"""
        try:
            if not self.is_initialized:
                await self.initialize()
            
            if not emails:
                return 0
            
            logger.info(f"Adding {len(emails)} emails to vector database...")
            
            # Prepare documents and metadata
            documents = []
            metadatas = []
            ids = []
            
            for email in emails:
                # Create searchable text content
                content = f"Subject: {email.subject}\n\nFrom: {email.sender}\n\nContent: {email.body}"
                documents.append(content)
                
                # Store metadata
                metadatas.append({
                    "subject": email.subject,
                    "sender": email.sender,
                    "recipients": ",".join(email.recipients),
                    "date": email.date.isoformat(),
                    "connector_id": email.connector_id,
                    "labels": ",".join(email.labels),
                    "original_id": email.id
                })
                
                # Use email ID or generate unique ID
                ids.append(email.id)
            
            # Check for existing documents to avoid duplicates
            existing_ids = set()
            try:
                existing = self.collection.get(ids=ids)
                existing_ids = set(existing.get('ids', []))
            except:
                pass  # Collection might be empty
            
            # Filter out existing documents
            new_documents = []
            new_metadatas = []
            new_ids = []
            
            for doc, meta, doc_id in zip(documents, metadatas, ids):
                if doc_id not in existing_ids:
                    new_documents.append(doc)
                    new_metadatas.append(meta)
                    new_ids.append(doc_id)
            
            if new_documents:
                # Add new documents to collection
                self.collection.add(
                    documents=new_documents,
                    metadatas=new_metadatas,
                    ids=new_ids
                )
                
                logger.info(f"Added {len(new_documents)} new emails to vector database")
                return len(new_documents)
            else:
                logger.info("No new emails to add (all already exist)")
                return 0
                
        except Exception as e:
            logger.error(f"Failed to add emails to vector database: {e}")
            raise
    
    async def semantic_search(self, query: str, limit: int = 10, filter_metadata: Optional[Dict] = None) -> List[QueryResult]:
        """Perform semantic search on email content"""
        try:
            if not self.is_initialized:
                await self.initialize()
            
            logger.info(f"Performing semantic search for: '{query}'")
            
            # Build where clause for filtering
            where_clause = {}
            if filter_metadata:
                for key, value in filter_metadata.items():
                    if value:
                        where_clause[key] = value
            
            # Perform semantic search
            results = self.collection.query(
                query_texts=[query],
                n_results=limit,
                where=where_clause if where_clause else None,
                include=["documents", "metadatas", "distances"]
            )
            
            # Convert results to QueryResult objects
            query_results = []
            
            if results['documents'] and results['documents'][0]:
                documents = results['documents'][0]
                metadatas = results['metadatas'][0] if results['metadatas'] else []
                distances = results['distances'][0] if results['distances'] else []
                
                for i, doc in enumerate(documents):
                    # Convert distance to similarity score (lower distance = higher similarity)
                    distance = distances[i] if i < len(distances) else 1.0
                    score = max(0, 1 - distance)  # Convert to 0-1 similarity score
                    
                    metadata = metadatas[i] if i < len(metadatas) else {}
                    
                    query_results.append(QueryResult(
                        content=doc,
                        metadata=metadata,
                        score=score
                    ))
            
            logger.info(f"Found {len(query_results)} relevant results")
            return query_results
            
        except Exception as e:
            logger.error(f"Semantic search failed: {e}")
            raise
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get vector database statistics"""
        try:
            if not self.is_initialized:
                await self.initialize()
            
            count = self.collection.count()
            
            return {
                "total_emails": count,
                "collection_name": self.collection.name,
                "embedding_model": "all-MiniLM-L6-v2",
                "is_initialized": self.is_initialized
            }
            
        except Exception as e:
            logger.error(f"Failed to get vector DB stats: {e}")
            return {
                "total_emails": 0,
                "error": str(e),
                "is_initialized": False
            }

# Global vector service instance
vector_service = VectorService()