<template>
  <div
    ref="cardRef"
    class="dew-card"
    :class="[
      `dew-card--${variant}`,
      `dew-card--${size}`,
      {
        'dew-card--glass': glass,
        'dew-card--interactive': interactive,
        'dew-card--no-hover': noHover,
        'dew-card--divided': divided,
        'dew-card--tinted': tinted,
        [`dew-card--accent-${accent}`]: accent,
      }
    ]"
    :tabindex="interactive ? 0 : undefined"
    :role="interactive ? 'button' : undefined"
    @mouseenter="onEnter"
    @mousemove="onMove"
    @mouseleave="onLeave"
    @keydown="onKeydown"
    @click="interactive && emit('click', $event)"
  >
    <!-- 折射层 -->
    <span class="dew-card__refraction" :style="refractionStyle"></span>
    <!-- 色散层 -->
    <span class="dew-card__chromatic" :style="chromaticStyle"></span>
    <!-- 顶部高光线 -->
    <span class="dew-card__highlight"></span>
    <!-- 色彩底色层（tinted 模式） -->
    <span v-if="tinted" class="dew-card__tint"></span>
    <!-- 内容 -->
    <div v-if="$slots.header" class="dew-card__header">
      <slot name="header" />
    </div>
    <div class="dew-card__body">
      <slot />
    </div>
    <div v-if="$slots.footer" class="dew-card__footer">
      <slot name="footer" />
    </div>
    <!-- 可交互指示器 -->
    <span v-if="interactive" class="dew-card__ripple" :style="rippleStyle"></span>
  </div>
</template>

<script setup>
import { ref, reactive, computed } from 'vue'

const props = defineProps({
  /** 卡片变体：default | elevated | inset | flat（纯色扁平，无 glass） */
  variant: { type: String, default: 'default' },
  /** 尺寸：sm | md | lg */
  size: { type: String, default: 'md' },
  /** 毛玻璃效果（更强的模糊和透明度） */
  glass: { type: Boolean, default: false },
  /** 可交互卡片：显示点击反馈，带 cursor: pointer */
  interactive: { type: Boolean, default: false },
  /** 禁用悬停上浮效果 */
  noHover: { type: Boolean, default: false },
  /** 色彩底色模式：在毛玻璃下方叠加淡色渐变 */
  tinted: { type: Boolean, default: false },
  /** 强调色：primary | success | warning | danger | info */
  accent: { type: String, default: null },
  /** 显示 header 底部分割线 */
  divided: { type: Boolean, default: false },
})

const emit = defineEmits(['click'])

const cardRef = ref(null)
const state = reactive({ hovering: false, x: 0.5, y: 0.5 })

/** 键盘可达：interactive 卡可 Tab 聚焦，Enter/Space 触发与点击同源的 click 事件 */
function onKeydown(e) {
  if (!props.interactive) return
  if (e.key !== 'Enter' && e.key !== ' ') return
  // 内嵌可交互元素（链接/按钮等）自带键盘语义：不代理触发卡片点击，
  // 交还原生行为——否则焦点在卡内链接上按 Enter 会被劫持成整卡动作
  // （2026-10-03 修：XLAB 引流卡键盘Enter开出帖子页而非项目页的根因）
  if (e.target !== cardRef.value
      && e.target.closest('a, button, input, select, textarea, [role="button"]')) {
    return
  }
  e.preventDefault()
  emit('click', e)
}

function onEnter() { state.hovering = true }
function onMove(e) {
  if (!cardRef.value) return
  const r = cardRef.value.getBoundingClientRect()
  state.x = (e.clientX - r.left) / r.width
  state.y = (e.clientY - r.top) / r.height
}
function onLeave() { state.hovering = false; state.x = 0.5; state.y = 0.5 }

const refractionStyle = computed(() => {
  const cx = (state.x * 100).toFixed(1)
  const cy = (state.y * 100).toFixed(1)
  const i = state.hovering ? 0.5 : 0.25
  return {
    background: `radial-gradient(ellipse at ${cx}% ${cy}%, rgba(255,255,255,${(0.35*i).toFixed(2)}) 0%, rgba(180,200,255,${(0.18*i).toFixed(2)}) 25%, rgba(200,160,255,${(0.1*i).toFixed(2)}) 45%, transparent 100%)`,
    opacity: state.hovering ? '0.9' : '0.5',
    transition: state.hovering ? 'opacity 0.15s' : 'opacity 0.4s',
  }
})

const chromaticStyle = computed(() => {
  if (!state.hovering) return { opacity: '0' }
  const cx = (state.x * 100).toFixed(1)
  const cy = (state.y * 100).toFixed(1)
  return {
    opacity: '0.7',
    background: `radial-gradient(ellipse at ${cx}% ${cy}%, rgba(255,150,150,0.05) 0%, rgba(150,255,150,0.04) 30%, rgba(150,150,255,0.06) 60%, transparent 100%)`,
  }
})

const rippleStyle = computed(() => ({
  '--ripple-x': `${(state.x * 100).toFixed(1)}%`,
  '--ripple-y': `${(state.y * 100).toFixed(1)}%`,
}))
</script>

<style scoped>
.dew-card {
  position: relative;
  isolation: isolate;
  font-family: var(--dew-font, inherit);
  backdrop-filter: blur(20px) saturate(1.4);
  -webkit-backdrop-filter: blur(20px) saturate(1.4);
  background: var(--dew-card-bg);
  border: 1px solid var(--dew-card-border);
  border-radius: var(--radius-lg);
  box-shadow: var(--dew-card-shadow);
  overflow: hidden;
  transition:
    transform 0.35s var(--dew-bounce),
    box-shadow 0.35s var(--dew-bounce),
    background 0.35s var(--dew-bounce),
    border-color 0.35s var(--dew-bounce);
}

.dew-card:hover {
  background: var(--dew-card-bg-hover);
  box-shadow: var(--dew-card-shadow-hover);
  transform: translateY(-2px);
}

/* ━━━━ 变体 ━━━━ */

/* ── elevated ── */
.dew-card--elevated {
  background: var(--dew-card-elevated-bg);
  box-shadow: var(--dew-card-elevated-shadow);
}
.dew-card--elevated:hover {
  background: var(--dew-card-elevated-bg-hover);
  box-shadow: var(--dew-card-elevated-shadow-hover);
  transform: translateY(-3px);
}

/* ── inset ── */
.dew-card--inset {
  background: var(--dew-card-inset-bg);
  border-color: var(--dew-card-inset-border);
  box-shadow: var(--dew-card-inset-shadow);
}
.dew-card--inset:hover {
  background: var(--dew-card-inset-bg-hover);
  border-color: var(--dew-card-inset-border-hover);
  box-shadow: var(--dew-card-inset-shadow-hover);
  transform: none;
}

/* ━━━━ 毛玻璃模式 ━━━━ */
.dew-card--glass {
  backdrop-filter: blur(28px) saturate(1.6);
  -webkit-backdrop-filter: blur(28px) saturate(1.6);
  background: var(--dew-card-glass-bg);
  border-color: var(--dew-card-glass-border);
  box-shadow: var(--dew-card-glass-shadow);
}
.dew-card--glass:hover {
  background: var(--dew-card-glass-bg-hover);
  box-shadow: var(--dew-card-glass-shadow-hover);
}

/* ━━━━ 扁平模式（纯色，无 glass，阅读/文档场景） ━━━━ */
.dew-card--flat {
  backdrop-filter: none;
  -webkit-backdrop-filter: none;
  background: var(--dew-card-flat-bg);
  border-color: var(--dew-card-flat-border);
  box-shadow: var(--dew-card-flat-shadow);
}
/* flat 是静态阅读/文档容器：hover 完全无反馈（背景/阴影/位移均不变） */
.dew-card--flat:hover {
  background: var(--dew-card-flat-bg);
  box-shadow: var(--dew-card-flat-shadow);
  transform: none;
}
/* flat 模式隐藏玻璃特效层（折射/色散/高光/底色） */
.dew-card--flat .dew-card__refraction,
.dew-card--flat .dew-card__chromatic,
.dew-card--flat .dew-card__highlight,
.dew-card--flat .dew-card__tint {
  display: none;
}

/* ━━━━ 可交互 ━━━━ */
.dew-card--interactive {
  cursor: pointer;
  user-select: none;
}
.dew-card--interactive:active {
  transform: translateY(0) scale(0.985) !important;
}

/* ━━━━ 禁用悬停（放在变体之后，靠源码顺序覆盖所有 hover transform） ━━━━ */
.dew-card--no-hover:hover {
  transform: none;
}

/* 点击涟漪层 */
.dew-card__ripple {
  position: absolute;
  inset: 0;
  z-index: 4;
  border-radius: inherit;
  pointer-events: none;
  background: radial-gradient(circle at var(--ripple-x, 50%) var(--ripple-y, 50%),
    var(--dew-glow-ripple) 0%,
    transparent 60%);
  opacity: 0;
  transition: opacity 0.4s ease;
}
.dew-card--interactive:active .dew-card__ripple {
  opacity: 1;
  transition: opacity 0s;
}

/* ━━━━ 色彩底色 ━━━━ */
.dew-card__tint {
  position: absolute;
  inset: 0;
  z-index: 0;
  border-radius: inherit;
  pointer-events: none;
  opacity: 0.35;
  background: linear-gradient(135deg, var(--dew-tint-default-from), var(--dew-tint-default-to));
}

/* ── accent 色彩变体 ── */
.dew-card--accent-primary .dew-card__tint {
  background: linear-gradient(135deg, var(--dew-tint-primary-from), var(--dew-tint-primary-to));
}
.dew-card--accent-success .dew-card__tint {
  background: linear-gradient(135deg, var(--dew-tint-success-from), var(--dew-tint-success-to));
}
.dew-card--accent-warning .dew-card__tint {
  background: linear-gradient(135deg, var(--dew-tint-warning-from), var(--dew-tint-warning-to));
}
.dew-card--accent-danger .dew-card__tint {
  background: linear-gradient(135deg, var(--dew-tint-danger-from), var(--dew-tint-danger-to));
}
.dew-card--accent-info .dew-card__tint {
  background: linear-gradient(135deg, var(--dew-tint-info-from), var(--dew-tint-info-to));
}

/* ━━━━ 尺寸（内边距） ━━━━ */
.dew-card--sm .dew-card__header,
.dew-card--sm .dew-card__body,
.dew-card--sm .dew-card__footer { padding-left: 14px; padding-right: 14px; }
.dew-card--sm .dew-card__body { padding-top: 10px; padding-bottom: 10px; }
.dew-card--sm .dew-card__header { padding-top: 12px; padding-bottom: 10px; }
.dew-card--sm .dew-card__footer { padding-bottom: 12px; }

.dew-card--md .dew-card__header,
.dew-card--md .dew-card__body,
.dew-card--md .dew-card__footer { padding-left: 16px; padding-right: 16px; }
.dew-card--md .dew-card__body { padding-top: 12px; padding-bottom: 12px; }
.dew-card--md .dew-card__header { padding-top: 14px; padding-bottom: 12px; }
.dew-card--md .dew-card__footer { padding-bottom: 14px; }

.dew-card--lg .dew-card__header,
.dew-card--lg .dew-card__body,
.dew-card--lg .dew-card__footer { padding-left: 20px; padding-right: 20px; }
.dew-card--lg .dew-card__body { padding-top: 14px; padding-bottom: 14px; }
.dew-card--lg .dew-card__header { padding-top: 16px; padding-bottom: 14px; }
.dew-card--lg .dew-card__footer { padding-bottom: 16px; }

/* ━━━━ 折射层 ━━━━ */
.dew-card__refraction {
  position: absolute;
  inset: 0;
  z-index: 1;
  border-radius: inherit;
  mix-blend-mode: overlay;
  pointer-events: none;
}

/* ━━━━ 色散层 ━━━━ */
.dew-card__chromatic {
  position: absolute;
  inset: 0;
  z-index: 1;
  border-radius: inherit;
  pointer-events: none;
  mix-blend-mode: screen;
  transition: opacity 0.4s ease;
}

/* ━━━━ 顶部高光线 ━━━━ */
.dew-card__highlight {
  position: absolute;
  top: 0;
  left: 15%;
  right: 15%;
  height: 1px;
  z-index: 2;
  background: linear-gradient(90deg, transparent, var(--dew-glow-highlight), transparent);
  pointer-events: none;
}

/* ━━━━ 结构层 ━━━━ */
.dew-card__header {
  position: relative;
  z-index: 3;
  font-weight: 600;
  font-size: 14px;
  color: var(--dew-text-heading);
  transition: color 0.35s ease;
}

/* ━━━━ 分割线（divided 模式下 header 底部显示） ━━━━ */
.dew-card--divided .dew-card__header {
  border-bottom: 1px solid var(--dew-card-divider);
}

.dew-card__body {
  position: relative;
  z-index: 3;
}

.dew-card__footer {
  position: relative;
  z-index: 3;
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
</style>
