import os
import pickle
import base64
from typing import List, Optional, Dict, Any
import logging
from datetime import datetime

from app.connectors.base import BaseConnector
from app.models.schemas import EmailMessage, ConnectorStatus

logger = logging.getLogger(__name__)

class GmailConnector(BaseConnector):
    """Gmail connector - Demo version with sample data"""
    
    def __init__(self, connector_id: str, config: Dict[str, Any]):
        super().__init__(connector_id, config)
        self.service = None
        self.credentials = None
        
    async def connect(self) -> bool:
        """Connect to Gmail - Demo version"""
        try:
            self.status = ConnectorStatus.CONNECTING
            self.error_message = None
            
            # For demo purposes, simulate successful connection
            self.status = ConnectorStatus.CONNECTED
            logger.info(f"Gmail connector {self.connector_id} connected (demo mode)")
            return True
                
        except Exception as e:
            self.status = ConnectorStatus.ERROR
            self.error_message = str(e)
            logger.error(f"Gmail connection failed: {e}")
            return False
    
    async def disconnect(self) -> bool:
        """Disconnect from Gmail"""
        self.service = None
        self.credentials = None
        self.status = ConnectorStatus.DISCONNECTED
        return True
    
    async def test_connection(self) -> bool:
        """Test Gmail connection"""
        return self.status == ConnectorStatus.CONNECTED
    
    async def fetch_messages(self, limit: int = 100) -> List[EmailMessage]:
        """Fetch Gmail messages - Demo version with sample data"""
        try:
            if self.status != ConnectorStatus.CONNECTED:
                raise Exception("Not connected to Gmail")
            
            # Return sample messages for demo
            sample_messages = [
                EmailMessage(
                    id="gmail_demo_1",
                    subject="Emma's Birthday Party Invitation",
                    sender="sarah.jones@gmail.com",
                    recipients=["you@gmail.com"],
                    date=datetime.now(),
                    body="Hi! You're invited to Emma's 8th birthday party this Saturday at 2pm at Riverside Park. Please bring a gift - she loves unicorns! Let me know if you can make it. Sarah",
                    labels=["Important"],
                    connector_id=self.connector_id
                ),
                EmailMessage(
                    id="gmail_demo_2", 
                    subject="Football Practice - This Weekend",
                    sender="coach.mike@sportsclub.com",
                    recipients=["you@gmail.com"],
                    date=datetime.now(),
                    body="Reminder: Football practice is this Sunday at 10am at the sports center. Please bring football boots, water bottle, and team kit. We'll have warm-ups starting at 9:45am. Coach Mike",
                    labels=["Sports"],
                    connector_id=self.connector_id
                )
            ]
            
            logger.info(f"Fetched {len(sample_messages)} demo messages from Gmail")
            return sample_messages
            
        except Exception as e:
            logger.error(f"Failed to fetch Gmail messages: {e}")
            raise