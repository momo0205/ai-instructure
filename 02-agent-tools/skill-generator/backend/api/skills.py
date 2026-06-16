"""
技能相关 API 路由
"""
from datetime import date, datetime
from typing import Optional
import io
import json
import re
import zipfile
from fastapi import APIRouter, Depends, Query, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlmodel import Session, select, func, col
from database import get_session, engine
from models import Skill, SkillListItem, SkillDetail
from doc_generator.generator import DocGenerator, generate_doc_direct, generate_skill_instructions
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/skills", tags=["skills"])


@router.get("", response_model=dict)
async def list_skills(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    source: Optional[str] = Query(None, description="来源过滤"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    date_str: Optional[str] = Query(None, alias="date", description="日期过滤 (YYYY-MM-DD)"),
    session: Session = Depends(get_session),
):
    """获取技能列表（分页）"""
    query = select(Skill)

    # 来源过滤
    if source:
        query = query.where(Skill.source == source)

    # 关键词搜索
    if search:
        query = query.where(
            col(Skill.title).contains(search) | col(Skill.description).contains(search)
        )

    # 日期过滤
    if date_str:
        try:
            target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            query = query.where(
                func.date(Skill.crawled_at) == target_date
            )
        except ValueError:
            pass

    # 计算总数
    count_query = select(func.count()).select_from(query.subquery())
    total = session.exec(count_query).one()

    # 排序 + 分页
    query = query.order_by(col(Skill.crawled_at).desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    skills = session.exec(query).all()
    items = [
        SkillListItem(
            id=s.id,
            title=s.title,
            source=s.source,
            source_url=s.source_url,
            description=s.description,
            tags=s.tags,
            stars=s.stars,
            language=s.language,
            crawled_at=s.crawled_at,
            is_doc_ready=s.is_doc_ready,
        )
        for s in skills
    ]

    return {
        "items": [item.model_dump() for item in items],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/{skill_id}", response_model=SkillDetail)
async def get_skill(skill_id: int, session: Session = Depends(get_session)):
    """获取技能详情"""
    skill = session.get(Skill, skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")

    return SkillDetail(
        id=skill.id,
        title=skill.title,
        source=skill.source,
        source_url=skill.source_url,
        description=skill.description,
        raw_content=skill.raw_content,
        doc_markdown=skill.doc_markdown,
        tags=skill.tags,
        stars=skill.stars,
        language=skill.language,
        crawled_at=skill.crawled_at,
        doc_generated_at=skill.doc_generated_at,
        is_doc_ready=skill.is_doc_ready,
    )


@router.post("/{skill_id}/generate-doc", response_model=dict)
async def generate_single_doc(skill_id: int, session: Session = Depends(get_session)):
    """为单条技能同步生成 AI 文档，生成完毕后直接返回最新文档内容"""
    skill = session.get(Skill, skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")

    logger.info(f"[GenerateDoc] 开始生成: [{skill.source}] {skill.title[:40]}")
    try:
        doc = await generate_doc_direct(
            title=skill.title,
            source=skill.source,
            source_url=skill.source_url,
            raw_content=skill.raw_content,
        )
        skill.doc_markdown = doc
        skill.doc_generated_at = datetime.now()
        skill.is_doc_ready = True
        session.add(skill)
        session.commit()
        session.refresh(skill)
        logger.info(f"[GenerateDoc] ✅ 完成: {skill.title[:40]}")
        return {
            "id": skill.id,
            "is_doc_ready": skill.is_doc_ready,
            "doc_markdown": skill.doc_markdown,
            "doc_generated_at": skill.doc_generated_at,
        }
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        logger.error(f"[GenerateDoc] ❌ 失败详情:\n{tb}")
        raise HTTPException(status_code=500, detail=f"文档生成失败: {type(e).__name__}: {str(e)}")


@router.post("/regenerate-docs", response_model=dict)
async def regenerate_docs(background_tasks: BackgroundTasks):
    """
    重新为所有 mock 文档（含「模板预览模式」字样）生成 AI 文档。
    在后台异步执行，立即返回。
    """
    background_tasks.add_task(_regenerate_all_mock_docs)
    return {"message": "文档重新生成任务已启动，请稍候查看结果", "status": "accepted"}


async def _regenerate_all_mock_docs():
    """后台批量重新生成所有未就绪文档"""
    from sqlmodel import Session as _Session
    with _Session(engine) as session:
        skills = session.exec(select(Skill)).all()
        skills_data = [
            {"id": s.id, "title": s.title, "source": s.source,
             "source_url": s.source_url, "raw_content": s.raw_content}
            for s in skills
            if not s.is_doc_ready or not s.doc_markdown
        ]

    if not skills_data:
        logger.info("[RegenerateDoc] 所有文档已就绪，无需重新生成")
        return

    logger.info(f"[RegenerateDoc] 开始重新生成 {len(skills_data)} 条文档")
    doc_gen = DocGenerator()
    results = await doc_gen.batch_generate(skills_data)

    with _Session(engine) as session:
        for r in results:
            if r.get("ok") and r.get("doc_markdown"):
                skill = session.get(Skill, r["id"])
                if skill:
                    skill.doc_markdown = r["doc_markdown"]
                    skill.doc_generated_at = r["generated_at"]
                    skill.is_doc_ready = True
                    session.add(skill)
        session.commit()

    success = sum(1 for r in results if r.get("ok"))
    logger.info(f"[RegenerateDoc] 完成，成功 {success}/{len(results)} 条")


# ──────────────────────────────────────────────────────────────────
# 下载 Skill（标准 CodeFlicker Skill 格式 zip 包）
# ──────────────────────────────────────────────────────────────────

def _slug(text: str) -> str:
    """将标题转换为 kebab-case slug，用作 skill 目录名"""
    text = text.lower()
    text = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "-", text)
    text = text.strip("-")
    return text[:60] or "skill"


def _build_skill_md(skill: Skill, slug: str, skill_instructions: str) -> str:
    """生成标准 CodeFlicker SKILL.md 内容（YAML frontmatter + AI 生成的操作指南）"""
    source_map = {
        "github": "GitHub Trending",
        "hackernews": "Hacker News",
        "devto": "Dev.to",
        "producthunt": "Product Hunt",
        "skillhub": "SkillHub",
    }
    source_label = source_map.get(skill.source, skill.source)

    # description 取原始描述（截短），用于 frontmatter
    description_short = (skill.description or skill.title)[:180].replace("\n", " ")

    frontmatter = f"""---
name: {slug}
description: This skill should be used when discussing "{skill.title}" or related topics from {source_label}. {description_short}
version: 1.0.0
source: skill-generator
original_url: {skill.source_url}
crawled_at: {skill.crawled_at.strftime('%Y-%m-%d')}
---
"""
    # SKILL.md 主体 = LLM 生成的 Agent 操作指南
    return frontmatter + "\n" + skill_instructions


def _build_readme(skill: Skill, slug: str) -> str:
    """生成 README.md 使用说明"""
    source_map = {
        "github": "GitHub Trending",
        "hackernews": "Hacker News",
        "devto": "Dev.to",
        "producthunt": "Product Hunt",
        "skillhub": "SkillHub",
    }
    source_label = source_map.get(skill.source, skill.source)
    return f"""# {skill.title} - Skill 使用说明

> 本 Skill 由 [skill-generator](https://github.com/skill-generator) 自动生成
> 来源：{source_label} | 原始链接：{skill.source_url}

## 安装方式

### 个人级 Skill（推荐）

将 `{slug}/` 目录复制到你的 CodeFlicker skills 目录：

```bash
# macOS / Linux
cp -r {slug} ~/.codeflicker/skills/

# 或 KwaiPilot
cp -r {slug} ~/.kwaipilot/skills/
```

### 项目级 Skill

将目录复制到当前项目：

```bash
cp -r {slug} .kwaipilot/skills/
```

## 目录结构

```
{slug}/
└── SKILL.md        # Skill 主文件（含完整中文文档）
```

## 生效方式

安装后等待约 **30 秒**自动生效，或重启 VS Code / CodeFlicker 立即生效。

## 触发方式

在对话中直接提到 **{skill.title}** 相关话题，Skill 将自动被加载提供专业指导。

也可手动触发：`/{slug}`

## 文档来源

- 原始来源：{source_label}
- 原始链接：{skill.source_url}
- 文档生成时间：{(skill.doc_generated_at or skill.crawled_at).strftime('%Y-%m-%d %H:%M')}

---
*由 skill-generator 自动生成，基于 DeepSeek AI 大模型*
"""


@router.get("/{skill_id}/download")
async def download_skill(skill_id: int, session: Session = Depends(get_session)):
    """
    下载 Skill 为标准 CodeFlicker Skill 格式 zip 包。
    - SKILL.md：由 LLM 实时生成的 Agent 操作指南（告诉 Agent「怎么做」）
    - README.md：安装和使用说明
    """
    skill = session.get(Skill, skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")

    slug = _slug(skill.title)

    # 实时生成 Skill 指令（操作指南，而非介绍文档）
    logger.info(f"[Download] 生成 Skill 指令: {skill.title[:40]}")
    try:
        skill_instructions = await generate_skill_instructions(
            title=skill.title,
            source=skill.source,
            source_url=skill.source_url,
            raw_content=skill.raw_content,
        )
    except Exception as e:
        logger.error(f"[Download] Skill 指令生成失败: {e}")
        raise HTTPException(status_code=500, detail=f"Skill 指令生成失败: {str(e)}")

    skill_md = _build_skill_md(skill, slug, skill_instructions)
    readme_md = _build_readme(skill, slug)

    # 构建 zip 包（内存）
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"{slug}/SKILL.md", skill_md.encode("utf-8"))
        zf.writestr(f"{slug}/README.md", readme_md.encode("utf-8"))
    buf.seek(0)

    filename = f"{slug}.zip"
    logger.info(f"[Download] ✅ 打包完成: {filename}")
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

