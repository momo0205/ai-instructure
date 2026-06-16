<script setup lang="ts">
import { onMounted, computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useMessage } from 'naive-ui'
import { useSkillStore } from '../stores/skill'
import { downloadSkill } from '../api'
import SkillDoc from '../components/SkillDetail.vue'

const route = useRoute()
const router = useRouter()
const store = useSkillStore()
const message = useMessage()

const skillId = computed(() => Number(route.params.id))
const downloading = ref(false)

onMounted(() => {
  store.loadSkillDetail(skillId.value)
})

const sourceConfig: Record<string, { label: string; color: string; bg: string }> = {
  github: { label: 'GitHub Trending', color: '#1d1d1f', bg: 'rgba(29,29,31,0.06)' },
  hackernews: { label: 'Hacker News', color: '#ff6600', bg: 'rgba(255,102,0,0.08)' },
  devto: { label: 'Dev.to', color: '#3d3d3d', bg: 'rgba(61,61,61,0.06)' },
  producthunt: { label: 'Product Hunt', color: '#da552f', bg: 'rgba(218,85,47,0.08)' },
  skillhub: { label: 'SO Blog', color: '#f48024', bg: 'rgba(244,128,36,0.08)' },
  skillhub_club: { label: 'SkillHub', color: '#7c3aed', bg: 'rgba(124,58,237,0.08)' },
}

const sourceInfo = computed(() => {
  const s = store.currentSkill?.source || ''
  return sourceConfig[s] || { label: s, color: '#6e6e73', bg: 'rgba(110,110,115,0.08)' }
})

const formattedCrawledAt = computed(() => {
  if (!store.currentSkill?.crawled_at) return ''
  return new Date(store.currentSkill.crawled_at).toLocaleDateString('zh-CN', {
    year: 'numeric', month: 'long', day: 'numeric'
  })
})

const formattedDocAt = computed(() => {
  if (!store.currentSkill?.doc_generated_at) return ''
  return new Date(store.currentSkill.doc_generated_at).toLocaleString('zh-CN', {
    month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
  })
})

function goBack() {
  router.push({ name: 'home' })
}

function openSource() {
  if (store.currentSkill?.source_url) {
    window.open(store.currentSkill.source_url, '_blank')
  }
}

async function handleDownload() {
  if (!store.currentSkill || downloading.value) return
  downloading.value = true
  message.loading('正在生成 Skill 指令包，请稍候（约 15-20 秒）…', { duration: 30000 })
  try {
    await downloadSkill(store.currentSkill.id)
    message.destroyAll()
    message.success('Skill 包下载成功！')
  } catch (err: any) {
    message.destroyAll()
    message.error(`下载失败：${err?.response?.data?.detail || '请稍后重试'}`)
  } finally {
    downloading.value = false
  }
}
</script>

<template>
  <div class="detail-page">
    <!-- 导航栏 -->
    <header class="nav">
      <div class="nav-inner">
        <button class="back-btn" @click="goBack">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
            <polyline points="15 18 9 12 15 6"/>
          </svg>
          返回
        </button>
        <div class="nav-brand" @click="goBack" style="cursor: pointer">
          <div class="brand-icon">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>
            </svg>
          </div>
          <span class="brand-name">Skill Generator</span>
        </div>
        <div style="width: 80px" />
      </div>
    </header>

    <!-- 加载中 -->
    <div v-if="store.detailLoading" class="loading-screen">
      <div class="loading-spinner" />
      <p>加载中…</p>
    </div>

    <!-- 不存在 -->
    <div v-else-if="!store.currentSkill" class="not-found">
      <p class="not-found-text">技能不存在或已删除</p>
      <button class="back-btn-lg" @click="goBack">← 返回列表</button>
    </div>

    <!-- 内容 -->
    <template v-else>
      <!-- Hero 区域 -->
      <section class="hero">
        <div class="hero-inner">
          <span
            class="source-badge"
            :style="{ color: sourceInfo.color, background: sourceInfo.bg }"
          >
            {{ sourceInfo.label }}
          </span>
          <h1 class="hero-title">{{ store.currentSkill.title }}</h1>
          <p v-if="store.currentSkill.description" class="hero-desc">
            {{ store.currentSkill.description }}
          </p>

          <div class="hero-meta">
            <template v-if="store.currentSkill.stars">
              <span class="meta-chip">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/>
                </svg>
                {{ store.currentSkill.stars.toLocaleString() }}
              </span>
            </template>
            <template v-if="store.currentSkill.language">
              <span class="meta-chip">{{ store.currentSkill.language }}</span>
            </template>
            <span class="meta-chip meta-chip--date">{{ formattedCrawledAt }}</span>
          </div>
        </div>
        <div class="hero-bg">
          <div class="hero-orb" />
        </div>
      </section>

      <!-- 主内容 -->
      <div class="content-layout">
        <!-- 左侧文档 -->
        <article class="doc-area">
          <div class="doc-card">
            <SkillDoc :skill="store.currentSkill" />
          </div>
        </article>

        <!-- 右侧边栏 -->
        <aside class="sidebar">
          <div class="sidebar-card">
            <h3 class="sidebar-title">基本信息</h3>

            <div class="info-list">
              <div class="info-row">
                <span class="info-label">来源</span>
                <span class="source-badge-sm" :style="{ color: sourceInfo.color }">
                  {{ sourceInfo.label }}
                </span>
              </div>

              <div v-if="store.currentSkill.stars" class="info-row">
                <span class="info-label">Stars</span>
                <span class="info-value">{{ store.currentSkill.stars.toLocaleString() }}</span>
              </div>

              <div v-if="store.currentSkill.language" class="info-row">
                <span class="info-label">语言</span>
                <span class="info-value">{{ store.currentSkill.language }}</span>
              </div>

              <div class="info-row">
                <span class="info-label">爬取于</span>
                <span class="info-value">{{ formattedCrawledAt }}</span>
              </div>

              <div v-if="formattedDocAt" class="info-row">
                <span class="info-label">文档生成</span>
                <span class="info-value">{{ formattedDocAt }}</span>
              </div>

              <div class="info-row">
                <span class="info-label">文档状态</span>
                <span class="status-dot" :class="store.currentSkill.is_doc_ready ? 'ready' : 'pending'">
                  <span class="dot" />
                  {{ store.currentSkill.is_doc_ready ? '已生成' : '待生成' }}
                </span>
              </div>
            </div>

            <div class="sidebar-actions">
              <button class="action-btn action-btn--secondary" @click="openSource">
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                  <path d="M18 13v6a2 2 0 01-2 2H5a2 2 0 01-2-2V8a2 2 0 012-2h6M15 3h6v6M10 14L21 3"/>
                </svg>
                查看原始链接
              </button>

              <button
                class="action-btn action-btn--primary"
                :class="{ loading: downloading }"
                :disabled="downloading"
                @click="handleDownload"
              >
                <svg v-if="!downloading" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                  <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M7 10l5 5 5-5M12 15V3"/>
                </svg>
                <span v-else class="spin">⟳</span>
                {{ downloading ? '生成中…' : '下载 Skill 包' }}
              </button>
            </div>

            <!-- Skill 包说明 -->
            <div class="skill-hint">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="12" r="10"/>
                <line x1="12" y1="8" x2="12" y2="12"/>
                <line x1="12" y1="16" x2="12.01" y2="16"/>
              </svg>
              <span>下载后解压到 <code>~/.codeflicker/skills/</code> 即可在 CodeFlicker 中使用</span>
            </div>
          </div>
        </aside>
      </div>
    </template>
  </div>
</template>

<style scoped>
.detail-page {
  min-height: 100vh;
  background: #ffffff;
}

/* ── 导航 ── */
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

.back-btn {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 14px;
  font-weight: 500;
  color: #0071e3;
  background: none;
  border: none;
  cursor: pointer;
  padding: 6px 10px;
  border-radius: 8px;
  transition: all 0.2s ease;
  width: 80px;
}

.back-btn:hover {
  background: rgba(0, 113, 227, 0.08);
}

.nav-brand {
  display: flex;
  align-items: center;
  gap: 8px;
}

.brand-icon {
  width: 28px;
  height: 28px;
  background: #1d1d1f;
  border-radius: 7px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
}

.brand-name {
  font-size: 16px;
  font-weight: 700;
  color: #1d1d1f;
  letter-spacing: -0.02em;
}

/* ── 加载 / 404 ── */
.loading-screen {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 50vh;
  gap: 16px;
  color: #aeaeb2;
}

.loading-spinner {
  width: 36px;
  height: 36px;
  border: 2.5px solid rgba(0, 0, 0, 0.08);
  border-top-color: #0071e3;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.not-found {
  text-align: center;
  padding: 80px 32px;
}

.not-found-text {
  font-size: 17px;
  color: #6e6e73;
  margin-bottom: 20px;
}

.back-btn-lg {
  font-size: 15px;
  font-weight: 500;
  color: #0071e3;
  background: none;
  border: none;
  cursor: pointer;
}

/* ── Hero ── */
.hero {
  position: relative;
  padding: 56px 32px 48px;
  text-align: center;
  overflow: hidden;
  animation: fadeUp 0.5s ease both;
}

.hero-inner {
  position: relative;
  z-index: 1;
  max-width: 800px;
  margin: 0 auto;
}

.source-badge {
  display: inline-block;
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.02em;
  padding: 4px 12px;
  border-radius: 980px;
  margin-bottom: 16px;
}

.hero-title {
  font-size: clamp(28px, 4vw, 44px);
  font-weight: 700;
  letter-spacing: -0.025em;
  line-height: 1.2;
  color: #1d1d1f;
  margin-bottom: 14px;
}

.hero-desc {
  font-size: 17px;
  color: #6e6e73;
  line-height: 1.6;
  max-width: 600px;
  margin: 0 auto 20px;
}

.hero-meta {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  flex-wrap: wrap;
}

.meta-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 12.5px;
  font-weight: 500;
  color: #6e6e73;
  background: rgba(0, 0, 0, 0.04);
  padding: 4px 10px;
  border-radius: 980px;
}

.meta-chip--date {
  color: #aeaeb2;
}

.hero-bg {
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.hero-orb {
  position: absolute;
  width: 600px;
  height: 300px;
  background: radial-gradient(ellipse, rgba(0, 113, 227, 0.07), transparent 70%);
  top: -50px;
  left: 50%;
  transform: translateX(-50%);
  filter: blur(40px);
}

/* ── 内容布局 ── */
.content-layout {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 32px 80px;
  display: grid;
  grid-template-columns: 1fr 300px;
  gap: 28px;
  align-items: start;
  animation: fadeUp 0.5s 0.1s ease both;
}

@media (max-width: 900px) {
  .content-layout {
    grid-template-columns: 1fr;
  }
  .sidebar {
    order: -1;
  }
}

/* ── 文档区 ── */
.doc-card {
  background: #ffffff;
  border: 1px solid rgba(0, 0, 0, 0.07);
  border-radius: 20px;
  padding: 40px 44px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.04);
}

/* ── 侧边栏 ── */
.sidebar {
  position: sticky;
  top: 72px;
}

.sidebar-card {
  background: rgba(250, 250, 250, 0.9);
  backdrop-filter: saturate(180%) blur(20px);
  -webkit-backdrop-filter: saturate(180%) blur(20px);
  border: 1px solid rgba(0, 0, 0, 0.07);
  border-radius: 20px;
  padding: 24px;
}

.sidebar-title {
  font-size: 13px;
  font-weight: 700;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: #aeaeb2;
  margin-bottom: 18px;
}

.info-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 24px;
}

.info-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
}

.info-label {
  font-size: 13px;
  color: #aeaeb2;
  font-weight: 500;
  flex-shrink: 0;
}

.info-value {
  font-size: 13px;
  color: #1d1d1f;
  font-weight: 500;
  text-align: right;
}

.source-badge-sm {
  font-size: 12.5px;
  font-weight: 600;
}

.status-dot {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 12.5px;
  font-weight: 600;
}

.status-dot .dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #aeaeb2;
}

.status-dot.ready .dot {
  background: #34c759;
  box-shadow: 0 0 0 3px rgba(52, 199, 89, 0.15);
}

.status-dot.ready {
  color: #34c759;
}

.status-dot.pending {
  color: #ff9f0a;
}

.status-dot.pending .dot {
  background: #ff9f0a;
}

/* ── 侧边栏操作按钮 ── */
.sidebar-actions {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-bottom: 16px;
}

.action-btn {
  width: 100%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 7px;
  font-size: 14px;
  font-weight: 600;
  padding: 11px 20px;
  border-radius: 12px;
  border: none;
  cursor: pointer;
  transition: all 0.2s ease;
  letter-spacing: -0.01em;
  font-family: inherit;
}

.action-btn:active {
  transform: scale(0.97);
}

.action-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.action-btn--secondary {
  background: rgba(0, 0, 0, 0.05);
  color: #1d1d1f;
  border: 1px solid rgba(0, 0, 0, 0.08);
}

.action-btn--secondary:hover:not(:disabled) {
  background: rgba(0, 0, 0, 0.08);
}

.action-btn--primary {
  background: #0071e3;
  color: #ffffff;
}

.action-btn--primary:hover:not(:disabled) {
  background: #0077ed;
  box-shadow: 0 6px 20px rgba(0, 113, 227, 0.35);
  transform: translateY(-1px);
}

.spin {
  display: inline-block;
  animation: spin 0.8s linear infinite;
}

/* ── Skill 说明提示 ── */
.skill-hint {
  display: flex;
  align-items: flex-start;
  gap: 7px;
  font-size: 11.5px;
  color: #aeaeb2;
  line-height: 1.5;
  padding: 12px;
  background: rgba(0, 0, 0, 0.02);
  border-radius: 10px;
}

.skill-hint svg {
  flex-shrink: 0;
  margin-top: 1px;
}

.skill-hint code {
  font-family: 'SF Mono', Menlo, monospace;
  font-size: 10.5px;
  background: rgba(0, 0, 0, 0.05);
  padding: 1px 4px;
  border-radius: 4px;
  color: #1d1d1f;
}

/* ── 动画 ── */
@keyframes fadeUp {
  from { opacity: 0; transform: translateY(12px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>
