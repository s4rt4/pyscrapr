"""Domain intelligence endpoints: WHOIS + DNS + Subdomains."""
from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.models.job import Job, JobStatus, JobType
from app.repositories.job_repository import JobRepository
from app.schemas.intel import DNSRequest, DomainIntelResponse, DomainRequest
from app.services import domain_intel

logger = logging.getLogger("pyscrapr.intel")

router = APIRouter()


@router.post("/analyze", response_model=DomainIntelResponse)
async def analyze_domain(
    req: DomainRequest,
    session: AsyncSession = Depends(get_session),
) -> DomainIntelResponse:
    """Run WHOIS + DNS + subdomains concurrently, persist a Job row."""
    job_id = str(uuid.uuid4())
    job = Job(
        id=job_id,
        type=JobType.DOMAIN_INTEL,
        url=req.domain,
        status=JobStatus.PENDING,
        config=req.model_dump(mode="json"),
        stats={},
    )
    repo = JobRepository(session)
    await repo.create(job)

    job.status = JobStatus.RUNNING
    await session.flush()

    try:
        result = await domain_intel.analyze(req.domain)
    except ValueError as e:
        job.status = JobStatus.ERROR
        job.error_message = str(e)
        await session.commit()
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Domain intel failed for %s", req.domain)
        job.status = JobStatus.ERROR
        job.error_message = str(e)
        await session.commit()
        raise HTTPException(status_code=500, detail=f"Analyze failed: {e}")

    job.status = JobStatus.DONE
    job.stats = {
        "subdomain_count": result["subdomain_count"],
        "dns_record_types": len([k for k, v in result["dns"].items() if v]),
        "whois_registered": bool(result["whois"].get("registered")),
    }
    await session.commit()

    return DomainIntelResponse(**result)


@router.post("/whois")
async def whois_only(req: DomainRequest) -> dict:
    try:
        return await domain_intel.whois_lookup(req.domain)
    except Exception as e:
        logger.exception("whois failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/dns")
async def dns_only(req: DNSRequest) -> dict:
    try:
        return await domain_intel.dns_records(req.domain, req.record_types)
    except Exception as e:
        logger.exception("dns failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/subdomains")
async def subdomains_only(req: DomainRequest) -> dict:
    try:
        subs = await domain_intel.subdomains_via_crtsh(req.domain)
        return {"domain": req.domain, "subdomains": subs, "count": len(subs)}
    except Exception as e:
        logger.exception("subdomains failed")
        raise HTTPException(status_code=500, detail=str(e))
