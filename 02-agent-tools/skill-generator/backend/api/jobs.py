"""
任务相关 API 路由
"""
import asyncio
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlmodel import Session, select, col
from database import get_session
from models import CrawlJob, CrawlJobResponse
from scheduler import run_crawl_job

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.get("", response_model=list[CrawlJobResponse])
async def list_jobs(
    limit: int = 20,
    session: Session = Depends(get_session),
):
    """获取爬取任务历史"""
    query = (
        select(CrawlJob)
        .order_by(col(CrawlJob.started_at).desc())
        .limit(limit)
    )
    jobs = session.exec(query).all()
    return [
        CrawlJobResponse(
            id=j.id,
            triggered_by=j.triggered_by,
            status=j.status,
            total=j.total,
            success=j.success,
            failed=j.failed,
            started_at=j.started_at,
            finished_at=j.finished_at,
            error_msg=j.error_msg,
        )
        for j in jobs
    ]


@router.post("/trigger", response_model=dict)
async def trigger_crawl(background_tasks: BackgroundTasks):
    """手动触发一次爬取 + 文档生成"""
    background_tasks.add_task(_run_crawl_background)
    return {"message": "爬取任务已触发", "status": "accepted"}


async def _run_crawl_background():
    """后台运行爬取任务"""
    await run_crawl_job(triggered_by="manual")


@router.get("/{job_id}", response_model=CrawlJobResponse)
async def get_job(job_id: int, session: Session = Depends(get_session)):
    """获取某次任务状态"""
    job = session.get(CrawlJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return CrawlJobResponse(
        id=job.id,
        triggered_by=job.triggered_by,
        status=job.status,
        total=job.total,
        success=job.success,
        failed=job.failed,
        started_at=job.started_at,
        finished_at=job.finished_at,
        error_msg=job.error_msg,
    )
