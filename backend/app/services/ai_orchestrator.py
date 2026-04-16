"""AI Tagging orchestrator — runs CLIP tagging on a Harvester job's images.

Reads image paths from assets table, runs ai_tagger, publishes SSE events,
persists results as JSON in the AI job's output_dir.
"""
import asyncio
import json
from pathlib import Path

from app.config import settings
from app.db.session import AsyncSessionLocal
from app.models.job import JobStatus
from app.repositories.asset_repository import AssetRepository
from app.repositories.job_repository import JobRepository
from app.services.ai_tagger import tag_images_async
from app.services.event_bus import event_bus


class AIOrchestrator:
    async def run(
        self,
        job_id: str,
        stop_event: asyncio.Event,
        harvester_job_id: str,
        labels: list[str],
    ) -> None:
        async with AsyncSessionLocal() as session:
            job_repo = JobRepository(session)
            asset_repo = AssetRepository(session)
            await job_repo.update_status(job_id, JobStatus.RUNNING)
            await session.commit()
            await event_bus.publish(job_id, {"type": "status", "status": "running"})

            try:
                # Get images from harvester job — check content_type OR extension
                _IMG_EXTS = {"jpg", "jpeg", "png", "webp", "gif", "bmp", "svg"}
                _IMG_MIMES = {"image/jpeg", "image/png", "image/webp", "image/gif", "image/bmp"}

                assets = await asset_repo.list_for_job(harvester_job_id, limit=10000)
                image_paths: list[Path] = []
                for a in assets:
                    if not a.local_path or not Path(a.local_path).exists():
                        continue
                    ext = a.local_path.lower().rsplit(".", 1)[-1] if "." in a.local_path else ""
                    mime = (a.content_type or "").split(";")[0].strip().lower()
                    if ext in _IMG_EXTS or mime in _IMG_MIMES:
                        image_paths.append(Path(a.local_path))

                if not image_paths:
                    await job_repo.update_status(job_id, JobStatus.ERROR, "No images found in harvester job")
                    await session.commit()
                    await event_bus.publish(job_id, {"type": "error", "message": "No images found"})
                    return

                await event_bus.publish(job_id, {
                    "type": "log",
                    "message": f"Loading CLIP model (first run downloads ~350 MB)…",
                })

                total = len(image_paths)
                loop = asyncio.get_running_loop()

                def on_progress(done: int, total: int, filename: str, tag: str, score: float):
                    if stop_event.is_set():
                        raise InterruptedError("cancelled")
                    asyncio.run_coroutine_threadsafe(
                        event_bus.publish(job_id, {
                            "type": "progress",
                            "done": done,
                            "total": total,
                            "filename": filename,
                            "top_tag": tag,
                            "top_score": score,
                        }),
                        loop,
                    )

                results = await tag_images_async(image_paths, labels, on_progress)

                # Save results as JSON
                out_dir = settings.data_dir / "ai_results"
                out_dir.mkdir(parents=True, exist_ok=True)
                results_path = out_dir / f"{job_id}.json"
                results_path.write_text(json.dumps({
                    "job_id": job_id,
                    "harvester_job_id": harvester_job_id,
                    "labels": labels,
                    "total_images": total,
                    "tagged": len(results),
                    "results": results,
                }, indent=2))

                stats = {
                    "total_images": total,
                    "tagged": len(results),
                    "labels": labels,
                }
                await job_repo.update_stats(job_id, stats)
                job = await job_repo.find_by_id(job_id)
                if job:
                    job.output_dir = str(results_path)

                if stop_event.is_set():
                    await job_repo.update_status(job_id, JobStatus.STOPPED)
                    await session.commit()
                    await event_bus.publish(job_id, {"type": "stopped"})
                else:
                    await job_repo.update_status(job_id, JobStatus.DONE)
                    await session.commit()
                    await event_bus.publish(job_id, {
                        "type": "done",
                        "stats": stats,
                        "results_count": len(results),
                    })

            except InterruptedError:
                await job_repo.update_status(job_id, JobStatus.STOPPED)
                await session.commit()
                await event_bus.publish(job_id, {"type": "stopped"})
            except Exception as e:
                try:
                    await session.rollback()
                except Exception:
                    pass
                async with AsyncSessionLocal() as err_session:
                    err_repo = JobRepository(err_session)
                    await err_repo.update_status(job_id, JobStatus.ERROR, str(e))
                    await err_session.commit()
                await event_bus.publish(job_id, {"type": "error", "message": str(e)})


ai_orchestrator = AIOrchestrator()
