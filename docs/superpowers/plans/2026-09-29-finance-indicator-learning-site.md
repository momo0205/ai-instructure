# Finance Indicator Learning Site Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and privately deploy a separate, beginner-friendly Chinese illustrated site for the five lessons in the approved design, ready for owner review before public release.

**Architecture:** A new `finance-ironmao` Git repository lives under `04-applications/investment-research/` and is excluded from the parent repository. A Vinext static export contains fixed fictional lesson data, pure indicator math, server-rendered lesson pages, and lightweight client interactions. It has no runtime dependency on the research platform or `notes.ironmao.com`.

**Tech Stack:** React 19, TypeScript, Vinext static export, SVG, CSS, Node built-in test runner, Sites private deployment.

**Spec:** `docs/superpowers/specs/2026-09-29-finance-indicator-learning-site-design.md`

**Execution status (2026-09-29):** Tasks 1–3 and Task 4 Step 1 completed. The owner-private Sites version was saved, but two deployment attempts of the same version failed with the provider's generic `AppGen deployment failed` response; no public or private URL exists yet. Task 4 Steps 2–3 remain open. The new project's registration had initially returned an internal error; subsequent site discovery recovered its ID, but `get_site` still reports `expected_url: null`, which may indicate incomplete provider provisioning. The local site and exported files remain intact and verified.

---

### Task 1: Independent project and numerical contract

**Files:**
- Create: `04-applications/investment-research/finance-ironmao/` via the Sites Vinext starter
- Create: `04-applications/investment-research/finance-ironmao/lib/lesson-data.ts`
- Create: `04-applications/investment-research/finance-ironmao/lib/indicator-math.ts`
- Create: `04-applications/investment-research/finance-ironmao/tests/indicator-math.test.mjs`
- Modify: `.gitignore`
- Modify: `04-applications/investment-research/finance-ironmao/next.config.ts`
- Modify: `04-applications/investment-research/finance-ironmao/.openai/hosting.json`

- [ ] **Step 1: Create the project and isolate it.** Run the Sites portable `project-setup.mjs` in the empty directory, then `git init` there. Add the exact path `04-applications/investment-research/finance-ironmao/` to the parent `.gitignore`. Set `output: 'export'` and `static.directory: 'dist/client'` (or the actual supported public export directory verified after build) without changing the project identity.
- [ ] **Step 2: Write the failing calculation tests.** `tests/indicator-math.test.mjs` imports pure functions from `../lib/indicator-math.ts` and asserts: `sma([10,11,12],3)` gives 11; EMA seeded by the first 3-point SMA gives 12.5 at day D; population standard deviation of `[10,11,12]` is `Math.sqrt(2/3)`; Bollinger(3,2) at C gives center 11, upper `11+2*Math.sqrt(2/3)`, lower `11-2*Math.sqrt(2/3)`; volume SMA of `[100,120,200]` gives 140; an absent close at E blocks price outputs while the same day's 170-share volume remains valid; zero volume is valid; warm-up produces `null`.
- [ ] **Step 3: Prove RED.** Run `node --experimental-strip-types --test tests/indicator-math.test.mjs`; expect missing module/export failure.
- [ ] **Step 4: Implement the minimal pure math and eight immutable A–H rows.** Use `number | null` for missing inputs, reject non-finite necessary values, require a contiguous valid window, seed EMA from its first complete window, and use population variance (`sum((x-mean)^2)/N`). Never interpret amount as close × volume. Keep the fixed OHLCV and amount values exactly as in the spec, plus a separate E-close-missing variant.
- [ ] **Step 5: Prove GREEN and commit the new repository.** Repeat the test; expect all assertions to pass. Commit only the independent site files in its repository.

### Task 2: Curriculum, diagrams, and teaching interaction

**Files:**
- Create: `04-applications/investment-research/finance-ironmao/lib/lessons.ts`
- Create: `04-applications/investment-research/finance-ironmao/components/lesson-diagrams.tsx`
- Create: `04-applications/investment-research/finance-ironmao/components/lesson-page.tsx`
- Create: `04-applications/investment-research/finance-ironmao/components/answer-reveal.tsx`
- Create/Modify: `04-applications/investment-research/finance-ironmao/app/page.tsx`
- Create: `04-applications/investment-research/finance-ironmao/app/learn/page.tsx`
- Create: `04-applications/investment-research/finance-ironmao/app/learn/[slug]/page.tsx`
- Create: `04-applications/investment-research/finance-ironmao/app/about/page.tsx`
- Modify: `04-applications/investment-research/finance-ironmao/app/globals.css`

- [ ] **Step 1: Write a failing content-contract test.** `tests/lessons.test.mjs` imports the lesson registry and verifies the exact slug order `candles`, `moving-averages`, `bollinger-bands`, `volume`, `read-a-chart`; each has a novice question, hand calculation, formula/parameters, “能描述什么”, “不能推出什么”, misconception, and a practice answer; no real ticker or buy/sell instruction. Run it and expect failure.
- [ ] **Step 2: Write five complete Chinese lessons, using the spec's A–H table throughout.** The first viewport offers the direct chapter route, not a generic product pitch. Each lesson repeats the common teaching rhythm and says “虚构教学数据”. Explain adjustment/source consistency, EMA seeding, 3-day pedagogical window versus common 20/2 defaults, amount as independent turnover field, gap/warm-up/zero handling, and non-predictive limits. The chart-reading chapter uses the E-close-missing variant rather than silently joining gaps.
- [ ] **Step 3: Make seven original, accessible diagrams.** Implement an annotated candle; close/SMA/EMA overlay; moving window and EMA seed; Bollinger center, bands, and width; volume versus amount with units; price gap versus valid volume; integrated chart. Each SVG has `<title>`/`<desc>`, visible legend and numeric/table equivalent. Line patterns/labels distinguish meaning without color alone.
- [ ] **Step 4: Add small teaching controls.** A preset-window toggle, accessible day selection, and native `<details>` answer reveal update educational numbers only; the static base case remains readable without JavaScript. Check keyboard focus and touch target size.
- [ ] **Step 5: Prove GREEN and commit.** Run both content and numerical tests, typecheck, and the local preview. Commit the lesson slice in the new repository.

### Task 3: Publication-quality site shell

**Files:**
- Modify: `04-applications/investment-research/finance-ironmao/app/layout.tsx`
- Modify: `04-applications/investment-research/finance-ironmao/app/globals.css`
- Create: `04-applications/investment-research/finance-ironmao/app/sitemap.ts`
- Create: `04-applications/investment-research/finance-ironmao/app/robots.ts`
- Modify: `04-applications/investment-research/finance-ironmao/public/favicon.svg`
- Create: `04-applications/investment-research/finance-ironmao/tests/site-contract.test.mjs`

- [ ] **Step 1: Write failing route/metadata tests.** Assert seven routes exist, each lesson has a distinct Chinese title/summary, public URL paths point only to `finance.ironmao.com`, and no `notes.ironmao.com` or private research paths are referenced. Run and expect failure.
- [ ] **Step 2: Implement shared typography/navigation and metadata.** Use the approved warm-paper/ink/sage/rust design, clear 16px+ body copy, desktop and mobile layouts, visible focus, reduced-motion support, canonical for each route, sitemap, robots, and a site-specific favicon. Include source and last-reviewed date on lessons/about; no fabricated social-preview image.
- [ ] **Step 3: Verify responsiveness and accessibility.** Inspect the live first meaningful preview at desktop and phone widths; check no horizontal overflow, readable diagram labels, keyboard order, contrast, and no color-only legend. Fix only evidenced defects.
- [ ] **Step 4: Run contract tests, typecheck, build, and commit.** Expect successful static output and no private data or absolute machine paths in public assets.

### Task 4: Private review deployment and handoff

**Files:**
- Verify: `04-applications/investment-research/finance-ironmao/.openai/hosting.json`
- Verify: `04-applications/investment-research/finance-ironmao/dist/client/`
- Update: `docs/superpowers/plans/2026-09-29-finance-indicator-learning-site.md` checkboxes only when actions pass

- [ ] **Step 1: Run final checks.** Numerical/content/route tests, `tsc --noEmit`, production build, `git diff --check`, all local routes, broken-link and secret/path scan; record exact results.
- [ ] **Step 2: Publish owner-private only.** Register one new Sites project, run the supported site-workflow script, save an archive-backed version, deploy privately, and wait for a successful deployment URL. Do not make the site public or connect DNS yet.
- [ ] **Step 3: Review handoff.** Give the owner the private preview URL and concise review checklist; explain that public release and `finance.ironmao.com` DNS binding remain pending owner approval. Preserve `notes.ironmao.com` unchanged.
- [ ] **Step 4: Memory and source-control SOP.** Attempt Mem0 write only if configured; never solicit or expose the key in logs. Commit/push only scoped site and plan changes, preserving unrelated dirty worktrees; report any blocked sync honestly.

## Self-review

The four tasks cover all seven design sections. The visual diagrams are code-native SVG, so no raster image generation is required. Public release is intentionally excluded until owner review, as the approved spec requires. No task changes the private research platform or AI notes site.
