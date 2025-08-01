from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import List, Dict, Any
import logging
import uuid
import asyncio
from datetime import datetime

from app.models.schemas import ConnectorType, ConnectorConfig, ConnectorInfo, ConnectorStatus
from app.connectors.gmail_connector import GmailConnector
from app.connectors.bt_internet_connector import BTInternetConnector
from app.services.vector_service import vector_service

router = APIRouter()
logger = logging.getLogger(__name__)

# In-memory connector storage and sync status
active_connectors: Dict[str, Any] = {}
sync_status: Dict[str, Dict[str, Any]] = {}

@router.get("/", response_model=List[ConnectorInfo])
async def list_connectors():
    """List all configured connectors with enhanced status"""
    connector_list = []
    
    for connector_id, connector_obj in active_connectors.items():
        # Get sync status
        sync_info = sync_status.get(connector_id, {})
        
        connector_list.append(ConnectorInfo(
            id=connector_id,
            type=ConnectorType(connector_obj.config.get('type', 'gmail')),
            name=connector_obj.config.get('name', connector_id),
            status=connector_obj.status,
            last_sync=sync_info.get('last_sync'),
            message_count=sync_info.get('message_count', 0),
            error_message=connector_obj.error_message
        ))
    
    return connector_list

@router.get("/{connector_id}/sync-status")
async def get_sync_status(connector_id: str):
    """Get detailed sync status for a connector"""
    if connector_id not in active_connectors:
        raise HTTPException(status_code=404, detail="Connector not found")
    
    sync_info = sync_status.get(connector_id, {})
    
    return {
        "connector_id": connector_id,
        "is_syncing": sync_info.get('is_syncing', False),
        "progress": sync_info.get('progress', 0),
        "status_message": sync_info.get('status_message', 'Ready'),
        "messages_processed": sync_info.get('messages_processed', 0),
        "total_messages": sync_info.get('total_messages', 0),
        "last_sync": sync_info.get('last_sync'),
        "sync_duration": sync_info.get('sync_duration', 0)
    }

@router.post("/", response_model=Dict[str, str])
async def create_connector(config: ConnectorConfig):
    """Create and configure a new connector"""
    try:
        connector_id = str(uuid.uuid4())[:8]
        
        # Add type to config
        config.config['type'] = config.type
        config.config['name'] = config.name
        
        # Create connector instance based on type
        if config.type == ConnectorType.GMAIL:
            connector = GmailConnector(connector_id, config.config)
        elif config.type == ConnectorType.BT_INTERNET:
            connector = BTInternetConnector(connector_id, config.config)
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported connector type: {config.type}")
        
        # Store connector
        active_connectors[connector_id] = connector
        
        # Initialize sync status
        sync_status[connector_id] = {
            'is_syncing': False,
            'progress': 0,
            'status_message': 'Created',
            'message_count': 0,
            'last_sync': None
        }
        
        logger.info(f"Created connector {connector_id} of type {config.type}")
        
        return {
            "connector_id": connector_id,
            "status": "created",
            "message": f"Connector {config.name} created successfully"
        }
        
    except Exception as e:
        logger.error(f"Failed to create connector: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{connector_id}/connect")
async def connect_connector(connector_id: str):
    """Connect a specific connector with status updates"""
    try:
        if connector_id not in active_connectors:
            raise HTTPException(status_code=404, detail="Connector not found")
        
        connector = active_connectors[connector_id]
        
        # Update status to connecting
        sync_status[connector_id]['status_message'] = 'Connecting...'
        
        success = await connector.connect()
        
        if success:
            sync_status[connector_id]['status_message'] = 'Connected'
            return {"status": "connected", "message": "Connector connected successfully"}
        else:
            sync_status[connector_id]['status_message'] = f'Connection failed: {connector.error_message}'
            raise HTTPException(status_code=500, detail=connector.error_message or "Connection failed")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Connection failed for {connector_id}: {e}")
        sync_status[connector_id]['status_message'] = f'Error: {str(e)}'
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{connector_id}/sync")
async def sync_connector(connector_id: str, background_tasks: BackgroundTasks):
    """Sync data from a connector with progress tracking"""
    try:
        if connector_id not in active_connectors:
            raise HTTPException(status_code=404, detail="Connector not found")
        
        connector = active_connectors[connector_id]
        
        if connector.status != ConnectorStatus.CONNECTED:
            raise HTTPException(status_code=400, detail="Connector not connected")
        
        # Check if already syncing
        if sync_status[connector_id].get('is_syncing', False):
            raise HTTPException(status_code=400, detail="Sync already in progress")
        
        # Start sync task
        background_tasks.add_task(enhanced_sync_connector_data, connector_id, connector)
        
        return {"status": "syncing", "message": "Enhanced sync started with vector embeddings"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Sync failed for {connector_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{connector_id}")
async def delete_connector(connector_id: str):
    """Delete a connector"""
    try:
        if connector_id not in active_connectors:
            raise HTTPException(status_code=404, detail="Connector not found")
        
        connector = active_connectors[connector_id]
        await connector.disconnect()
        
        # Clean up
        del active_connectors[connector_id]
        if connector_id in sync_status:
            del sync_status[connector_id]
        
        return {"status": "deleted", "message": "Connector deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete failed for {connector_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def enhanced_sync_connector_data(connector_id: str, connector):
    """Enhanced background sync with vector database storage and progress tracking"""
    try:
        logger.info(f"Starting enhanced sync for connector {connector_id}")
        start_time = asyncio.get_event_loop().time()
        
        # Update sync status
        sync_status[connector_id].update({
            'is_syncing': True,
            'progress': 0,
            'status_message': 'Fetching emails...',
            'messages_processed': 0,
            'total_messages': 0
        })
        
        # Step 1: Fetch messages
        sync_status[connector_id]['status_message'] = 'Fetching emails from server...'
        messages = await connector.fetch_messages(limit=100)
        
        if messages:
            sync_status[connector_id].update({
                'total_messages': len(messages),
                'progress': 25,
                'status_message': f'Processing {len(messages)} emails...'
            })
            
            # Step 2: Store in vector database
            sync_status[connector_id]['status_message'] = 'Creating embeddings and storing in vector database...'
            
            # Initialize vector service if needed
            if not vector_service.is_initialized:
                await vector_service.initialize()
            
            # Add emails to vector database
            new_count = await vector_service.add_emails(messages)
            
            sync_status[connector_id].update({
                'progress': 75,
                'status_message': 'Finalizing sync...',
                'messages_processed': new_count
            })
            
            # Step 3: Complete
            sync_duration = round(asyncio.get_event_loop().time() - start_time, 2)
            
            sync_status[connector_id].update({
                'is_syncing': False,
                'progress': 100,
                'status_message': f'Sync complete! Added {new_count} new emails to knowledge base.',
                'message_count': len(messages),
                'last_sync': datetime.now(),
                'sync_duration': sync_duration
            })
            
            logger.info(f"Enhanced sync completed for {connector_id}: {new_count} new emails processed in {sync_duration}s")
            
        else:
            sync_status[connector_id].update({
                'is_syncing': False,
                'progress': 100,
                'status_message': 'Sync complete - no new messages found',
                'last_sync': datetime.now()
            })
            
            logger.info(f"Sync completed for {connector_id}: no new messages")
            
    except Exception as e:
        logger.error(f"Enhanced sync task failed for {connector_id}: {e}")
        sync_status[connector_id].update({
            'is_syncing': False,
            'progress': 0,
            'status_message': f'Sync failed: {str(e)}'
        })