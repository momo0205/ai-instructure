<script setup lang="ts">
import { NConfigProvider, NMessageProvider, zhCN, dateZhCN } from 'naive-ui'
import { RouterView } from 'vue-router'
</script>

<template>
  <NConfigProvider :locale="zhCN" :date-locale="dateZhCN">
    <NMessageProvider placement="top">
      <RouterView v-slot="{ Component }">
        <Transition name="page" mode="out-in">
          <component :is="Component" />
        </Transition>
      </RouterView>
    </NMessageProvider>
  </NConfigProvider>
</template>

<style>
/* ── Apple 设计系统：全局基础 ── */
*, *::before, *::after {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

:root {
  --apple-bg: #ffffff;
  --apple-bg-secondary: #f5f5f7;
  --apple-bg-tertiary: #fafafa;
  --apple-text-primary: #1d1d1f;
  --apple-text-secondary: #6e6e73;
  --apple-text-tertiary: #aeaeb2;
  --apple-accent: #0071e3;
  --apple-accent-hover: #0077ed;
  --apple-success: #34c759;
  --apple-warning: #ff9f0a;
  --apple-danger: #ff3b30;
  --apple-border: rgba(0, 0, 0, 0.08);
  --apple-border-strong: rgba(0, 0, 0, 0.12);
  --apple-shadow-sm: 0 2px 8px rgba(0, 0, 0, 0.06);
  --apple-shadow-md: 0 4px 20px rgba(0, 0, 0, 0.08);
  --apple-shadow-lg: 0 12px 40px rgba(0, 0, 0, 0.12);
  --apple-radius-sm: 8px;
  --apple-radius-md: 14px;
  --apple-radius-lg: 20px;
  --apple-radius-xl: 28px;
  --apple-blur: saturate(180%) blur(20px);
  --transition-fast: 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  --transition-base: 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  --transition-slow: 0.5s cubic-bezier(0.4, 0, 0.2, 1);
  --transition-spring: 0.4s cubic-bezier(0.34, 1.56, 0.64, 1);
}

html {
  scroll-behavior: smooth;
}

body {
  font-family: -apple-system, 'SF Pro Display', 'SF Pro Text', BlinkMacSystemFont,
    'Helvetica Neue', 'PingFang SC', 'Hiragino Sans GB', sans-serif;
  /* 默认黑色背景，深色 landing 页不闪白 */
  background-color: #000000;
  color: var(--apple-text-primary);
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  font-feature-settings: 'kern' 1;
}

/* ── 页面过渡动画（landing ↔ home 丝滑切换）── */
.page-enter-active {
  transition: opacity 0.4s cubic-bezier(0.4, 0, 0.2, 1),
              transform 0.4s cubic-bezier(0.34, 1.2, 0.64, 1);
}
.page-leave-active {
  transition: opacity 0.3s cubic-bezier(0.4, 0, 0.2, 1),
              transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}
.page-enter-from {
  opacity: 0;
  transform: translateY(16px) scale(0.99);
}
.page-leave-to {
  opacity: 0;
  transform: translateY(-8px) scale(1.005);
}

/* ── 列表交错入场 ── */
.card-list-enter-active {
  transition: opacity var(--transition-base), transform var(--transition-spring);
}
.card-list-enter-from {
  opacity: 0;
  transform: translateY(20px) scale(0.97);
}

/* ── 滚动条美化 ── */
::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}
::-webkit-scrollbar-track {
  background: transparent;
}
::-webkit-scrollbar-thumb {
  background: rgba(0, 0, 0, 0.15);
  border-radius: 3px;
}
::-webkit-scrollbar-thumb:hover {
  background: rgba(0, 0, 0, 0.25);
}

/* ── 文字选中颜色 ── */
::selection {
  background: rgba(0, 113, 227, 0.15);
  color: inherit;
}

/* ── 覆盖 Naive UI 全局主题 ── */
.n-card {
  border-radius: var(--apple-radius-md) !important;
  border: 1px solid var(--apple-border) !important;
  box-shadow: var(--apple-shadow-sm) !important;
}

.n-button {
  border-radius: 980px !important;
  font-weight: 500 !important;
  letter-spacing: -0.01em !important;
}

.n-input {
  border-radius: var(--apple-radius-sm) !important;
}

.n-select .n-base-selection {
  border-radius: var(--apple-radius-sm) !important;
}

.n-tag {
  font-weight: 500 !important;
}
</style>
