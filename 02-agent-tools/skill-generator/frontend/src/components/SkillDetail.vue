<script setup lang="ts">
import { computed } from 'vue'
import { marked } from 'marked'
import { markedHighlight } from 'marked-highlight'
import hljs from 'highlight.js'
import type { SkillDetail } from '../api'

const props = defineProps<{
  skill: SkillDetail
}>()

// 配置 marked
marked.use(
  markedHighlight({
    highlight(code: string, lang: string) {
      if (lang && hljs.getLanguage(lang)) {
        return hljs.highlight(code, { language: lang }).value
      }
      return hljs.highlightAuto(code).value
    },
  })
)
marked.use({ breaks: true })

const renderedHtml = computed(() => {
  if (!props.skill.doc_markdown) {
    return `<div class="no-doc">
      <p>文档尚未生成</p>
      <p class="no-doc-sub">点击卡片上的「AI 生成文档」按钮生成</p>
    </div>`
  }
  return marked.parse(props.skill.doc_markdown) as string
})
</script>

<template>
  <div class="skill-doc">
    <div class="markdown-body" v-html="renderedHtml" />
  </div>
</template>

<style>
/* highlight.js Apple 风格配色（非 scoped，hljs 类在 shadow DOM 外） */
.hljs {
  background: #f5f5f7 !important;
  color: #1d1d1f !important;
}
.hljs-keyword { color: #ad3da4 !important; }
.hljs-string { color: #c41a16 !important; }
.hljs-comment { color: #707070 !important; font-style: italic; }
.hljs-number { color: #1c00cf !important; }
.hljs-function { color: #3900a4 !important; }
.hljs-title { color: #3900a4 !important; }
.hljs-built_in { color: #3900a4 !important; }
.hljs-attr { color: #0070c9 !important; }
</style>

<style scoped>
.skill-doc {
  font-family: -apple-system, 'SF Pro Text', 'Helvetica Neue', 'PingFang SC', sans-serif;
}

/* 无文档状态 */
:deep(.no-doc) {
  text-align: center;
  padding: 48px 0;
  color: #aeaeb2;
}

:deep(.no-doc p) {
  font-size: 16px;
  font-weight: 500;
  margin-bottom: 8px;
  color: #6e6e73;
}

:deep(.no-doc-sub) {
  font-size: 14px !important;
  color: #aeaeb2 !important;
}

/* ── Markdown 主体 ── */
.markdown-body {
  font-size: 16px;
  line-height: 1.75;
  color: #1d1d1f;
  -webkit-font-smoothing: antialiased;
}

/* H1 */
.markdown-body :deep(h1) {
  font-size: 32px;
  font-weight: 700;
  letter-spacing: -0.025em;
  line-height: 1.2;
  color: #1d1d1f;
  margin-bottom: 8px;
  padding-bottom: 20px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.07);
}

/* H2 */
.markdown-body :deep(h2) {
  font-size: 22px;
  font-weight: 700;
  letter-spacing: -0.02em;
  color: #1d1d1f;
  margin-top: 40px;
  margin-bottom: 14px;
  padding-left: 14px;
  border-left: 3px solid #0071e3;
}

/* H3 */
.markdown-body :deep(h3) {
  font-size: 17px;
  font-weight: 600;
  letter-spacing: -0.01em;
  color: #1d1d1f;
  margin-top: 28px;
  margin-bottom: 10px;
}

/* H4+ */
.markdown-body :deep(h4),
.markdown-body :deep(h5),
.markdown-body :deep(h6) {
  font-size: 15px;
  font-weight: 600;
  color: #1d1d1f;
  margin-top: 20px;
  margin-bottom: 8px;
}

/* 段落 */
.markdown-body :deep(p) {
  margin-bottom: 16px;
  color: #3a3a3c;
}

/* 列表 */
.markdown-body :deep(ul),
.markdown-body :deep(ol) {
  padding-left: 24px;
  margin-bottom: 16px;
}

.markdown-body :deep(li) {
  margin-bottom: 6px;
  color: #3a3a3c;
}

.markdown-body :deep(ul li::marker) {
  color: #0071e3;
}

/* 行内代码 */
.markdown-body :deep(code) {
  font-family: 'SF Mono', 'JetBrains Mono', Menlo, Consolas, monospace;
  font-size: 13.5px;
  background: rgba(0, 0, 0, 0.04);
  border: 1px solid rgba(0, 0, 0, 0.06);
  color: #c41a16;
  padding: 2px 6px;
  border-radius: 6px;
}

/* 代码块 */
.markdown-body :deep(pre) {
  background: #f5f5f7;
  border: 1px solid rgba(0, 0, 0, 0.06);
  border-radius: 14px;
  padding: 20px 22px;
  overflow-x: auto;
  margin-bottom: 20px;
  position: relative;
}

.markdown-body :deep(pre code) {
  background: none;
  border: none;
  color: inherit;
  padding: 0;
  font-size: 13.5px;
  line-height: 1.65;
}

/* 引用块 */
.markdown-body :deep(blockquote) {
  margin: 20px 0;
  padding: 16px 20px;
  background: rgba(0, 113, 227, 0.04);
  border-left: 3px solid #0071e3;
  border-radius: 0 12px 12px 0;
  color: #3a3a3c;
}

.markdown-body :deep(blockquote p) {
  margin-bottom: 0;
  font-style: italic;
}

/* 链接 */
.markdown-body :deep(a) {
  color: #0071e3;
  text-decoration: none;
  font-weight: 500;
  border-bottom: 1px solid rgba(0, 113, 227, 0.2);
  transition: border-color 0.2s ease;
}

.markdown-body :deep(a:hover) {
  border-bottom-color: #0071e3;
}

/* 分割线 */
.markdown-body :deep(hr) {
  border: none;
  height: 1px;
  background: rgba(0, 0, 0, 0.07);
  margin: 32px 0;
}

/* 表格 */
.markdown-body :deep(table) {
  width: 100%;
  border-collapse: collapse;
  margin-bottom: 20px;
  font-size: 14.5px;
  border-radius: 12px;
  overflow: hidden;
  border: 1px solid rgba(0, 0, 0, 0.07);
}

.markdown-body :deep(th) {
  background: rgba(0, 0, 0, 0.03);
  font-weight: 600;
  color: #1d1d1f;
  padding: 10px 16px;
  text-align: left;
  border-bottom: 1px solid rgba(0, 0, 0, 0.07);
}

.markdown-body :deep(td) {
  padding: 10px 16px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.04);
  color: #3a3a3c;
}

.markdown-body :deep(tr:last-child td) {
  border-bottom: none;
}

.markdown-body :deep(tr:hover td) {
  background: rgba(0, 0, 0, 0.015);
}

/* strong / em */
.markdown-body :deep(strong) {
  font-weight: 700;
  color: #1d1d1f;
}

.markdown-body :deep(em) {
  font-style: italic;
  color: #3a3a3c;
}
</style>
