from pydantic import BaseModel, EmailStr
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

class ConnectorType(str, Enum):
    GMAIL = "gmail"
    BT_INTERNET = "bt_internet"
    CALENDAR = "calendar"
    WHATSAPP = "whatsapp"

class ConnectorStatus(str, Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"

class ConnectorConfig(BaseModel):
    type: ConnectorType
    name: str
    config: Dict[str, Any]
    enabled: bool = True

class ConnectorInfo(BaseModel):
    id: str
    type: ConnectorType
    name: str
    status: ConnectorStatus
    last_sync: Optional[datetime] = None
    message_count: int = 0
    error_message: Optional[str] = None

class EmailMessage(BaseModel):
    id: str
    subject: str
    sender: str
    recipients: List[str]
    date: datetime
    body: str
    labels: List[str] = []
    connector_id: str

class ChatMessage(BaseModel):
    message: str
    context_filter: Optional[Dict[str, Any]] = None

class ChatResponse(BaseModel):
    response: str
    sources: List[Dict[str, Any]]
    processing_time: float

class QueryResult(BaseModel):
    content: str
    metadata: Dict[str, Any]
    score: float