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
        self._last_heartbeat: float = 0.0

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

        await self.client.register()

        loop = asyncio.get_running_loop()
        while not self._shutdown_event.is_set():
            now = loop.time()
            if now - self._last_heartbeat >= self.settings.heartbeat_interval_seconds:
                await self.client.send_heartbeat()
                self._last_heartbeat = now

            task = await self.client.claim_task()
            if task is not None:
                try:
                    payload_type, payload = await self.runner.run(task)
                except Exception as exc:  # noqa: BLE001
                    payload_type = "execution_result"
                    payload = {"success": False, "error": str(exc)}
                await self.client.submit_result(task=task, payload_type=payload_type, payload=payload)
                continue

            await asyncio.sleep(self.settings.poll_interval_seconds)

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
            pass

    await service.run()


def main() -> None:
    """CLI entrypoint for worker runtime."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    asyncio.run(run_worker())


if __name__ == "__main__":
    main()
