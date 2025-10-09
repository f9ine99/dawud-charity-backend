"""
WebSocket Connection Manager for Real-Time Updates
Manages WebSocket connections and broadcasts events to connected admin clients.
"""

from typing import Dict, Set
from fastapi import WebSocket
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections for real-time updates."""
    
    def __init__(self):
        # Store active connections: {admin_username: set of WebSocket connections}
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self.connection_count = 0
        
    async def connect(self, websocket: WebSocket, admin_username: str):
        """Accept and register a new WebSocket connection."""
        await websocket.accept()
        
        if admin_username not in self.active_connections:
            self.active_connections[admin_username] = set()
        
        self.active_connections[admin_username].add(websocket)
        self.connection_count += 1
        
        logger.info(f"Admin '{admin_username}' connected. Total connections: {self.connection_count}")
        
        # Send welcome message
        await self.send_personal_message(
            {
                "type": "connection_established",
                "message": "Real-time connection established",
                "timestamp": datetime.now().isoformat()
            },
            websocket
        )
    
    def disconnect(self, websocket: WebSocket, admin_username: str):
        """Remove a WebSocket connection."""
        if admin_username in self.active_connections:
            self.active_connections[admin_username].discard(websocket)
            self.connection_count -= 1
            
            # Clean up empty sets
            if not self.active_connections[admin_username]:
                del self.active_connections[admin_username]
            
            logger.info(f"Admin '{admin_username}' disconnected. Total connections: {self.connection_count}")
    
    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """Send a message to a specific WebSocket connection."""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")
    
    async def broadcast(self, message: dict, exclude_admin: str = None):
        """
        Broadcast a message to all connected admin clients.
        
        Args:
            message: The message dictionary to broadcast
            exclude_admin: Optional admin username to exclude from broadcast
        """
        disconnected = []
        
        for admin_username, connections in self.active_connections.items():
            # Skip if this admin should be excluded
            if exclude_admin and admin_username == exclude_admin:
                continue
            
            for connection in connections.copy():
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.error(f"Error broadcasting to {admin_username}: {e}")
                    disconnected.append((connection, admin_username))
        
        # Clean up disconnected clients
        for connection, admin_username in disconnected:
            self.disconnect(connection, admin_username)
    
    async def broadcast_new_donation(self, donation_data: dict):
        """Broadcast a new donation submission event."""
        message = {
            "type": "new_donation",
            "data": donation_data,
            "timestamp": datetime.now().isoformat()
        }
        await self.broadcast(message)
        logger.info(f"Broadcasted new donation: {donation_data.get('id')}")
    
    async def broadcast_donation_verified(self, donation_id: int, verified: bool, verified_by: str):
        """Broadcast a donation verification status change."""
        message = {
            "type": "donation_verified" if verified else "donation_unverified",
            "data": {
                "id": donation_id,
                "is_verified": verified,
                "verified_by": verified_by,
                "verified_at": datetime.now().isoformat()
            },
            "timestamp": datetime.now().isoformat()
        }
        await self.broadcast(message)
        logger.info(f"Broadcasted verification change for donation {donation_id}: {verified}")
    
    async def broadcast_stats_update(self, stats: dict):
        """Broadcast updated dashboard statistics."""
        message = {
            "type": "stats_update",
            "data": stats,
            "timestamp": datetime.now().isoformat()
        }
        await self.broadcast(message)
        logger.info("Broadcasted stats update")
    
    def get_connection_count(self) -> int:
        """Get the total number of active connections."""
        return self.connection_count
    
    def get_connected_admins(self) -> list:
        """Get list of currently connected admin usernames."""
        return list(self.active_connections.keys())


# Global connection manager instance
manager = ConnectionManager()

