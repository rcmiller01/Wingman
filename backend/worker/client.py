"""Control-plane client abstraction for worker communication."""

from __future__ import annotations

import logging
from dataclasses import dataclass


logger = logging.getLogger(__name__)


@dataclass(slots=True)
class HeartbeatResponse:
    """Stubbed response for heartbeat exchanges."""

    accepted: bool = True
    detail: str = "heartbeat accepted"


class WorkerControlPlaneClient:
    """Client used by worker to communicate with the control plane."""

    def __init__(self, base_url: str, worker_id: str, site: str) -> None:
        self.base_url = base_url
        self.worker_id = worker_id
        self.site = site

    async def send_heartbeat(self) -> HeartbeatResponse:
        """Send worker heartbeat.

        This is intentionally a stub for Ticket 6. Ticket 7 wires concrete API calls.
        """

        logger.info(
            "worker_heartbeat_stub",
            extra={
                "worker_id": self.worker_id,
                "site": self.site,
                "control_plane_url": self.base_url,
            },
        )
        return HeartbeatResponse()
