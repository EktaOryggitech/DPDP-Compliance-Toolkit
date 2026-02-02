"""
DPDP GUI Compliance Scanner - WebSocket Manager

Manages real-time WebSocket connections for scan progress updates.
"""
import asyncio
import json
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Set
from fastapi import WebSocket, WebSocketDisconnect


@dataclass
class ScanProgress:
    """Scan progress update message."""
    scan_id: str
    status: str
    current_step: int
    total_steps: int
    percent: int
    message: str
    current_url: Optional[str] = None
    findings_count: int = 0
    pages_scanned: int = 0
    total_pages: int = 0
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    elapsed_seconds: int = 0
    estimated_remaining_seconds: Optional[int] = None
    timestamp: str = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict())


class ConnectionManager:
    """
    WebSocket connection manager for real-time updates.

    Features:
    - Multiple concurrent connections per scan
    - Automatic connection cleanup
    - Broadcasting to all connected clients
    - Individual scan subscriptions
    """

    def __init__(self):
        # Map of scan_id -> set of connected websockets
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        # Map of websocket -> scan_id for cleanup
        self.connection_scans: Dict[WebSocket, str] = {}
        # Lock for thread-safe operations
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, scan_id: str):
        """
        Accept and register a new WebSocket connection.

        Args:
            websocket: WebSocket connection
            scan_id: ID of the scan to subscribe to
        """
        await websocket.accept()

        async with self._lock:
            if scan_id not in self.active_connections:
                self.active_connections[scan_id] = set()

            self.active_connections[scan_id].add(websocket)
            self.connection_scans[websocket] = scan_id

        # Send initial connection confirmation
        await self.send_personal_message(
            websocket,
            {
                "type": "connected",
                "scan_id": scan_id,
                "message": "Connected to scan progress updates",
            },
        )

    async def disconnect(self, websocket: WebSocket):
        """
        Remove a WebSocket connection.

        Args:
            websocket: WebSocket connection to remove
        """
        async with self._lock:
            scan_id = self.connection_scans.get(websocket)
            if scan_id and scan_id in self.active_connections:
                self.active_connections[scan_id].discard(websocket)

                # Clean up empty scan entries
                if not self.active_connections[scan_id]:
                    del self.active_connections[scan_id]

            if websocket in self.connection_scans:
                del self.connection_scans[websocket]

    async def send_personal_message(
        self,
        websocket: WebSocket,
        message: Dict[str, Any],
    ):
        """
        Send a message to a specific connection.

        Args:
            websocket: Target WebSocket connection
            message: Message to send
        """
        try:
            await websocket.send_json(message)
        except Exception:
            await self.disconnect(websocket)

    async def broadcast_to_scan(self, scan_id: str, message: Dict[str, Any]):
        """
        Broadcast a message to all connections subscribed to a scan.

        Args:
            scan_id: Scan ID to broadcast to
            message: Message to broadcast
        """
        async with self._lock:
            connections = self.active_connections.get(scan_id, set()).copy()

        disconnected = []
        for connection in connections:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.append(connection)

        # Clean up disconnected clients
        for connection in disconnected:
            await self.disconnect(connection)

    async def send_progress(self, progress: ScanProgress):
        """
        Send a progress update to all subscribers of a scan.

        Args:
            progress: ScanProgress object with update details
        """
        message = {
            "type": "progress",
            **progress.to_dict(),
        }
        await self.broadcast_to_scan(progress.scan_id, message)

    async def send_finding(
        self,
        scan_id: str,
        finding: Dict[str, Any],
    ):
        """
        Send a new finding notification.

        Args:
            scan_id: Scan ID
            finding: Finding details
        """
        message = {
            "type": "finding",
            "scan_id": scan_id,
            "finding": finding,
            "timestamp": datetime.utcnow().isoformat(),
        }
        await self.broadcast_to_scan(scan_id, message)

    async def send_completion(
        self,
        scan_id: str,
        status: str,
        summary: Dict[str, Any],
    ):
        """
        Send scan completion notification.

        Args:
            scan_id: Scan ID
            status: Final status (completed, failed, cancelled)
            summary: Summary of scan results
        """
        message = {
            "type": "completed",
            "scan_id": scan_id,
            "status": status,
            "summary": summary,
            "timestamp": datetime.utcnow().isoformat(),
        }
        await self.broadcast_to_scan(scan_id, message)

    async def send_error(
        self,
        scan_id: str,
        error_message: str,
    ):
        """
        Send error notification.

        Args:
            scan_id: Scan ID
            error_message: Error description
        """
        message = {
            "type": "error",
            "scan_id": scan_id,
            "error": error_message,
            "timestamp": datetime.utcnow().isoformat(),
        }
        await self.broadcast_to_scan(scan_id, message)

    def get_connection_count(self, scan_id: str) -> int:
        """Get number of active connections for a scan."""
        return len(self.active_connections.get(scan_id, set()))

    def get_total_connections(self) -> int:
        """Get total number of active connections."""
        return sum(len(conns) for conns in self.active_connections.values())


# Global connection manager instance
manager = ConnectionManager()


class ScanProgressReporter:
    """
    Helper class for reporting scan progress from worker tasks.

    Uses Redis pub/sub for cross-process communication with the WebSocket server.
    """

    def __init__(self, scan_id: str, redis_url: str = None):
        self.scan_id = scan_id
        self.redis_url = redis_url
        self._redis = None
        self._total_steps = 100
        self._current_step = 0
        self._findings_count = 0
        self._pages_scanned = 0
        self._total_pages = 0
        self._critical_count = 0
        self._high_count = 0
        self._medium_count = 0
        self._low_count = 0
        self._started_at: Optional[datetime] = None

    async def connect(self):
        """Connect to Redis for pub/sub."""
        try:
            import redis.asyncio as aioredis
            self._redis = await aioredis.from_url(
                self.redis_url or "redis://localhost:6379/0"
            )
        except Exception as e:
            print(f"Could not connect to Redis for progress updates: {e}")
            self._redis = None

    async def disconnect(self):
        """Disconnect from Redis."""
        if self._redis:
            await self._redis.close()

    def set_total_steps(self, total: int):
        """Set the total number of steps."""
        self._total_steps = total

    def set_total_pages(self, total: int):
        """Set the total number of pages to scan."""
        self._total_pages = total

    def start_timer(self):
        """Start the scan timer."""
        self._started_at = datetime.utcnow()

    def increment_severity(self, severity: str):
        """Increment severity count."""
        if severity == "critical":
            self._critical_count += 1
        elif severity == "high":
            self._high_count += 1
        elif severity == "medium":
            self._medium_count += 1
        elif severity == "low":
            self._low_count += 1

    def _calculate_timing(self) -> tuple:
        """Calculate elapsed and estimated remaining time."""
        if not self._started_at:
            return 0, None

        elapsed = (datetime.utcnow() - self._started_at).total_seconds()
        elapsed_seconds = int(elapsed)

        # Estimate remaining time based on pages scanned
        estimated_remaining = None
        if self._pages_scanned > 0 and self._total_pages > 0:
            time_per_page = elapsed / self._pages_scanned
            remaining_pages = self._total_pages - self._pages_scanned
            estimated_remaining = int(time_per_page * remaining_pages)

        return elapsed_seconds, estimated_remaining

    async def update(
        self,
        step: int = None,
        message: str = "",
        current_url: str = None,
        increment_findings: int = 0,
        increment_pages: int = 0,
    ):
        """
        Send a progress update.

        Args:
            step: Current step number (or None to increment by 1)
            message: Status message
            current_url: URL/window currently being scanned
            increment_findings: Number of new findings to add to count
            increment_pages: Number of new pages to add to count
        """
        if step is not None:
            self._current_step = step
        else:
            self._current_step += 1

        self._findings_count += increment_findings
        self._pages_scanned += increment_pages

        percent = int((self._current_step / self._total_steps) * 100)
        elapsed_seconds, estimated_remaining = self._calculate_timing()

        progress = ScanProgress(
            scan_id=self.scan_id,
            status="running",
            current_step=self._current_step,
            total_steps=self._total_steps,
            percent=min(percent, 100),
            message=message,
            current_url=current_url,
            findings_count=self._findings_count,
            pages_scanned=self._pages_scanned,
            total_pages=self._total_pages,
            critical_count=self._critical_count,
            high_count=self._high_count,
            medium_count=self._medium_count,
            low_count=self._low_count,
            elapsed_seconds=elapsed_seconds,
            estimated_remaining_seconds=estimated_remaining,
        )

        await self._publish(progress)

    async def report_finding(self, finding: Dict[str, Any]):
        """Report a new finding."""
        if self._redis:
            message = json.dumps({
                "type": "finding",
                "scan_id": self.scan_id,
                "finding": finding,
            })
            await self._redis.publish(f"scan:{self.scan_id}", message)

    async def complete(self, status: str, summary: Dict[str, Any]):
        """Report scan completion."""
        if self._redis:
            message = json.dumps({
                "type": "completed",
                "scan_id": self.scan_id,
                "status": status,
                "summary": summary,
            })
            await self._redis.publish(f"scan:{self.scan_id}", message)

    async def error(self, error_message: str):
        """Report an error."""
        if self._redis:
            message = json.dumps({
                "type": "error",
                "scan_id": self.scan_id,
                "error": error_message,
            })
            await self._redis.publish(f"scan:{self.scan_id}", message)

    async def _publish(self, progress: ScanProgress):
        """Publish progress to Redis channel."""
        if self._redis:
            message = json.dumps({
                "type": "progress",
                **progress.to_dict(),
            })
            await self._redis.publish(f"scan:{self.scan_id}", message)


async def websocket_subscriber(scan_id: str, redis_url: str):
    """
    Subscribe to Redis channel and forward messages to WebSocket clients.

    This should be run as a background task for each active scan.
    """
    try:
        import redis.asyncio as aioredis

        redis = await aioredis.from_url(redis_url)
        pubsub = redis.pubsub()
        await pubsub.subscribe(f"scan:{scan_id}")

        async for message in pubsub.listen():
            if message["type"] == "message":
                try:
                    data = json.loads(message["data"])
                    await manager.broadcast_to_scan(scan_id, data)
                except json.JSONDecodeError:
                    pass

    except Exception as e:
        print(f"WebSocket subscriber error for scan {scan_id}: {e}")
    finally:
        await pubsub.unsubscribe(f"scan:{scan_id}")
        await redis.close()
