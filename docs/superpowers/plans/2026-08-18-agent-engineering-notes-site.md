# Agent 工程笔记网站 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 建立独立公开的“Agent 工程笔记”内容站，以经过脱敏的 Agent Evidence Lab 学习材料为首发内容，并提供可验证的构建、预览和发布流程。

**Architecture:** 在 `ai-instructure` 同级创建独立仓库 `/Users/chenmao/Desktop/workspace/agent-engineering-notes`，使用 Sites 初始化的 React/Vinext 多路由应用。Markdown 文章由服务端内容模块完成严格元数据校验、发布状态过滤、安全 HTML 渲染和静态搜索；CI 只读取公开仓库，不连接私人工作区。

**Tech Stack:** React、TypeScript、Vinext/Vite、Markdown、Zod、gray-matter、marked、sanitize-html、Vitest、Testing Library、Sites Hosting、GitHub

---

## File map

```text
agent-engineering-notes/
├── .openai/hosting.json
├── .github/workflows/verify.yml
├── app/
│   ├── layout.tsx
│   ├── globals.css
│   ├── page.tsx
│   ├── journey/page.tsx
│   ├── articles/page.tsx
│   ├── articles/[slug]/page.tsx
│   ├── projects/agent-evidence-lab/page.tsx
│   ├── about/page.tsx
│   ├── rss.xml/route.ts
│   ├── sitemap.ts
│   └── robots.ts
├── components/{site-header,site-footer,article-card,article-body,reading-path,search-filter}.tsx
├── content/articles/*.md
├── lib/content/{article-schema,article-repository,markdown-renderer,search-index}.ts
├── scripts/{scan-public-content,check-internal-links}.mjs
├── tests/{content,security,pages}/
├── public/og.png
├── README.md
└── HANDOFF.md
```

## Task 1: Initialize the isolated public repository

**Files:**
- Create: `/Users/chenmao/Desktop/workspace/agent-engineering-notes/**`
- Modify: `package.json`
- Create: `.gitignore`

- [ ] **Step 1: Prove the target is absent or empty**

Run:

```bash
test ! -e /Users/chenmao/Desktop/workspace/agent-engineering-notes || \
  test -z "$(find /Users/chenmao/Desktop/workspace/agent-engineering-notes -mindepth 1 -maxdepth 1 -print -quit)"
```

Expected: exit `0`. A non-empty target is a hard stop; inspect it instead of overwriting.

- [ ] **Step 2: Initialize the Sites starter exactly once**

From the empty target directory run:

```bash
/Users/chenmao/.codex/plugins/cache/openai-bundled/sites/0.1.34/scripts/init-site.sh "$PWD"
```

Expected: `.openai/hosting.json`, `app/page.tsx`, `app/layout.tsx`, `app/globals.css`, lockfile and installed dependencies.

- [ ] **Step 3: Add content and test dependencies**

```bash
npm install zod gray-matter marked sanitize-html
npm install -D vitest @testing-library/react @testing-library/jest-dom jsdom @types/sanitize-html
```

Merge these scripts into `package.json`:

```json
{
  "scripts": {
    "test": "vitest run",
    "check:secrets": "node scripts/scan-public-content.mjs",
    "check:links": "node scripts/check-internal-links.mjs",
    "verify": "npm run test && npm run check:secrets && npm run check:links && npm run build"
  }
}
```

- [ ] **Step 4: Remove starter-only UI and metadata**

Delete `app/_sites-preview`, remove its imports and every `codex-preview` metadata marker. If unused elsewhere, run `npm uninstall react-loading-skeleton`.

- [ ] **Step 5: Add repository ignores**

```gitignore
node_modules/
.vinext/
.vite/
dist/
.env
.env.*
!.env.example
.DS_Store
coverage/
```

- [ ] **Step 6: Verify and commit baseline**

Run `npm run build`; expect exit `0` and Cloudflare-compatible ESM output. Then:

```bash
test -d .git || git init
git branch -M main
git add .
git commit -m "chore: initialize Agent engineering notes site"
```

## Task 2: Add the strict article model

**Files:**
- Create: `lib/content/article-schema.ts`
- Create: `lib/content/article-repository.ts`
- Test: `tests/content/article-schema.test.ts`
- Test: `tests/content/article-repository.test.ts`

- [ ] **Step 1: Write the failing schema test**

```ts
import { describe, expect, it } from "vitest";
import { articleMetadataSchema } from "../../lib/content/article-schema";

const valid = { title: "从 Java 后端到 Agent 开发", summary: "技术栈变化与学习路径。",
  status: "published", category: "学习路径", publishedAt: "2026-08-18",
  updatedAt: "2026-08-18", readingMinutes: 12, tags: ["Java", "Agent"] };

describe("articleMetadataSchema", () => {
  it("accepts complete metadata", () => expect(articleMetadataSchema.parse(valid).status).toBe("published"));
  it("rejects unknown state", () => expect(() => articleMetadataSchema.parse({ ...valid, status: "public" })).toThrow());
  it("rejects missing summary", () => expect(() => articleMetadataSchema.parse({ ...valid, summary: undefined })).toThrow());
});
```

- [ ] **Step 2: Verify RED**

Run: `npm test -- tests/content/article-schema.test.ts`  
Expected: FAIL because `article-schema.ts` is missing.

- [ ] **Step 3: Implement metadata types**

```ts
import { z } from "zod";
const isoDate = /^\d{4}-\d{2}-\d{2}$/;
export const articleMetadataSchema = z.object({
  title: z.string().min(4).max(120), summary: z.string().min(8).max(240),
  status: z.enum(["draft", "review", "published"]),
  category: z.enum(["学习路径", "工程实践", "真实复盘", "架构决策"]),
  publishedAt: z.string().regex(isoDate), updatedAt: z.string().regex(isoDate),
  readingMinutes: z.number().int().positive().max(60),
  tags: z.array(z.string().min(1).max(30)).min(1).max(8),
});
export type ArticleMetadata = z.infer<typeof articleMetadataSchema>;
export type Article = ArticleMetadata & { slug: string; body: string };
```

- [ ] **Step 4: Verify GREEN**

Run: `npm test -- tests/content/article-schema.test.ts`  
Expected: 3 tests pass.

- [ ] **Step 5: Test parsing and publication filtering**

Create a repository test using complete YAML frontmatter. Assert `parseArticle("java-to-agent.md", source).slug === "java-to-agent"` and assert `visibleArticles([review, published])` returns only `published`.

- [ ] **Step 6: Implement the repository**

```ts
import fs from "node:fs";
import path from "node:path";
import matter from "gray-matter";
import { articleMetadataSchema, type Article } from "./article-schema";
const root = path.join(process.cwd(), "content", "articles");
export function parseArticle(name: string, source: string): Article {
  const parsed = matter(source);
  return { ...articleMetadataSchema.parse(parsed.data), slug: name.replace(/\.md$/, ""), body: parsed.content.trim() };
}
export function allArticles(): Article[] {
  return fs.readdirSync(root).filter(x => x.endsWith(".md"))
    .map(x => parseArticle(x, fs.readFileSync(path.join(root, x), "utf8")))
    .sort((a, b) => b.updatedAt.localeCompare(a.updatedAt) || a.slug.localeCompare(b.slug));
}
export const visibleArticles = (values = allArticles()) => values.filter(x => x.status === "published");
export const articleBySlug = (slug: string) => visibleArticles().find(x => x.slug === slug);
```

- [ ] **Step 7: Verify and commit**

Run `npm test -- tests/content`; expect all pass. Commit:

```bash
git add lib/content tests/content package.json package-lock.json
git commit -m "feat: add strict article content model"
```

## Task 3: Render safe Markdown and article routes

**Files:**
- Create: `lib/content/markdown-renderer.ts`
- Create: `components/article-body.tsx`
- Create: `components/article-card.tsx`
- Create: `app/articles/page.tsx`
- Create: `app/articles/[slug]/page.tsx`
- Test: `tests/content/markdown-renderer.test.ts`

- [ ] **Step 1: Write the failing safety test**

```ts
const html = renderMarkdown("# 标题\n\n`code`\n\n<script>alert(1)</script>");
expect(html).toContain("<h1>标题</h1>");
expect(html).toContain("<code>code</code>");
expect(html).not.toContain("script");
expect(html).not.toContain("alert(1)");
```

Run `npm test -- tests/content/markdown-renderer.test.ts`; expect missing-module failure.

- [ ] **Step 2: Implement the only HTML trust boundary**

```ts
import { marked } from "marked";
import sanitizeHtml from "sanitize-html";
export function renderMarkdown(markdown: string): string {
  return sanitizeHtml(marked.parse(markdown, { async: false }) as string, {
    allowedTags: sanitizeHtml.defaults.allowedTags.concat(["img", "h1", "h2"]),
    allowedAttributes: { a: ["href", "title"], img: ["src", "alt", "title"] },
    allowedSchemes: ["https"],
  });
}
```

`ArticleBody` is the only component allowed to use `dangerouslySetInnerHTML`:

```tsx
export function ArticleBody({ html }: { html: string }) {
  return <article className="article-body" dangerouslySetInnerHTML={{ __html: html }} />;
}
```

- [ ] **Step 3: Implement article list/detail**

The list calls `visibleArticles()`. Detail calls `articleBySlug`, returns the framework not-found response for missing/review/draft slugs, and passes only sanitized `renderMarkdown(article.body)` to `ArticleBody`. Cards render category, reading time, title and summary.

- [ ] **Step 4: Verify and commit**

Run `npm test && npm run build`; expect all pass. Commit:

```bash
git add lib/content components app/articles tests/content
git commit -m "feat: add safe article publishing routes"
```

## Task 4: Build the approved visual system and homepage

**Files:**
- Modify: `app/layout.tsx`
- Modify: `app/globals.css`
- Modify: `app/page.tsx`
- Create: `components/site-header.tsx`
- Create: `components/site-footer.tsx`
- Test: `tests/pages/routes.test.tsx`

- [ ] **Step 1: Write the failing homepage contract**

```tsx
render(<Home />);
expect(screen.getByRole("heading", { name: /真正能工作的 Agent/ })).toBeInTheDocument();
expect(screen.getByText("Agent Evidence Lab")).toBeInTheDocument();
expect(screen.getByRole("heading", { name: "最近写下的东西" })).toBeInTheDocument();
```

Run the test; expect failure against the starter.

- [ ] **Step 2: Define shared production tokens**

```css
:root {
  --paper:#f7f6f2; --ink:#202124; --muted:#6d6d69; --line:#deddd7;
  --feature:#262b3a; --feature-ink:#f7f7f5; --accent:#536fd7;
  --card-blue:#e4e8f3; --card-green:#e3ece7; --card-warm:#eee5df;
  --radius-large:20px; --radius-card:17px; --content-width:1120px;
}
```

Use package-managed or self-hosted fonts. Chinese headings/body use a soft sans stack; metadata uses monospace. Production must not depend on Google Fonts availability.

- [ ] **Step 3: Implement the approved homepage**

Required: brand `Agent 工程笔记`; personal learning hero; deep-indigo Agent Evidence Lab feature block; three low-saturation article cards; “为什么写下来”. Forbidden: grid paper, tag wall, terminal status panel, gradients, glowing AI imagery.

- [ ] **Step 4: Set site metadata**

Title: `Agent 工程笔记`  
Description: `从 Java 后端到 Agent Engineering：代码、失败、实验和工程判断。`

- [ ] **Step 5: Verify and commit**

Run `npm test -- tests/pages/routes.test.tsx && npm run build`; expect pass. Commit:

```bash
git add app components tests/pages
git commit -m "feat: build approved Agent engineering notes homepage"
```

## Task 5: Add journey, project, about, and static search

**Files:**
- Create: `app/journey/page.tsx`
- Create: `app/projects/agent-evidence-lab/page.tsx`
- Create: `app/about/page.tsx`
- Create: `components/reading-path.tsx`
- Create: `components/search-filter.tsx`
- Create: `lib/content/search-index.ts`
- Test: `tests/content/search-index.test.ts`

- [ ] **Step 1: Write the failing normalized-search test**

```ts
const articles = [
  { slug:"loop", title:"受约束 Agent Loop", summary:"观察、决策和验证", tags:["Agent"] },
  { slug:"java", title:"Java 到 Agent", summary:"技术栈迁移", tags:["Java"] },
];
expect(searchArticles(articles, "  loop ").map(x => x.slug)).toEqual(["loop"]);
expect(searchArticles(articles, "JAVA").map(x => x.slug)).toEqual(["java"]);
```

- [ ] **Step 2: Implement deterministic client search**

```ts
type Searchable={slug:string;title:string;summary:string;tags:string[]};
export function searchArticles<T extends Searchable>(items:T[], raw:string):T[] {
  const q=raw.normalize("NFC").trim().toLocaleLowerCase();
  return q ? items.filter(x => [x.title,x.summary,...x.tags].join(" ").normalize("NFC").toLocaleLowerCase().includes(q)) : items;
}
```

- [ ] **Step 3: Build remaining static routes**

- `/journey`: LLM API → Tool Calling → Context → Harness → RAG → Loop → Evaluation → Production.
- Project: completed M0–M2, current M3, 5/5 fixed-set result, remaining Checkpoint/Trace/budget/tool recovery.
- About: Java background, writing purpose, public-content policy; no private infrastructure detail.
- SearchFilter: query only published metadata; empty query preserves repository ordering.

- [ ] **Step 4: Verify and commit**

Run `npm test -- tests/content/search-index.test.ts && npm run build`; expect six routes build. Commit:

```bash
git add app/journey app/projects app/about components lib/content/search-index.ts tests/content/search-index.test.ts
git commit -m "feat: add learning journey and project pages"
```

## Task 6: Enforce public-content security and link gates

**Files:**
- Create: `scripts/scan-public-content.mjs`
- Create: `scripts/check-internal-links.mjs`
- Test: `tests/security/scan-public-content.test.ts`
- Test: `tests/security/check-internal-links.test.ts`
- Create: `.github/workflows/verify.yml`

- [ ] **Step 1: Write scanner tests**

Assert rejection for `sk-...`, Bearer headers, private-key headers, PostgreSQL URLs, IPv4 addresses, `/Users/...`, `.env` assignments and tunnel tokens. Assert ordinary prose and `[REDACTED]` pass. Findings expose only rule, relative path and line—not the full match.

- [ ] **Step 2: Implement a fixed-root scanner**

```js
export const PUBLIC_ROOTS=["content","app","components","public","README.md","HANDOFF.md"];
```

Never traverse `..`, outbound symlinks, `.git`, `node_modules`, `.env*`, or `ai-instructure`. Export `scanText(text,path)` for tests; CLI exits non-zero on findings.

- [ ] **Step 3: Test and implement link checks**

Extract relative Markdown links; require target Markdown/assets to exist. Reject `file://`, local absolute paths and escaping paths. Allow `https://` without making network calls.

- [ ] **Step 4: Add secret-free CI**

```yaml
name: verify
on: { pull_request: {}, push: { branches: [main] } }
permissions: { contents: read }
jobs:
  verify:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: 22, cache: npm }
      - run: npm ci
      - run: npm run verify
```

- [ ] **Step 5: Verify fail-closed behavior and commit**

Run valid checks, then temporarily add one fake secret and prove `check:secrets` fails before removing it. Run `npm run verify`; expect pass. Commit:

```bash
git add scripts tests/security .github package.json package-lock.json
git commit -m "feat: enforce public content safety gates"
```

## Task 7: Add SEO, RSS, sitemap, and social preview

**Files:**
- Create: `app/rss.xml/route.ts`
- Create: `app/sitemap.ts`
- Create: `app/robots.ts`
- Create: `public/og.png`
- Modify: `app/layout.tsx`

- [ ] **Step 1: Add published-only metadata outputs**

RSS and sitemap call `visibleArticles()`. Canonical base uses `SITE_URL` with local fallback `http://localhost:3000`, never a private hostname. Add title template `%s · Agent 工程笔记`.

- [ ] **Step 2: Generate one bespoke social card**

Use image generation once after copy is frozen. Required text: `Agent 工程笔记`; approved palette; no robots, brains, circuits, neon or invented copy. Inspect and retry at most once. Save as `public/og.png`.

- [ ] **Step 3: Verify and commit**

Run `npm run build`; confirm draft/review slugs are absent from RSS/sitemap. Commit:

```bash
git add app public/og.png
git commit -m "feat: add publishing metadata and feeds"
```

## Task 8: Curate the first five articles together

**Files:**
- Create: `content/articles/{java-to-agent,agent-llm-context-harness,bounded-agent-loop,stance-misclassification,java-vs-python-worker}.md`
- Create: `docs/review/first-release-content-review.md`

- [ ] **Step 1: Inventory sources safely**

Read relevant Agent Evidence Lab design, acceptance, roadmap, ADR and source files. Record source path, target article, sensitive category and planned redaction without copying sensitive values.

- [ ] **Step 2: Draft all five as `review`**

Each article distinguishes current/future behavior, includes code/test evidence and avoids private paths, credentials, topology and personal identifiers.

- [ ] **Step 3: Prove review content is not public**

Run `npm run verify`; expect pass and no review article in production index, RSS or sitemap.

- [ ] **Step 4: Obtain explicit owner approval article by article**

Present summary, removals, factual claims and preview to 陈矛. Change to `published` only after approval. MVP requires at least three published; the other two may stay review.

- [ ] **Step 5: Re-verify and commit**

Run `npm run verify`; expect only approved slugs public. Commit:

```bash
git add content/articles docs/review
git commit -m "docs: publish reviewed Agent engineering articles"
```

## Task 9: Document maintenance and account handoff

**Files:**
- Create: `README.md`
- Create: `HANDOFF.md`
- Create: `docs/design/site-design.md`

- [ ] **Step 1: Copy the approved design into the public repository**

Remove private absolute paths and internal Git details; preserve goals, visual tokens, page structure, publication states and safety boundaries.

- [ ] **Step 2: Write README**

Document purpose, public/private boundary, install, dev, tests, `npm run verify`, metadata, status transitions and deployment. State explicitly that CI never reads the private workspace.

- [ ] **Step 3: Write HANDOFF with exact sections**

```md
# Handoff
## Current outcome
## Repository and branch
## Last verified commands
## Published and review articles
## Security boundaries
## Remaining work
## New Codex account startup
```

The startup section requires reading README, HANDOFF, design, Git log and status before edits. Do not include auth files, account IDs or tokens.

- [ ] **Step 4: Verify and commit**

Run `npm run verify && git diff --check`; expect pass. Commit:

```bash
git add README.md HANDOFF.md docs/design
git commit -m "docs: add publishing and account handoff guide"
```

## Task 10: Publish GitHub and Sites preview

**Files:**
- No source changes expected unless validation finds a real defect.

- [ ] **Step 1: Resolve authentication first**

```bash
gh auth status
ssh -T git@github.com
```

Expected: intended GitHub identity and successful SSH authentication. Current root-repository push failed with `Permission denied (publickey)`; if still failing, stop and ask 陈矛 to restore SSH or authorize HTTPS. Do not rewrite unrelated remotes.

- [ ] **Step 2: Create the approved public repository**

After showing exact owner/name:

```bash
gh repo create agent-engineering-notes --public --source=. --remote=origin --push
```

Expected: public repo and pushed `main`.

- [ ] **Step 3: Confirm CI**

Run `gh run list --limit 5`; expect `verify` success without repository secrets.

- [ ] **Step 4: Deploy through Sites Hosting**

Invoke `sites-hosting`, deploy the verified build, and retain its URL. Smoke-check homepage, journey, articles, one published article, project, about, RSS, sitemap and mobile navigation.

- [ ] **Step 5: Record final handoff**

Add repository URL, preview URL, verified commit and optional work to HANDOFF. Run `npm run verify`, commit and push.

## Final verification gate

Run:

```bash
npm ci
npm run verify
git diff --check
git status --short --branch
gh run list --limit 5
```

Completion requires six routes, at least three approved articles, zero secret findings, zero broken links, reviewed desktop/mobile preview, green public CI, live Sites URL, and a handoff naming the verified commit and remaining optional work.
