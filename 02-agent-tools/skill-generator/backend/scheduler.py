"""
定时任务调度器
"""
import asyncio
import logging
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlmodel import Session, select
from config import settings
from database import engine
from models import Skill, CrawlJob
from crawler.github_trending import GitHubTrendingCrawler
from crawler.hackernews import HackerNewsCrawler
from crawler.devto import DevtoCrawler
from crawler.producthunt import ProductHuntCrawler
from crawler.skillhub import SkillHubCrawler
from crawler.skillhub_club import SkillHubClubCrawler
from doc_generator.generator import DocGenerator

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def run_crawl_job(triggered_by: str = "scheduler") -> CrawlJob:
    """执行一次完整的爬取 + 文档生成任务"""

    # 1. 创建任务记录
    with Session(engine) as session:
        job = CrawlJob(
            triggered_by=triggered_by,
            status="running",
            started_at=datetime.now(),
        )
        session.add(job)
        session.commit()
        session.refresh(job)
        job_id = job.id

    logger.info(f"[Scheduler] 开始爬取任务 #{job_id} (triggered_by={triggered_by})")

    try:
        # 2. 并发执行所有启用的爬虫
        crawlers = []
        if settings.CRAWL_GITHUB_ENABLED:
            crawlers.append(GitHubTrendingCrawler())
        if settings.CRAWL_HACKERNEWS_ENABLED:
            crawlers.append(HackerNewsCrawler())
        if settings.CRAWL_DEVTO_ENABLED:
            crawlers.append(DevtoCrawler())
        if settings.CRAWL_PRODUCTHUNT_ENABLED:
            crawlers.append(ProductHuntCrawler())
        if settings.CRAWL_SKILLHUB_ENABLED:
            crawlers.append(SkillHubCrawler())
        if settings.CRAWL_SKILLHUB_CLUB_ENABLED:
            crawlers.append(SkillHubClubCrawler(api_key=settings.SKILLHUB_CLUB_API_KEY))

        results = await asyncio.gather(
            *[c.safe_crawl() for c in crawlers],
            return_exceptions=True,
        )

        # 3. 合并去重并写入数据库
        all_items = []
        for result in results:
            if isinstance(result, list):
                all_items.extend(result)

        total_count = len(all_items)
        success_count = 0
        failed_count = 0
        new_skill_ids = []

        with Session(engine) as session:
            for item in all_items:
                # 基于 source_url 去重
                existing = session.exec(
                    select(Skill).where(Skill.source_url == item.source_url)
                ).first()
                if existing:
                    continue

                try:
                    skill = Skill(
                        title=item.title,
                        source=item.source,
                        source_url=item.source_url,
                        description=item.description,
                        raw_content=item.raw_content,
                        tags=item.tags,
                        stars=item.stars,
                        language=item.language,
                        crawled_at=datetime.now(),
                    )
                    session.add(skill)
                    session.commit()
                    session.refresh(skill)
                    new_skill_ids.append(skill.id)
                    success_count += 1
                except Exception as e:
                    logger.error(f"[Scheduler] 写入失败: {item.title} - {e}")
                    session.rollback()
                    failed_count += 1

        logger.info(f"[Scheduler] 爬取完成，新增 {success_count} 条，失败 {failed_count} 条")

        # 4. 为新技能生成 AI 文档（mock 模式无需 API Key 也会生成模板文档）
        if new_skill_ids:
            logger.info(f"[Scheduler] 开始生成文档，共 {len(new_skill_ids)} 条")
            doc_gen = DocGenerator()

            with Session(engine) as session:
                skills_to_gen = []
                for sid in new_skill_ids:
                    skill = session.get(Skill, sid)
                    if skill:
                        skills_to_gen.append({
                            "id": skill.id,
                            "title": skill.title,
                            "source": skill.source,
                            "source_url": skill.source_url,
                            "raw_content": skill.raw_content,
                        })

            doc_results = await doc_gen.batch_generate(skills_to_gen)

            with Session(engine) as session:
                for doc_result in doc_results:
                    skill = session.get(Skill, doc_result["id"])
                    if skill:
                        skill.doc_markdown = doc_result["doc_markdown"]
                        skill.doc_generated_at = doc_result["generated_at"]
                        skill.is_doc_ready = True
                        session.add(skill)
                session.commit()

            logger.info(f"[Scheduler] 文档生成完成")

        # 5. 更新任务状态
        with Session(engine) as session:
            job = session.get(CrawlJob, job_id)
            if job:
                job.status = "done"
                job.total = total_count
                job.success = success_count
                job.failed = failed_count
                job.finished_at = datetime.now()
                session.add(job)
                session.commit()
                session.refresh(job)
                return job

    except Exception as e:
        logger.error(f"[Scheduler] 任务失败: {e}")
        with Session(engine) as session:
            job = session.get(CrawlJob, job_id)
            if job:
                job.status = "failed"
                job.error_msg = str(e)
                job.finished_at = datetime.now()
                session.add(job)
                session.commit()
                session.refresh(job)
                return job

    # fallback
    with Session(engine) as session:
        return session.get(CrawlJob, job_id)


def init_scheduler():
    """初始化调度器"""
    if not settings.SCHEDULER_ENABLED:
        logger.info("[Scheduler] 调度器未启用")
        return

    scheduler.add_job(
        run_crawl_job,
        trigger=CronTrigger(
            hour=settings.SCHEDULER_HOUR,
            minute=settings.SCHEDULER_MINUTE,
            timezone=settings.SCHEDULER_TIMEZONE,
        ),
        id="daily_crawl",
        replace_existing=True,
        kwargs={"triggered_by": "scheduler"},
    )
    scheduler.start()
    logger.info(
        f"[Scheduler] 调度器已启动，每天 {settings.SCHEDULER_HOUR}:{settings.SCHEDULER_MINUTE:02d} "
        f"({settings.SCHEDULER_TIMEZONE}) 执行爬取"
    )
