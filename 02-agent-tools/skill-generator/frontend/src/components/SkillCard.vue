<script setup lang="ts">
import { computed, ref } from 'vue'
import { useMessage } from 'naive-ui'
import { generateSkillDoc, downloadSkill } from '../api'
import type { SkillListItem } from '../api'

const props = defineProps<{
  skill: SkillListItem
  index?: number
}>()

const emit = defineEmits<{
  (e: 'click', id: number): void
  (e: 'doc-generated', id: number): void
}>()

const message = useMessage()
const generating = ref(false)
const downloading = ref(false)

const sourceConfig: Record<string, { label: string; color: string; bg: string }> = {
  github: { label: 'GitHub', color: '#1d1d1f', bg: 'rgba(29,29,31,0.06)' },
  hackernews: { label: 'HN', color: '#ff6600', bg: 'rgba(255,102,0,0.08)' },
  devto: { label: 'Dev.to', color: '#3d3d3d', bg: 'rgba(61,61,61,0.06)' },
  producthunt: { label: 'PH', color: '#da552f', bg: 'rgba(218,85,47,0.08)' },
  skillhub: { label: 'SO Blog', color: '#f48024', bg: 'rgba(244,128,36,0.08)' },
  skillhub_club: { label: 'SkillHub', color: '#7c3aed', bg: 'rgba(124,58,237,0.08)' },
}

const sourceInfo = computed(
  () => sourceConfig[props.skill.source] || { label: props.skill.source, color: '#6e6e73', bg: 'rgba(110,110,115,0.08)' }
)

const parsedTags = computed(() => {
  if (!props.skill.tags) return []
  try {
    return JSON.parse(props.skill.tags).filter(Boolean).slice(0, 2)
  } catch {
    return []
  }
})

const formattedDate = computed(() => {
  const d = new Date(props.skill.crawled_at)
  return `${d.getMonth() + 1}/${d.getDate()}`
})

const animDelay = computed(() => `${(props.index ?? 0) * 40}ms`)

async function handleGenerateDoc(e: MouseEvent) {
  e.stopPropagation()
  if (generating.value) return
  generating.value = true
  try {
    await generateSkillDoc(props.skill.id)
    message.success(`「${props.skill.title.slice(0, 20)}」文档生成成功！`)
    emit('doc-generated', props.skill.id)
  } catch (err: any) {
    message.error(`文档生成失败：${err?.response?.data?.detail || '请稍后重试'}`)
  } finally {
    generating.value = false
  }
}

function handleDownload(e: MouseEvent) {
  e.stopPropagation()
  if (downloading.value) return
  downloading.value = true
  message.loading(`正在生成 Skill 包…`, { duration: 30000 })
  downloadSkill(props.skill.id)
    .then(() => {
      message.destroyAll()
      message.success(`Skill 包下载成功！`)
    })
    .catch((err: any) => {
      message.destroyAll()
      message.error(`下载失败：${err?.response?.data?.detail || '请稍后重试'}`)
    })
    .finally(() => { downloading.value = false })
}
</script>

<template>
  <div
    class="skill-card"
    :style="{ '--delay': animDelay }"
    @click="emit('click', skill.id)"
  >
    <!-- 悬浮光晕 -->
    <div class="card-glow" />

    <!-- 卡片内容 -->
    <div class="card-inner">
      <!-- 顶部：来源 badge + 日期 -->
      <div class="card-top">
        <span class="source-badge" :style="{ color: sourceInfo.color, background: sourceInfo.bg }">
          {{ sourceInfo.label }}
        </span>
        <span class="card-date">{{ formattedDate }}</span>
      </div>

      <!-- 标题 -->
      <h3 class="card-title">{{ skill.title }}</h3>

      <!-- 描述 -->
      <p class="card-desc">{{ skill.description || '暂无描述' }}</p>

      <!-- 底部：stars / tags / 操作 -->
      <div class="card-bottom">
        <div class="card-meta">
          <template v-if="skill.stars">
            <span class="stars">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor">
                <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/>
              </svg>
              {{ skill.stars >= 1000 ? `${(skill.stars / 1000).toFixed(1)}k` : skill.stars }}
            </span>
          </template>
          <template v-if="skill.language">
            <span class="lang-tag">{{ skill.language }}</span>
          </template>
          <template v-for="tag in parsedTags" :key="tag">
            <span class="topic-tag">{{ tag }}</span>
          </template>
        </div>

        <!-- 操作区 -->
        <div class="card-actions" @click.stop>
          <template v-if="!skill.is_doc_ready">
            <button
              class="action-btn action-btn--generate"
              :class="{ loading: generating }"
              :disabled="generating"
              @click="handleGenerateDoc"
            >
              <svg v-if="!generating" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                <path d="M12 2l2.4 7.4H22l-6.2 4.5 2.4 7.4L12 17 5.8 21.3l2.4-7.4L2 9.4h7.6z"/>
              </svg>
              <span class="spin-icon" v-else>⟳</span>
              {{ generating ? '生成中' : 'AI 生成' }}
            </button>
          </template>
          <template v-else>
            <span class="ready-badge">
              <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3">
                <polyline points="20 6 9 17 4 12"/>
              </svg>
              就绪
            </span>
            <button
              class="action-btn action-btn--download"
              :class="{ loading: downloading }"
              :disabled="downloading"
              @click="handleDownload"
            >
              <svg v-if="!downloading" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M7 10l5 5 5-5M12 15V3"/>
              </svg>
              <span class="spin-icon" v-else>⟳</span>
              {{ downloading ? '…' : '下载' }}
            </button>
          </template>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* ── 入场动画 ── */
.skill-card {
  animation: cardIn 0.5s cubic-bezier(0.34, 1.56, 0.64, 1) both;
  animation-delay: var(--delay, 0ms);
}

@keyframes cardIn {
  from {
    opacity: 0;
    transform: translateY(24px) scale(0.96);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

/* ── 卡片基础 ── */
.skill-card {
  position: relative;
  cursor: pointer;
  border-radius: 18px;
  background: #ffffff;
  border: 1px solid rgba(0, 0, 0, 0.07);
  transition:
    transform 0.35s cubic-bezier(0.34, 1.56, 0.64, 1),
    box-shadow 0.35s cubic-bezier(0.4, 0, 0.2, 1),
    border-color 0.3s ease;
  overflow: hidden;
  will-change: transform;
}

.skill-card:hover {
  transform: translateY(-5px) scale(1.01);
  box-shadow:
    0 20px 60px rgba(0, 0, 0, 0.1),
    0 6px 20px rgba(0, 0, 0, 0.06);
  border-color: rgba(0, 0, 0, 0.12);
}

.skill-card:active {
  transform: translateY(-2px) scale(0.995);
  transition-duration: 0.12s;
}

/* ── 光晕效果 ── */
.card-glow {
  position: absolute;
  inset: -1px;
  border-radius: 18px;
  background: radial-gradient(
    circle at 50% 0%,
    rgba(0, 113, 227, 0.06) 0%,
    transparent 60%
  );
  opacity: 0;
  transition: opacity 0.4s ease;
  pointer-events: none;
}

.skill-card:hover .card-glow {
  opacity: 1;
}

/* ── 内容区 ── */
.card-inner {
  padding: 18px 20px 16px;
}

/* ── 顶部 ── */
.card-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.source-badge {
  display: inline-flex;
  align-items: center;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.02em;
  padding: 3px 9px;
  border-radius: 980px;
  line-height: 1.6;
}

.card-date {
  font-size: 11px;
  color: #aeaeb2;
  font-weight: 400;
}

/* ── 标题 ── */
.card-title {
  font-size: 15px;
  font-weight: 600;
  line-height: 1.45;
  color: #1d1d1f;
  margin-bottom: 8px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  letter-spacing: -0.01em;
}

/* ── 描述 ── */
.card-desc {
  font-size: 12.5px;
  color: #6e6e73;
  line-height: 1.6;
  margin-bottom: 14px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* ── 底部 ── */
.card-bottom {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
}

/* ── 元信息 ── */
.card-meta {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
  flex: 1;
  min-width: 0;
}

.stars {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  font-size: 11.5px;
  color: #6e6e73;
  font-weight: 500;
}

.lang-tag,
.topic-tag {
  font-size: 11px;
  padding: 2px 7px;
  border-radius: 980px;
  font-weight: 500;
}

.lang-tag {
  background: rgba(0, 0, 0, 0.05);
  color: #1d1d1f;
}

.topic-tag {
  background: rgba(0, 113, 227, 0.07);
  color: #0071e3;
}

/* ── 操作区 ── */
.card-actions {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
}

.ready-badge {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  font-size: 11px;
  font-weight: 600;
  color: #34c759;
  background: rgba(52, 199, 89, 0.08);
  padding: 3px 8px;
  border-radius: 980px;
}

.action-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 11.5px;
  font-weight: 600;
  padding: 4px 11px;
  border-radius: 980px;
  border: none;
  cursor: pointer;
  transition: all 0.2s ease;
  letter-spacing: -0.01em;
  white-space: nowrap;
}

.action-btn:active {
  transform: scale(0.94);
}

.action-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.action-btn--generate {
  background: #0071e3;
  color: #fff;
}

.action-btn--generate:hover:not(:disabled) {
  background: #0077ed;
  box-shadow: 0 4px 12px rgba(0, 113, 227, 0.35);
}

.action-btn--download {
  background: rgba(0, 0, 0, 0.05);
  color: #1d1d1f;
  border: 1px solid rgba(0, 0, 0, 0.1);
}

.action-btn--download:hover:not(:disabled) {
  background: rgba(0, 0, 0, 0.09);
}

.spin-icon {
  display: inline-block;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>
