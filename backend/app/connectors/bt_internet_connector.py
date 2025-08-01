import imaplib
import email
from email.header import decode_header
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime

from app.connectors.base import BaseConnector
from app.models.schemas import EmailMessage, ConnectorStatus

logger = logging.getLogger(__name__)

class BTInternetConnector(BaseConnector):
    """BT Internet email connector using IMAP"""
    
    def __init__(self, connector_id: str, config: Dict[str, Any]):
        super().__init__(connector_id, config)
        self.imap = None
        
    async def connect(self) -> bool:
        """Connect to BT Internet email via IMAP"""
        try:
            self.status = ConnectorStatus.CONNECTING
            self.error_message = None
            
            # BT Internet IMAP settings
            imap_server = self.config.get('imap_server', 'mail.btinternet.com')
            port = self.config.get('port', 993)  # SSL port
            
            # Connect and login
            self.imap = imaplib.IMAP4_SSL(imap_server, port)
            self.imap.login(
                self.config['username'], 
                self.config['password']
            )
            
            self.status = ConnectorStatus.CONNECTED
            logger.info(f"BT Internet connector {self.connector_id} connected successfully")
            return True
            
        except Exception as e:
            self.status = ConnectorStatus.ERROR
            self.error_message = str(e)
            logger.error(f"BT Internet connection failed: {e}")
            return False
    
    async def disconnect(self) -> bool:
        """Disconnect from BT Internet email"""
        try:
            if self.imap:
                self.imap.logout()
                self.imap = None
            self.status = ConnectorStatus.DISCONNECTED
            return True
        except Exception as e:
            logger.error(f"BT Internet disconnect failed: {e}")
            return False
    
    async def test_connection(self) -> bool:
        """Test BT Internet connection"""
        try:
            if not self.imap:
                return False
            status, mailboxes = self.imap.list()
            return status == 'OK'
        except Exception as e:
            logger.error(f"BT Internet connection test failed: {e}")
            return False
    
    async def fetch_messages(self, limit: int = 100) -> List[EmailMessage]:
        """Fetch BT Internet email messages"""
        try:
            if not self.imap:
                raise Exception("Not connected to BT Internet")
            
            # Select mailbox
            mailbox = self.config.get('mailbox', 'INBOX')
            self.imap.select(mailbox)
            
            # Search for messages (most recent first)
            status, message_ids = self.imap.search(None, 'ALL')
            
            if status != 'OK':
                raise Exception("Failed to search messages")
            
            # Get message IDs (limit to most recent)
            msg_ids = message_ids[0].split()[-limit:]
            email_messages = []
            
            for msg_id in msg_ids:
                # Fetch message
                status, msg_data = self.imap.fetch(msg_id, '(RFC822)')
                
                if status == 'OK':
                    # Parse message
                    email_msg = self._parse_imap_message(msg_id.decode(), msg_data[0][1])
                    if email_msg:
                        email_messages.append(email_msg)
            
            logger.info(f"Fetched {len(email_messages)} messages from BT Internet")
            return email_messages
            
        except Exception as e:
            logger.error(f"Failed to fetch BT Internet messages: {e}")
            raise
    
    def _parse_imap_message(self, msg_id: str, raw_email: bytes) -> Optional[EmailMessage]:
        """Parse IMAP email message"""
        try:
            msg = email.message_from_bytes(raw_email)
            
            # Extract headers
            subject = self._decode_header(msg.get('Subject', 'No Subject'))
            sender = self._decode_header(msg.get('From', ''))
            recipients = self._decode_header(msg.get('To', '')).split(',')
            date_str = msg.get('Date', '')
            
            # Parse date
            try:
                msg_date = email.utils.parsedate_to_datetime(date_str)
            except:
                msg_date = datetime.now()
            
            # Extract body
            body = self._extract_imap_body(msg)
            
            return EmailMessage(
                id=f"bt_{msg_id}",
                subject=subject,
                sender=sender,
                recipients=[r.strip() for r in recipients],
                date=msg_date,
                body=body,
                labels=[],
                connector_id=self.connector_id
            )
            
        except Exception as e:
            logger.error(f"Failed to parse BT Internet message: {e}")
            return None
    
    def _decode_header(self, header: str) -> str:
        """Decode email header"""
        try:
            decoded = decode_header(header)
            return ''.join([
                part.decode(encoding or 'utf-8') if isinstance(part, bytes) else part
                for part, encoding in decoded
            ])
        except:
            return header or ""
    
    def _extract_imap_body(self, msg) -> str:
        """Extract text body from IMAP message"""
        try:
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        return part.get_payload(decode=True).decode('utf-8', errors='ignore')
            else:
                return msg.get_payload(decode=True).decode('utf-8', errors='ignore')
            return ""
        except Exception:
            return ""