"""FastAPI application factory."""
import asyncio
import logging
import sys
from contextlib import asynccontextmanager

# Windows + asyncio subprocess fix. Must run BEFORE any event loop is created
# by uvicorn. Uvicorn's reload subprocess re-imports this module fresh, so
# setting the policy here covers both parent and child processes. Without
# ProactorEventLoopPolicy, Playwright's subprocess_exec raises
# NotImplementedError on Windows.
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import select, update

from app.config import settings
from app.db.session import AsyncSessionLocal, init_db, close_db
from app.models.job import Job, JobStatus
from app.api import ai, bulk, bypass, cluster, data_api, diff, docs as docs_api, export, exposure, harvester, history, downloads, intel, linkcheck, llm, mapper, media, metadata as metadata_api, osint, pipeline, playground, ripper, scheduled, screenshot, screenshot_compare, screenshot_gallery, screenshot_video, security, seo, settings as settings_api, sitemap as sitemap_api, ssl_inspect, system, tech, threat, vault, wayback, webhooks, worker

logger = logging.getLogger("pyscrapr")


async def _recover_orphaned_jobs() -> int:
    """Reset jobs stuck in RUNNING/PENDING after a server restart."""
    async with AsyncSessionLocal() as session:
        stmt = (
            update(Job)
            .where(Job.status.in_([JobStatus.RUNNING, JobStatus.PENDING]))
            .values(
                status=JobStatus.STOPPED,
                error_message="Interrupted by server restart",
            )
        )
        result = await session.execute(stmt)
        await session.commit()
        return result.rowcount  # type: ignore[return-value]


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_db()
    recovered = await _recover_orphaned_jobs()
    if recovered:
        logger.warning("Recovered %d orphaned job(s) on startup", recovered)
    # Start EventBus cleanup task
    from app.services.event_bus import event_bus
    event_bus.start_cleanup_task()
    # Register webhook listener for job completion events
    from app.services.webhook_listener import on_job_event
    event_bus.add_global_listener(on_job_event)
    # Register email listener for job completion events
    from app.services.email_listener import on_job_event as on_email_event
    event_bus.add_global_listener(on_email_event)
    # Register pipeline listener for auto-run on job done
    from app.services.pipeline_listener import on_job_event as on_pipeline_event
    event_bus.add_global_listener(on_pipeline_event)
    # Register threat auto-scan listener
    from app.services.threat_scan_listener import on_job_event as on_threat_event
    event_bus.add_global_listener(on_threat_event)
    # Schedule YARA rules auto-fetch in background (non-blocking)
    try:
        from app.services.yara_engine import get_engine as _get_yara

        async def _yara_bg_fetch() -> None:
            try:
                await _get_yara().ensure_rules_downloaded()
            except Exception as e:
                logger.warning("YARA auto-fetch background gagal: %s", e)

        asyncio.create_task(_yara_bg_fetch())
    except Exception as e:
        logger.warning("Tidak bisa menjadwalkan YARA auto-fetch: %s", e)
    yield
    # Shutdown
    event_bus.stop_cleanup_task()
    await close_db()


def create_app() -> FastAPI:
    app = FastAPI(
        title="PyScrapr API",
        description="Modular web scraping toolkit — Image Harvester / URL Mapper / Site Ripper",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Routers
    app.include_router(harvester.router, prefix="/api/harvester", tags=["harvester"])
    app.include_router(mapper.router, prefix="/api/mapper", tags=["mapper"])
    app.include_router(ripper.router, prefix="/api/ripper", tags=["ripper"])
    app.include_router(media.router, prefix="/api/media", tags=["media"])
    app.include_router(ai.router, prefix="/api/ai", tags=["ai"])
    app.include_router(playground.router, prefix="/api/playground", tags=["playground"])
    app.include_router(bypass.router, prefix="/api/bypass", tags=["bypass"])
    app.include_router(data_api.router, prefix="/api/data", tags=["data"])
    app.include_router(export.router, prefix="/api/export", tags=["export"])
    app.include_router(bulk.router, prefix="/api/bulk", tags=["bulk"])
    app.include_router(diff.router, prefix="/api/diff", tags=["diff"])
    app.include_router(scheduled.router, prefix="/api/scheduled", tags=["scheduled"])
    app.include_router(vault.router, prefix="/api/vault", tags=["vault"])
    app.include_router(settings_api.router, prefix="/api/settings", tags=["settings"])
    app.include_router(webhooks.router, prefix="/api/webhooks", tags=["webhooks"])
    app.include_router(webhooks.email_router, prefix="/api/email", tags=["email"])
    app.include_router(llm.router, prefix="/api/llm", tags=["llm"])
    app.include_router(pipeline.router, prefix="/api/pipeline", tags=["pipeline"])
    app.include_router(docs_api.router, prefix="/api/docs", tags=["docs"])
    app.include_router(system.router, prefix="/api/system", tags=["system"])
    app.include_router(history.router, prefix="/api/history", tags=["history"])
    app.include_router(downloads.router, prefix="/api/downloads", tags=["downloads"])
    app.include_router(worker.router, prefix="/api/worker", tags=["worker"])
    app.include_router(cluster.router, prefix="/api/cluster", tags=["cluster"])
    app.include_router(tech.router, prefix="/api/tech", tags=["tech"])
    app.include_router(screenshot.router, prefix="/api/screenshot", tags=["screenshot"])
    app.include_router(screenshot_gallery.router, prefix="/api/screenshot", tags=["screenshot"])
    app.include_router(screenshot_compare.router, prefix="/api/screenshot/compare", tags=["screenshot"])
    app.include_router(screenshot_video.router, prefix="/api/screenshot/video", tags=["screenshot"])
    # Register 'screenshot' as a schedulable tool (extends bulk.TYPE_MAP + _dispatch)
    from app.services.screenshot_scheduler import register_screenshot_tool
    register_screenshot_tool()
    app.include_router(seo.router, prefix="/api/seo", tags=["seo"])
    app.include_router(linkcheck.router, prefix="/api/linkcheck", tags=["linkcheck"])
    app.include_router(security.router, prefix="/api/security", tags=["security"])
    app.include_router(ssl_inspect.router, prefix="/api/ssl", tags=["ssl"])
    app.include_router(intel.router, prefix="/api/intel", tags=["intel"])
    app.include_router(wayback.router, prefix="/api/wayback", tags=["wayback"])
    app.include_router(sitemap_api.router, prefix="/api/sitemap", tags=["sitemap"])
    app.include_router(threat.router, prefix="/api/threat", tags=["threat"])
    app.include_router(metadata_api.router, prefix="/api/metadata", tags=["metadata"])
    app.include_router(osint.router, prefix="/api/osint", tags=["osint"])
    app.include_router(exposure.router, prefix="/api/exposure", tags=["exposure"])

    @app.get("/api/health")
    async def health():
        return JSONResponse({"status": "ok", "version": app.version})

    return app


app = create_app()
