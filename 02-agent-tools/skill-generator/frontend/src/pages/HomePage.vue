<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useMessage } from 'naive-ui'
import { useSkillStore } from '../stores/skill'
import SkillCard from '../components/SkillCard.vue'

const router = useRouter()
const store = useSkillStore()
const message = useMessage()

const searchValue = ref('')
const sourceValue = ref('')
const crawling = ref(false)

const sources = [
  { value: '', label: '全部' },
  { value: 'github', label: 'GitHub' },
  { value: 'hackernews', label: 'HN' },
  { value: 'devto', label: 'Dev.to' },
  { value: 'producthunt', label: 'PH' },
  { value: 'skillhub', label: 'SO Blog' },
  { value: 'skillhub_club', label: 'SkillHub' },
]

onMounted(() => {
  store.loadSkills()
})

let searchTimer: ReturnType<typeof setTimeout>
function handleSearchInput() {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    store.filterSearch = searchValue.value || undefined
    store.loadSkills(1)
  }, 300)
}

function handleSourceSelect(val: string) {
  sourceValue.value = val
  store.filterSource = val || undefined
  store.loadSkills(1)
}

function handleCardClick(id: number) {
  router.push({ name: 'detail', params: { id } })
}

function handleDocGenerated(skillId: number) {
  const skill = store.skills.find(s => s.id === skillId)
  if (skill) skill.is_doc_ready = true
}

async function handleTriggerCrawl() {
  crawling.value = true
  try {
    await store.trigger()
    message.success('爬取任务已触发，请稍后查看')
    setTimeout(() => store.loadSkills(1), 5000)
  } catch {
    message.error('触发爬取失败')
  } finally {
    crawling.value = false
  }
}

function handlePageChange(page: number) {
  store.loadSkills(page)
  window.scrollTo({ top: 0, behavior: 'smooth' })
}
</script>

<template>
  <div class="home">
    <!-- ── 磨砂玻璃导航栏 ── -->
    <header class="nav">
      <div class="nav-inner">
        <div class="nav-brand">
          <div class="brand-icon">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>
            </svg>
          </div>
          <span class="brand-name">Skill Generator</span>
        </div>

        <div class="nav-actions">
          <button
            class="crawl-btn"
            :class="{ loading: crawling }"
            :disabled="crawling"
            @click="handleTriggerCrawl"
          >
            <svg v-if="!crawling" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
              <polyline points="23 4 23 10 17 10"/>
              <path d="M20.49 15a9 9 0 11-2.12-9.36L23 10"/>
            </svg>
            <span v-else class="spin">⟳</span>
            {{ crawling ? '爬取中…' : '立即爬取' }}
          </button>
        </div>
      </div>
    </header>

    <!-- ── Hero 区域 ── -->
    <section class="hero">
      <div class="hero-inner">
        <div class="hero-eyebrow">Daily Discovery</div>
        <h1 class="hero-title">
          发现今日<br>
          <span class="hero-gradient">最实用技能</span>
        </h1>
        <p class="hero-subtitle">
          每日自动抓取 GitHub Trending、Hacker News 等平台<br>
          AI 生成中文文档，一键下载为可用 Skill 包
        </p>

        <!-- 搜索框 -->
        <div class="hero-search">
          <div class="search-box">
            <svg class="search-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
            </svg>
            <input
              v-model="searchValue"
              class="search-input"
              placeholder="搜索技能、工具、框架…"
              @input="handleSearchInput"
            />
            <kbd v-if="!searchValue" class="search-kbd">⌘K</kbd>
            <button v-else class="search-clear" @click="searchValue = ''; handleSearchInput()">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
              </svg>
            </button>
          </div>
        </div>
      </div>

      <!-- 背景装饰 -->
      <div class="hero-bg">
        <div class="hero-orb hero-orb--1" />
        <div class="hero-orb hero-orb--2" />
        <div class="hero-orb hero-orb--3" />
      </div>
    </section>

    <!-- ── 主内容区 ── -->
    <main class="main">
      <div class="main-inner">
        <!-- 来源筛选 pills + 统计 -->
        <div class="filter-row">
          <div class="source-pills">
            <button
              v-for="s in sources"
              :key="s.value"
              class="source-pill"
              :class="{ active: sourceValue === s.value }"
              @click="handleSourceSelect(s.value)"
            >
              {{ s.label }}
            </button>
          </div>
          <div class="stats-label">
            <template v-if="store.loading">
              <span class="loading-dots">加载中</span>
            </template>
            <template v-else>
              <strong>{{ store.total }}</strong> 条技能
            </template>
          </div>
        </div>

        <!-- 技能卡片网格 -->
        <div v-if="!store.loading || store.skills.length > 0" class="cards-grid">
          <SkillCard
            v-for="(skill, idx) in store.skills"
            :key="skill.id"
            :skill="skill"
            :index="idx"
            @click="handleCardClick"
            @doc-generated="handleDocGenerated"
          />
        </div>

        <!-- 骨架屏 Loading -->
        <div v-if="store.loading && store.skills.length === 0" class="skeleton-grid">
          <div v-for="i in 8" :key="i" class="skeleton-card">
            <div class="skeleton-line skeleton-line--short" />
            <div class="skeleton-line" />
            <div class="skeleton-line skeleton-line--medium" />
            <div class="skeleton-line skeleton-line--xs" />
          </div>
        </div>

        <!-- 空状态 -->
        <div v-if="!store.loading && store.skills.length === 0" class="empty-state">
          <div class="empty-icon">
            <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <circle cx="12" cy="12" r="10"/>
              <line x1="12" y1="8" x2="12" y2="12"/>
              <line x1="12" y1="16" x2="12.01" y2="16"/>
            </svg>
          </div>
          <p class="empty-title">暂无技能数据</p>
          <p class="empty-sub">点击「立即爬取」开始获取今日技能</p>
          <button class="crawl-btn crawl-btn--lg" @click="handleTriggerCrawl">
            立即爬取
          </button>
        </div>

        <!-- 分页 -->
        <div v-if="store.total > store.pageSize" class="pagination">
          <button
            class="page-btn"
            :disabled="store.currentPage <= 1"
            @click="handlePageChange(store.currentPage - 1)"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
              <polyline points="15 18 9 12 15 6"/>
            </svg>
          </button>

          <div class="page-numbers">
            <button
              v-for="p in Math.ceil(store.total / store.pageSize)"
              :key="p"
              class="page-num"
              :class="{ active: p === store.currentPage }"
              @click="handlePageChange(p)"
            >
              {{ p }}
            </button>
          </div>

          <button
            class="page-btn"
            :disabled="store.currentPage >= Math.ceil(store.total / store.pageSize)"
            @click="handlePageChange(store.currentPage + 1)"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
              <polyline points="9 18 15 12 9 6"/>
            </svg>
          </button>
        </div>
      </div>
    </main>
  </div>
</template>

<style scoped>
.home {
  min-height: 100vh;
  background: #ffffff;
}

/* ── 导航栏 ── */
.nav {
  position: sticky;
  top: 0;
  z-index: 200;
  background: rgba(255, 255, 255, 0.8);
  backdrop-filter: saturate(180%) blur(20px);
  -webkit-backdrop-filter: saturate(180%) blur(20px);
  border-bottom: 1px solid rgba(0, 0, 0, 0.07);
}

.nav-inner {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 32px;
  height: 52px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.nav-brand {
  display: flex;
  align-items: center;
  gap: 10px;
}

.brand-icon {
  width: 30px;
  height: 30px;
  background: #1d1d1f;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
}

.brand-name {
  font-size: 17px;
  font-weight: 700;
  color: #1d1d1f;
  letter-spacing: -0.02em;
}

.crawl-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 600;
  padding: 7px 16px;
  border-radius: 980px;
  border: none;
  cursor: pointer;
  background: #1d1d1f;
  color: #fff;
  transition: all 0.2s ease;
  letter-spacing: -0.01em;
}

.crawl-btn:hover:not(:disabled) {
  background: #333;
  transform: scale(1.02);
}

.crawl-btn:active {
  transform: scale(0.97);
}

.crawl-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.crawl-btn--lg {
  margin-top: 16px;
  padding: 10px 24px;
  font-size: 15px;
}

.spin {
  display: inline-block;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* ── Hero ── */
.hero {
  position: relative;
  padding: 80px 32px 64px;
  text-align: center;
  overflow: hidden;
}

.hero-inner {
  position: relative;
  z-index: 1;
  max-width: 700px;
  margin: 0 auto;
}

.hero-eyebrow {
  display: inline-block;
  font-size: 13px;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #0071e3;
  margin-bottom: 16px;
  animation: fadeUp 0.6s ease both;
}

.hero-title {
  font-size: clamp(40px, 6vw, 64px);
  font-weight: 700;
  line-height: 1.1;
  letter-spacing: -0.03em;
  color: #1d1d1f;
  margin-bottom: 20px;
  animation: fadeUp 0.6s 0.1s ease both;
}

.hero-gradient {
  background: linear-gradient(135deg, #0071e3 0%, #30a0f0 50%, #5ac8fa 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.hero-subtitle {
  font-size: 17px;
  color: #6e6e73;
  line-height: 1.65;
  margin-bottom: 36px;
  font-weight: 400;
  animation: fadeUp 0.6s 0.2s ease both;
}

/* ── 搜索框 ── */
.hero-search {
  animation: fadeUp 0.6s 0.3s ease both;
}

.search-box {
  position: relative;
  max-width: 520px;
  margin: 0 auto;
}

.search-icon {
  position: absolute;
  left: 16px;
  top: 50%;
  transform: translateY(-50%);
  color: #aeaeb2;
  pointer-events: none;
}

.search-input {
  width: 100%;
  height: 50px;
  padding: 0 50px 0 46px;
  font-size: 15px;
  font-family: inherit;
  background: rgba(0, 0, 0, 0.04);
  border: 1px solid rgba(0, 0, 0, 0.08);
  border-radius: 14px;
  outline: none;
  color: #1d1d1f;
  transition: all 0.25s ease;
}

.search-input::placeholder {
  color: #aeaeb2;
}

.search-input:focus {
  background: #ffffff;
  border-color: #0071e3;
  box-shadow: 0 0 0 4px rgba(0, 113, 227, 0.12);
}

.search-kbd {
  position: absolute;
  right: 14px;
  top: 50%;
  transform: translateY(-50%);
  font-size: 11px;
  font-family: inherit;
  color: #aeaeb2;
  background: rgba(0, 0, 0, 0.05);
  border: 1px solid rgba(0, 0, 0, 0.08);
  border-radius: 5px;
  padding: 2px 6px;
  pointer-events: none;
}

.search-clear {
  position: absolute;
  right: 14px;
  top: 50%;
  transform: translateY(-50%);
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.06);
  border: none;
  border-radius: 50%;
  cursor: pointer;
  color: #6e6e73;
  transition: all 0.15s ease;
}

.search-clear:hover {
  background: rgba(0, 0, 0, 0.1);
}

/* ── Hero 背景装饰 ── */
.hero-bg {
  position: absolute;
  inset: 0;
  pointer-events: none;
  overflow: hidden;
}

.hero-orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(60px);
  opacity: 0.35;
}

.hero-orb--1 {
  width: 500px;
  height: 500px;
  background: radial-gradient(circle, rgba(0, 113, 227, 0.2), transparent 70%);
  top: -200px;
  left: -100px;
  animation: orbFloat 8s ease-in-out infinite;
}

.hero-orb--2 {
  width: 400px;
  height: 400px;
  background: radial-gradient(circle, rgba(90, 200, 250, 0.15), transparent 70%);
  top: -100px;
  right: -80px;
  animation: orbFloat 10s ease-in-out infinite reverse;
}

.hero-orb--3 {
  width: 300px;
  height: 300px;
  background: radial-gradient(circle, rgba(52, 199, 89, 0.1), transparent 70%);
  bottom: -80px;
  left: 40%;
  animation: orbFloat 12s ease-in-out infinite;
}

@keyframes orbFloat {
  0%, 100% { transform: translateY(0px) scale(1); }
  50% { transform: translateY(-20px) scale(1.05); }
}

/* ── 主内容 ── */
.main {
  padding: 0 32px 80px;
}

.main-inner {
  max-width: 1200px;
  margin: 0 auto;
}

/* ── 筛选行 ── */
.filter-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 28px;
  gap: 16px;
}

.source-pills {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.source-pill {
  padding: 6px 16px;
  border-radius: 980px;
  font-size: 13px;
  font-weight: 500;
  border: 1px solid rgba(0, 0, 0, 0.1);
  background: transparent;
  color: #6e6e73;
  cursor: pointer;
  transition: all 0.2s ease;
  letter-spacing: -0.01em;
}

.source-pill:hover {
  background: rgba(0, 0, 0, 0.04);
  color: #1d1d1f;
}

.source-pill.active {
  background: #1d1d1f;
  color: #fff;
  border-color: #1d1d1f;
}

.stats-label {
  font-size: 13px;
  color: #aeaeb2;
  white-space: nowrap;
}

.loading-dots::after {
  content: '...';
  animation: dots 1.2s steps(4, end) infinite;
}

@keyframes dots {
  0%, 20% { content: '.'; }
  40% { content: '..'; }
  60%, 100% { content: '...'; }
}

/* ── 卡片网格 ── */
.cards-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
}

/* ── 骨架屏 ── */
.skeleton-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
}

.skeleton-card {
  background: #f5f5f7;
  border-radius: 18px;
  padding: 20px;
  height: 160px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  animation: shimmer 1.5s ease-in-out infinite;
}

.skeleton-line {
  height: 12px;
  border-radius: 6px;
  background: linear-gradient(90deg, #ebebeb 25%, #f5f5f7 50%, #ebebeb 75%);
  background-size: 200% 100%;
  animation: shimmerLine 1.5s ease-in-out infinite;
  width: 100%;
}

.skeleton-line--short { width: 35%; }
.skeleton-line--medium { width: 70%; }
.skeleton-line--xs { width: 50%; }

@keyframes shimmerLine {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

/* ── 空状态 ── */
.empty-state {
  text-align: center;
  padding: 80px 0;
}

.empty-icon {
  width: 72px;
  height: 72px;
  margin: 0 auto 20px;
  background: #f5f5f7;
  border-radius: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #aeaeb2;
}

.empty-title {
  font-size: 20px;
  font-weight: 600;
  color: #1d1d1f;
  margin-bottom: 6px;
}

.empty-sub {
  font-size: 15px;
  color: #6e6e73;
}

/* ── 分页 ── */
.pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding-top: 48px;
}

.page-btn {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 10px;
  border: 1px solid rgba(0, 0, 0, 0.1);
  background: transparent;
  cursor: pointer;
  color: #1d1d1f;
  transition: all 0.2s ease;
}

.page-btn:hover:not(:disabled) {
  background: rgba(0, 0, 0, 0.04);
}

.page-btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.page-numbers {
  display: flex;
  gap: 4px;
}

.page-num {
  min-width: 36px;
  height: 36px;
  padding: 0 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 10px;
  border: 1px solid transparent;
  background: transparent;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  color: #6e6e73;
  transition: all 0.2s ease;
}

.page-num:hover {
  background: rgba(0, 0, 0, 0.04);
  color: #1d1d1f;
}

.page-num.active {
  background: #1d1d1f;
  color: #fff;
  border-color: #1d1d1f;
}

/* ── 入场动画 ── */
@keyframes fadeUp {
  from {
    opacity: 0;
    transform: translateY(16px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>
