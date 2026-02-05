"""Entrypoint and loop for standalone worker service."""

from __future__ import annotations

import asyncio
import logging
import signal

from worker.client import WorkerControlPlaneClient
from worker.config import WorkerSettings, get_worker_settings
from worker.runner import TaskRunner


logger = logging.getLogger(__name__)


class WorkerService:
    """Coordinates lifecycle for the worker loop."""

    def __init__(self, settings: WorkerSettings) -> None:
        self.settings = settings
        self.client = WorkerControlPlaneClient(
            base_url=settings.control_plane_url,
            worker_id=settings.worker_id,
            site=settings.site,
        )
        self.runner = TaskRunner()
        self._shutdown_event = asyncio.Event()

    def request_shutdown(self) -> None:
        """Trigger graceful shutdown."""

        self._shutdown_event.set()

    async def run(self) -> None:
        """Run worker loop until shutdown signal is received."""

        logger.info(
            "worker_starting",
            extra={
                "worker_id": self.settings.worker_id,
                "site": self.settings.site,
                "mode": self.settings.mode,
                "allow_cloud_llm": self.settings.allow_cloud_llm,
            },
        )

        await self.client.send_heartbeat()
        await self._shutdown_event.wait()

        logger.info("worker_stopping", extra={"worker_id": self.settings.worker_id})


async def run_worker(settings: WorkerSettings | None = None) -> None:
    """Run worker until interrupted or asked to stop."""

    resolved_settings = settings or get_worker_settings()
    service = WorkerService(settings=resolved_settings)
    loop = asyncio.get_running_loop()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, service.request_shutdown)
        except NotImplementedError:
            # Signal handlers are unavailable in some test platforms (e.g. Windows)
            pass

    try:
        await service.run()
    finally:
        await asyncio.sleep(0)


def main() -> None:
    """CLI entrypoint for worker runtime."""

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    asyncio.run(run_worker())


if __name__ == "__main__":
    main()
