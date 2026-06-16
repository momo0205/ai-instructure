<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

// ── 鼠标追踪光晕 ──
const mouseX = ref(50)
const mouseY = ref(50)

function handleMouseMove(e: MouseEvent) {
  mouseX.value = (e.clientX / window.innerWidth) * 100
  mouseY.value = (e.clientY / window.innerHeight) * 100
}

// ── 滚动驱动动画 ──
const heroVisible = ref(false)
const featuresVisible = ref(false)
const sourcesVisible = ref(false)
const ctaVisible = ref(false)

// ── 特性卡片数据 ──
const features = [
  {
    icon: '⚡',
    title: '每日自动爬取',
    desc: '每天自动抓取 GitHub Trending、Hacker News、Dev.to、Product Hunt、SkillHub 最新内容，无需人工干预',
    color: '#ffd60a',
  },
  {
    icon: '🧠',
    title: 'AI 深度理解',
    desc: '基于 DeepSeek 大模型，深度分析原文，提炼真实操作步骤、安装命令、触发场景，拒绝幻觉创作',
    color: '#0affef',
  },
  {
    icon: '📦',
    title: '一键打包下载',
    desc: '自动生成标准格式的 Skill 包，解压即用。兼容 CodeFlicker、Cursor、Claude Code 等主流 AI 编程助手',
    color: '#bf5af2',
  },
  {
    icon: '🔍',
    title: '智能搜索过滤',
    desc: '按来源、关键词过滤，评分体系筛选高质量内容，让你只看到真正有价值的技能',
    color: '#34c759',
  },
]

const sources = [
  { name: 'GitHub', desc: 'README 全文', icon: '◎', color: '#e8e8e8' },
  { name: 'HN', desc: 'Show/Ask HN', icon: '▲', color: '#ff6600' },
  { name: 'Dev.to', desc: '完整文章正文', icon: '✦', color: '#7aa2f7' },
  { name: 'PH', desc: 'Product Hunt', icon: '●', color: '#da552f' },
  { name: 'SO Blog', desc: 'Stack Overflow 博客', icon: '◆', color: '#f48024' },
  { name: 'SkillHub', desc: 'AI Skill 市集', icon: '★', color: '#bf5af2' },
]

// ── Canvas 粒子背景 ──
const canvasRef = ref<HTMLCanvasElement | null>(null)
let animFrameId = 0

function initCanvas() {
  const canvas = canvasRef.value
  if (!canvas) return
  const ctx = canvas.getContext('2d')!
  canvas.width = window.innerWidth
  canvas.height = window.innerHeight

  const particles: Array<{
    x: number; y: number; vx: number; vy: number;
    size: number; opacity: number; hue: number;
  }> = []

  const PARTICLE_COUNT = 80
  for (let i = 0; i < PARTICLE_COUNT; i++) {
    particles.push({
      x: Math.random() * canvas.width,
      y: Math.random() * canvas.height,
      vx: (Math.random() - 0.5) * 0.3,
      vy: (Math.random() - 0.5) * 0.3,
      size: Math.random() * 1.5 + 0.5,
      opacity: Math.random() * 0.5 + 0.1,
      hue: Math.random() > 0.5 ? 210 : 270, // 蓝紫双色
    })
  }

  const W = canvas.width
  const H = canvas.height

  function draw() {
    ctx.clearRect(0, 0, W, H)

    // 绘制粒子
    for (const p of particles) {
      p.x += p.vx
      p.y += p.vy
      if (p.x < 0) p.x = W
      if (p.x > W) p.x = 0
      if (p.y < 0) p.y = H
      if (p.y > H) p.y = 0

      ctx.beginPath()
      ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2)
      ctx.fillStyle = `hsla(${p.hue}, 80%, 70%, ${p.opacity})`
      ctx.fill()
    }

    // 绘制连线
    for (let i = 0; i < particles.length; i++) {
      for (let j = i + 1; j < particles.length; j++) {
        const dx = particles[i].x - particles[j].x
        const dy = particles[i].y - particles[j].y
        const dist = Math.sqrt(dx * dx + dy * dy)
        if (dist < 120) {
          ctx.beginPath()
          ctx.moveTo(particles[i].x, particles[i].y)
          ctx.lineTo(particles[j].x, particles[j].y)
          ctx.strokeStyle = `rgba(120, 160, 255, ${0.08 * (1 - dist / 120)})`
          ctx.lineWidth = 0.5
          ctx.stroke()
        }
      }
    }

    animFrameId = requestAnimationFrame(draw)
  }
  draw()
}

// ── Intersection Observer 触发入场 ──
let observers: IntersectionObserver[] = []

function observeSection(id: string, visibleRef: { value: boolean }) {
  const el = document.getElementById(id)
  if (!el) return
  const obs = new IntersectionObserver(
    ([entry]) => { if (entry.isIntersecting) visibleRef.value = true },
    { threshold: 0.15 }
  )
  obs.observe(el)
  observers.push(obs)
}

function handleEnter() {
  router.push({ name: 'home' })
}

onMounted(() => {
  window.addEventListener('mousemove', handleMouseMove)
  initCanvas()
  // 略微延迟，等 CSS transition 生效后触发 Hero 入场
  setTimeout(() => { heroVisible.value = true }, 100)
  observeSection('features-section', featuresVisible)
  observeSection('sources-section', sourcesVisible)
  observeSection('cta-section', ctaVisible)
})

onUnmounted(() => {
  window.removeEventListener('mousemove', handleMouseMove)
  cancelAnimationFrame(animFrameId)
  observers.forEach(o => o.disconnect())
})
</script>

<template>
  <div class="landing" @mousemove="handleMouseMove">
    <!-- ── Canvas 粒子背景 ── -->
    <canvas ref="canvasRef" class="particle-canvas" />

    <!-- ── 全局追踪光晕 ── -->
    <div
      class="mouse-glow"
      :style="{
        background: `radial-gradient(600px circle at ${mouseX}% ${mouseY}%, rgba(120,100,255,0.07), transparent 60%)`
      }"
    />

    <!-- ════════════════════════════════════════════════════
         SECTION 1: Hero
    ════════════════════════════════════════════════════ -->
    <section class="hero-section">
      <!-- 背景装饰层 -->
      <div class="bg-grid" />
      <div class="bg-orb bg-orb--blue" />
      <div class="bg-orb bg-orb--purple" />
      <div class="bg-orb bg-orb--cyan" />

      <div class="hero-content" :class="{ visible: heroVisible }">
        <!-- 小徽章 -->
        <div class="hero-badge">
          <span class="badge-dot" />
          <span>每日自动更新 · AI 驱动</span>
        </div>

        <!-- 主标题 -->
        <h1 class="hero-title">
          <span class="title-line line-1">发现今日最</span>
          <span class="title-line line-2">
            <span class="gradient-text">前沿 AI Skill</span>
          </span>
          <span class="title-line line-3">自动生成，即刻可用</span>
        </h1>

        <!-- 副标题 -->
        <p class="hero-subtitle">
          每天从 6 大平台自动爬取，AI 深度分析并提炼为标准 Skill 包<br>
          安装到 Claude Code、Cursor、CodeFlicker，让 AI 更懂你的工作
        </p>

        <!-- CTA 按钮组 -->
        <div class="hero-actions">
          <button class="btn btn--primary" @click="handleEnter">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
              <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>
            </svg>
            开始探索
          </button>
          <a class="btn btn--ghost" href="#features-section">
            了解更多
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
              <polyline points="6 9 12 15 18 9"/>
            </svg>
          </a>
        </div>

        <!-- 数据统计 -->
        <div class="hero-stats">
          <div class="stat">
            <span class="stat-num">6</span>
            <span class="stat-label">数据来源</span>
          </div>
          <div class="stat-divider" />
          <div class="stat">
            <span class="stat-num">每日</span>
            <span class="stat-label">自动爬取</span>
          </div>
          <div class="stat-divider" />
          <div class="stat">
            <span class="stat-num">100%</span>
            <span class="stat-label">真实内容</span>
          </div>
        </div>
      </div>

      <!-- 向下滚动提示 -->
      <div class="scroll-hint" :class="{ visible: heroVisible }">
        <div class="scroll-line" />
        <span>向下滚动</span>
      </div>
    </section>

    <!-- ════════════════════════════════════════════════════
         SECTION 2: 核心能力
    ════════════════════════════════════════════════════ -->
    <section id="features-section" class="features-section">
      <div class="section-inner" :class="{ visible: featuresVisible }">
        <div class="section-header">
          <span class="section-eyebrow">Core Capabilities</span>
          <h2 class="section-title">为什么选择 Skill Generator？</h2>
          <p class="section-desc">不只是爬虫，而是一条从「信息」到「可用技能」的完整流水线</p>
        </div>

        <div class="features-grid">
          <div
            v-for="(feat, i) in features"
            :key="i"
            class="feature-card"
            :style="{ '--delay': `${i * 100}ms`, '--accent': feat.color }"
          >
            <div class="feature-icon">{{ feat.icon }}</div>
            <h3 class="feature-title">{{ feat.title }}</h3>
            <p class="feature-desc">{{ feat.desc }}</p>
            <div class="feature-glow" />
          </div>
        </div>
      </div>
    </section>

    <!-- ════════════════════════════════════════════════════
         SECTION 3: 数据来源展示
    ════════════════════════════════════════════════════ -->
    <section id="sources-section" class="sources-section">
      <div class="section-inner" :class="{ visible: sourcesVisible }">
        <div class="section-header">
          <span class="section-eyebrow">Data Sources</span>
          <h2 class="section-title">来自全球最优质的技术社区</h2>
          <p class="section-desc">每个来源都经过精心筛选，确保内容密度和技术价值</p>
        </div>

        <div class="sources-flow">
          <div
            v-for="(src, i) in sources"
            :key="i"
            class="source-chip"
            :style="{ '--delay': `${i * 80}ms`, '--color': src.color }"
          >
            <span class="source-icon" :style="{ color: src.color }">{{ src.icon }}</span>
            <div>
              <div class="source-name">{{ src.name }}</div>
              <div class="source-desc">{{ src.desc }}</div>
            </div>
          </div>
        </div>

        <!-- 流程示意 -->
        <div class="pipeline">
          <div class="pipeline-step">
            <div class="step-num">01</div>
            <div class="step-text">爬取原文内容</div>
          </div>
          <div class="pipeline-arrow">→</div>
          <div class="pipeline-step">
            <div class="step-num">02</div>
            <div class="step-text">AI 深度分析</div>
          </div>
          <div class="pipeline-arrow">→</div>
          <div class="pipeline-step">
            <div class="step-num">03</div>
            <div class="step-text">生成 Skill 包</div>
          </div>
          <div class="pipeline-arrow">→</div>
          <div class="pipeline-step">
            <div class="step-num">04</div>
            <div class="step-text">一键安装使用</div>
          </div>
        </div>
      </div>
    </section>

    <!-- ════════════════════════════════════════════════════
         SECTION 4: CTA
    ════════════════════════════════════════════════════ -->
    <section id="cta-section" class="cta-section">
      <div class="cta-inner" :class="{ visible: ctaVisible }">
        <div class="cta-glow" />
        <h2 class="cta-title">准备好了吗？</h2>
        <p class="cta-subtitle">开始发现今日最新、最实用的 AI 技能</p>
        <button class="btn btn--primary btn--lg" @click="handleEnter">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
            <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>
          </svg>
          立即开始探索
        </button>
        <p class="cta-hint">无需注册 · 完全免费 · 每日更新</p>
      </div>
    </section>
  </div>
</template>

<style scoped>
/* ════════════════════════════════════════════════════
   基础 / 全局
════════════════════════════════════════════════════ */
.landing {
  min-height: 100vh;
  background: #000000;
  color: #f5f5f7;
  overflow-x: hidden;
  position: relative;
}

.particle-canvas {
  position: fixed;
  inset: 0;
  z-index: 0;
  pointer-events: none;
}

.mouse-glow {
  position: fixed;
  inset: 0;
  z-index: 1;
  pointer-events: none;
  transition: background 0.1s ease;
}

/* ════════════════════════════════════════════════════
   HERO SECTION
════════════════════════════════════════════════════ */
.hero-section {
  position: relative;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 0 24px;
  overflow: hidden;
  z-index: 2;
}

/* 网格背景 */
.bg-grid {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(255,255,255,0.025) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255,255,255,0.025) 1px, transparent 1px);
  background-size: 60px 60px;
  mask-image: radial-gradient(ellipse 80% 80% at 50% 50%, black 30%, transparent 100%);
}

/* 光晕球 */
.bg-orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(80px);
  animation: orbPulse 8s ease-in-out infinite;
}
.bg-orb--blue {
  width: 700px; height: 700px;
  background: radial-gradient(circle, rgba(0,113,227,0.18), transparent 70%);
  top: -200px; left: -150px;
  animation-delay: 0s;
}
.bg-orb--purple {
  width: 600px; height: 600px;
  background: radial-gradient(circle, rgba(120,60,255,0.15), transparent 70%);
  top: -100px; right: -100px;
  animation-delay: -3s;
}
.bg-orb--cyan {
  width: 500px; height: 500px;
  background: radial-gradient(circle, rgba(0,220,200,0.08), transparent 70%);
  bottom: -100px; left: 40%;
  animation-delay: -5s;
}

@keyframes orbPulse {
  0%, 100% { transform: scale(1) translate(0, 0); opacity: 0.8; }
  50% { transform: scale(1.1) translate(20px, -20px); opacity: 1; }
}

/* Hero 内容 */
.hero-content {
  position: relative;
  z-index: 3;
  max-width: 860px;
  text-align: center;
  opacity: 0;
  transform: translateY(40px);
  transition: opacity 0.9s cubic-bezier(0.4, 0, 0.2, 1),
              transform 0.9s cubic-bezier(0.4, 0, 0.2, 1);
}
.hero-content.visible {
  opacity: 1;
  transform: translateY(0);
}

/* Badge */
.hero-badge {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 6px 16px;
  border-radius: 980px;
  border: 1px solid rgba(255,255,255,0.1);
  background: rgba(255,255,255,0.05);
  font-size: 12.5px;
  color: rgba(255,255,255,0.6);
  letter-spacing: 0.03em;
  margin-bottom: 32px;
  backdrop-filter: blur(10px);
}
.badge-dot {
  width: 7px; height: 7px;
  border-radius: 50%;
  background: #34c759;
  box-shadow: 0 0 8px #34c759;
  animation: dotPulse 2s ease-in-out infinite;
}
@keyframes dotPulse {
  0%, 100% { box-shadow: 0 0 4px #34c759; }
  50% { box-shadow: 0 0 12px #34c759, 0 0 24px rgba(52,199,89,0.4); }
}

/* 标题 */
.hero-title {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-bottom: 24px;
}
.title-line {
  display: block;
  font-size: clamp(44px, 7vw, 84px);
  font-weight: 700;
  letter-spacing: -0.04em;
  line-height: 1.1;
  color: #f5f5f7;
}
.line-1 { opacity: 0; animation: slideUp 0.7s 0.2s cubic-bezier(0.34, 1.56, 0.64, 1) forwards; }
.line-2 { opacity: 0; animation: slideUp 0.7s 0.35s cubic-bezier(0.34, 1.56, 0.64, 1) forwards; }
.line-3 { opacity: 0; animation: slideUp 0.7s 0.5s cubic-bezier(0.34, 1.56, 0.64, 1) forwards; font-size: clamp(28px, 4.5vw, 52px); color: rgba(245,245,247,0.5); font-weight: 400; }

@keyframes slideUp {
  from { opacity: 0; transform: translateY(30px); }
  to { opacity: 1; transform: translateY(0); }
}

.gradient-text {
  background: linear-gradient(135deg, #5ac8fa 0%, #7d6fff 40%, #ff2d78 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  background-size: 200% 200%;
  animation: gradientShift 5s ease infinite;
}
@keyframes gradientShift {
  0% { background-position: 0% 50%; }
  50% { background-position: 100% 50%; }
  100% { background-position: 0% 50%; }
}

/* 副标题 */
.hero-subtitle {
  font-size: 18px;
  color: rgba(245,245,247,0.55);
  line-height: 1.7;
  margin-bottom: 44px;
  opacity: 0;
  animation: fadeIn 0.8s 0.7s ease forwards;
}

/* 按钮 */
.hero-actions {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
  margin-bottom: 52px;
  opacity: 0;
  animation: fadeIn 0.8s 0.85s ease forwards;
}

.btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 15px;
  font-weight: 600;
  padding: 13px 28px;
  border-radius: 980px;
  border: none;
  cursor: pointer;
  font-family: inherit;
  letter-spacing: -0.01em;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  text-decoration: none;
}
.btn--primary {
  background: linear-gradient(135deg, #5ac8fa, #7d6fff);
  color: #fff;
  box-shadow: 0 0 30px rgba(120,100,255,0.3);
}
.btn--primary:hover {
  transform: translateY(-2px) scale(1.03);
  box-shadow: 0 8px 40px rgba(120,100,255,0.5);
}
.btn--primary:active { transform: scale(0.97); }
.btn--ghost {
  background: rgba(255,255,255,0.06);
  color: rgba(255,255,255,0.7);
  border: 1px solid rgba(255,255,255,0.1);
  backdrop-filter: blur(10px);
}
.btn--ghost:hover {
  background: rgba(255,255,255,0.1);
  color: #fff;
}
.btn--lg {
  font-size: 17px;
  padding: 16px 40px;
}

/* 数据统计 */
.hero-stats {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 32px;
  opacity: 0;
  animation: fadeIn 0.8s 1s ease forwards;
}
.stat {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}
.stat-num {
  font-size: 28px;
  font-weight: 700;
  letter-spacing: -0.03em;
  color: #f5f5f7;
}
.stat-label {
  font-size: 12px;
  color: rgba(245,245,247,0.4);
  letter-spacing: 0.04em;
  text-transform: uppercase;
}
.stat-divider {
  width: 1px;
  height: 40px;
  background: rgba(255,255,255,0.1);
}

/* 向下滚动提示 */
.scroll-hint {
  position: absolute;
  bottom: 40px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  opacity: 0;
  transition: opacity 1s 1.5s ease;
  color: rgba(255,255,255,0.25);
  font-size: 11px;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}
.scroll-hint.visible { opacity: 1; }
.scroll-line {
  width: 1px;
  height: 48px;
  background: linear-gradient(to bottom, transparent, rgba(255,255,255,0.25));
  animation: scrollLineAnim 2s ease-in-out infinite;
}
@keyframes scrollLineAnim {
  0%, 100% { transform: scaleY(0); transform-origin: top; opacity: 0; }
  50% { transform: scaleY(1); transform-origin: top; opacity: 1; }
}

/* ════════════════════════════════════════════════════
   通用 SECTION 样式
════════════════════════════════════════════════════ */
.features-section,
.sources-section,
.cta-section {
  position: relative;
  z-index: 2;
  padding: 120px 24px;
}

.section-inner {
  max-width: 1100px;
  margin: 0 auto;
  opacity: 0;
  transform: translateY(50px);
  transition: opacity 0.8s cubic-bezier(0.4, 0, 0.2, 1),
              transform 0.8s cubic-bezier(0.4, 0, 0.2, 1);
}
.section-inner.visible {
  opacity: 1;
  transform: translateY(0);
}

.section-header {
  text-align: center;
  margin-bottom: 64px;
}
.section-eyebrow {
  display: block;
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: rgba(120,100,255,0.8);
  margin-bottom: 12px;
}
.section-title {
  font-size: clamp(28px, 4vw, 44px);
  font-weight: 700;
  letter-spacing: -0.03em;
  color: #f5f5f7;
  margin-bottom: 14px;
}
.section-desc {
  font-size: 17px;
  color: rgba(245,245,247,0.45);
  line-height: 1.65;
}

/* ════════════════════════════════════════════════════
   FEATURES SECTION
════════════════════════════════════════════════════ */
.features-section {
  background: radial-gradient(ellipse 80% 50% at 50% 100%, rgba(30,20,60,0.6), transparent);
}

.features-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 20px;
}

.feature-card {
  position: relative;
  background: rgba(255,255,255,0.03);
  border: 1px solid rgba(255,255,255,0.07);
  border-radius: 24px;
  padding: 32px 28px;
  overflow: hidden;
  cursor: default;
  opacity: 0;
  transform: translateY(30px);
  transition:
    opacity 0.6s var(--delay, 0ms) ease,
    transform 0.6s var(--delay, 0ms) cubic-bezier(0.34, 1.2, 0.64, 1),
    border-color 0.3s ease,
    background 0.3s ease;
}
.section-inner.visible .feature-card {
  opacity: 1;
  transform: translateY(0);
}
.feature-card:hover {
  background: rgba(255,255,255,0.05);
  border-color: rgba(255,255,255,0.12);
}
.feature-card:hover .feature-glow {
  opacity: 1;
}

.feature-icon {
  font-size: 36px;
  margin-bottom: 20px;
  filter: drop-shadow(0 0 12px var(--accent));
}
.feature-title {
  font-size: 18px;
  font-weight: 700;
  color: #f5f5f7;
  margin-bottom: 10px;
  letter-spacing: -0.02em;
}
.feature-desc {
  font-size: 14px;
  color: rgba(245,245,247,0.45);
  line-height: 1.65;
}

.feature-glow {
  position: absolute;
  top: 0; left: 0;
  width: 100%; height: 100%;
  background: radial-gradient(circle at 50% 0%, var(--accent, #7d6fff), transparent 60%);
  opacity: 0;
  transition: opacity 0.4s ease;
  pointer-events: none;
  mix-blend-mode: screen;
  filter: blur(20px);
}

/* ════════════════════════════════════════════════════
   SOURCES SECTION
════════════════════════════════════════════════════ */
.sources-section {
  background: radial-gradient(ellipse 70% 60% at 50% 0%, rgba(0,60,120,0.15), transparent);
}

.sources-flow {
  display: flex;
  flex-wrap: wrap;
  gap: 14px;
  justify-content: center;
  margin-bottom: 64px;
}

.source-chip {
  display: flex;
  align-items: center;
  gap: 12px;
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 16px;
  padding: 14px 20px;
  opacity: 0;
  transform: scale(0.9) translateY(20px);
  transition:
    opacity 0.5s var(--delay, 0ms) ease,
    transform 0.5s var(--delay, 0ms) cubic-bezier(0.34, 1.3, 0.64, 1),
    border-color 0.3s ease,
    background 0.3s ease;
  cursor: default;
  min-width: 160px;
}
.section-inner.visible .source-chip {
  opacity: 1;
  transform: scale(1) translateY(0);
}
.source-chip:hover {
  background: rgba(255,255,255,0.07);
  border-color: var(--color, rgba(255,255,255,0.2));
  box-shadow: 0 0 20px color-mix(in srgb, var(--color, #fff) 20%, transparent);
}

.source-icon {
  font-size: 22px;
  width: 24px;
  text-align: center;
}
.source-name {
  font-size: 15px;
  font-weight: 700;
  color: #f5f5f7;
  letter-spacing: -0.01em;
}
.source-desc {
  font-size: 12px;
  color: rgba(245,245,247,0.4);
  margin-top: 2px;
}

/* 流程管线 */
.pipeline {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
  flex-wrap: wrap;
  padding: 40px;
  background: rgba(255,255,255,0.02);
  border: 1px solid rgba(255,255,255,0.06);
  border-radius: 24px;
}
.pipeline-step {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}
.step-num {
  font-size: 28px;
  font-weight: 800;
  color: rgba(120,100,255,0.5);
  letter-spacing: -0.04em;
}
.step-text {
  font-size: 14px;
  color: rgba(245,245,247,0.6);
  font-weight: 500;
}
.pipeline-arrow {
  font-size: 20px;
  color: rgba(255,255,255,0.15);
}

/* ════════════════════════════════════════════════════
   CTA SECTION
════════════════════════════════════════════════════ */
.cta-section {
  border-top: 1px solid rgba(255,255,255,0.05);
}
.cta-inner {
  position: relative;
  max-width: 700px;
  margin: 0 auto;
  text-align: center;
  padding: 80px 40px;
  background: rgba(255,255,255,0.02);
  border: 1px solid rgba(255,255,255,0.07);
  border-radius: 32px;
  overflow: hidden;
  opacity: 0;
  transform: translateY(40px) scale(0.98);
  transition: opacity 0.8s ease, transform 0.8s cubic-bezier(0.34, 1.2, 0.64, 1);
}
.cta-inner.visible {
  opacity: 1;
  transform: translateY(0) scale(1);
}
.cta-glow {
  position: absolute;
  width: 400px; height: 400px;
  background: radial-gradient(circle, rgba(120,100,255,0.1), transparent 70%);
  top: 50%; left: 50%;
  transform: translate(-50%, -50%);
  filter: blur(40px);
  pointer-events: none;
  animation: orbPulse 6s ease-in-out infinite;
}
.cta-title {
  font-size: clamp(32px, 5vw, 52px);
  font-weight: 700;
  letter-spacing: -0.035em;
  color: #f5f5f7;
  margin-bottom: 12px;
  position: relative;
}
.cta-subtitle {
  font-size: 18px;
  color: rgba(245,245,247,0.45);
  margin-bottom: 40px;
  position: relative;
}
.cta-hint {
  font-size: 13px;
  color: rgba(245,245,247,0.25);
  margin-top: 20px;
  letter-spacing: 0.02em;
  position: relative;
}

/* ════════════════════════════════════════════════════
   通用动画
════════════════════════════════════════════════════ */
@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}
</style>
