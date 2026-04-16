"""Scheduled jobs CRUD endpoints."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.scheduler import (
    create_schedule,
    delete_schedule,
    list_schedules,
    toggle_schedule,
)

router = APIRouter()


class CreateScheduleRequest(BaseModel):
    tool: str = Field(description="harvester | mapper | ripper | media")
    url: str
    config: dict = Field(default_factory=dict)
    cron: str = Field(description="5-field cron: '0 3 * * *' = daily 3am")
    label: str = ""


@router.post("/create")
async def create(req: CreateScheduleRequest):
    try:
        meta = create_schedule(
            tool=req.tool,
            url=req.url,
            config=req.config,
            cron_expr=req.cron,
            label=req.label,
        )
        return meta
    except Exception as e:
        raise HTTPException(400, str(e))


@router.get("/list")
async def list_all():
    return list_schedules()


@router.delete("/{schedule_id}")
async def delete(schedule_id: str):
    if not delete_schedule(schedule_id):
        raise HTTPException(404, "Schedule not found")
    return {"ok": True}


@router.post("/{schedule_id}/toggle")
async def toggle(schedule_id: str, enabled: bool = True):
    if not toggle_schedule(schedule_id, enabled):
        raise HTTPException(404, "Schedule not found")
    return {"ok": True}
