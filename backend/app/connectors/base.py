from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from app.models.schemas import EmailMessage, ConnectorStatus

class BaseConnector(ABC):
    """Base class for all data connectors"""
    
    def __init__(self, connector_id: str, config: Dict[str, Any]):
        self.connector_id = connector_id
        self.config = config
        self.status = ConnectorStatus.DISCONNECTED
        self.error_message = None
        
    @abstractmethod
    async def connect(self) -> bool:
        """Establish connection to data source"""
        pass
    
    @abstractmethod
    async def disconnect(self) -> bool:
        """Close connection to data source"""
        pass
    
    @abstractmethod
    async def fetch_messages(self, limit: int = 100) -> List[EmailMessage]:
        """Fetch messages from data source"""
        pass
    
    @abstractmethod
    async def test_connection(self) -> bool:
        """Test if connection is valid"""
        pass