"""Entrypoint and loop for standalone worker service."""

from __future__ import annotations

import asyncio
import logging
import signal
from pathlib import Path
from datetime import datetime, timezone

import httpx

from worker.client import WorkerControlPlaneClient
from worker.config import WorkerSettings, get_worker_settings
from worker.offline import OfflineBuffer, OfflineBufferConfig
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
        self.offline_buffer = OfflineBuffer(
            OfflineBufferConfig(
                directory=Path(settings.offline_dir),
                max_files=settings.offline_max_files,
                max_mb=settings.offline_max_mb,
                max_age_seconds=settings.offline_max_age_seconds,
            )
        )

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

        try:
            await self.client.register(capabilities=self._capabilities())
        except (httpx.HTTPError, OSError) as exc:
            logger.warning(
                "worker_registration_failed",
                extra={"worker_id": self.settings.worker_id, "error": str(exc)},
            )

        loop = asyncio.get_running_loop()
        while not self._shutdown_event.is_set():
            try:
                await self._replay_offline_buffer()

                now = loop.time()
                if now - self._last_heartbeat >= self.settings.heartbeat_interval_seconds:
                    try:
                        await self.client.send_heartbeat(capabilities=self._capabilities())
                        self._last_heartbeat = now
                    except (httpx.HTTPError, OSError) as exc:
                        logger.warning(
                            "worker_heartbeat_failed",
                            extra={"worker_id": self.settings.worker_id, "error": str(exc)},
                        )

                try:
                    task = await self.client.claim_task()
                except (httpx.HTTPError, OSError) as exc:
                    logger.warning(
                        "worker_claim_failed",
                        extra={"worker_id": self.settings.worker_id, "error": str(exc)},
                    )
                    task = None

                if task is not None:
                    try:
                        payload_type, payload = await self.runner.run(task)
                    except Exception as exc:  # noqa: BLE001
                        payload_type = "execution_result"
                        payload = {"success": False, "error": str(exc), "error_code": "EXECUTION_ERROR"}

                    envelope = {
                        "worker_id": self.settings.worker_id,
                        "site_name": self.settings.site,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "payload_type": payload_type,
                        "task_id": task.task_id,
                        "idempotency_key": task.idempotency_key,
                        "payload": payload,
                    }
                    await self._submit_or_buffer(envelope)
                    continue

            except Exception as exc:  # noqa: BLE001
                logger.error(
                    "worker_loop_error",
                    extra={"worker_id": self.settings.worker_id, "error": str(exc)},
                    exc_info=True,
                )

            await asyncio.sleep(self.settings.poll_interval_seconds)

        await self.client.close()
        logger.info("worker_stopping", extra={"worker_id": self.settings.worker_id})

    def _capabilities(self) -> dict:
        return {"tasks": ["collect_facts", "execute_script", "execute_action"], "offline_backlog_size": self.offline_buffer.backlog_size()}

    async def _submit_or_buffer(self, envelope: dict) -> None:
        try:
            await self.client.submit_envelope(envelope)
        except (httpx.HTTPError, OSError):
            self.offline_buffer.write(envelope)

    async def _replay_offline_buffer(self) -> None:
        pending = self.offline_buffer.list_pending()
        if not pending:
            return

        for path in pending[: self.settings.offline_replay_batch_size]:
            envelope = self.offline_buffer.load(path)
            try:
                await self.client.submit_envelope(envelope)
                self.offline_buffer.ack_delete(path)
            except (httpx.HTTPError, OSError):
                break
            await asyncio.sleep(self.settings.offline_replay_interval_seconds)


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
