<template>
  <button
    ref="btnRef"
    type="button"
    class="dew-btn"
    :class="[
      `dew-btn--${type}`,
      `dew-btn--${size}`,
      { 'dew-btn--block': block, 'dew-btn--lit': active }
    ]"
    :disabled="disabled || loading"
    :style="sizeStyle"
    @mouseenter="onEnter"
    @mousemove="onMove"
    @mouseleave="onLeave"
    @click="$emit('click', $event)"
  >
    <span class="dew-btn__refraction" :style="refractionStyle"></span>
    <span class="dew-btn__chromatic" :style="chromaticStyle"></span>
    <!-- 隐藏测量层：始终渲染内容用于计算真实宽度 -->
    <span ref="measureRef" class="dew-btn__measure">
      <slot />
    </span>
    <!-- 可见内容层 -->
    <span class="dew-btn__content">
      <span v-if="loading" class="dew-btn__spinner" aria-hidden="true"></span>
      <slot />
    </span>
  </button>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUpdated, onBeforeUnmount, nextTick, watch } from 'vue'

const props = defineProps({
  type: { type: String, default: 'glass' },
  size: { type: String, default: 'md' },
  disabled: { type: Boolean, default: false },
  loading: { type: Boolean, default: false },
  block: { type: Boolean, default: false },
  active: { type: Boolean, default: false },
})

defineEmits(['click'])

const btnRef = ref(null)
const measureRef = ref(null)
const state = reactive({ hovering: false, x: 0.5, y: 0.5 })
const currentWidth = ref(null)
let ro = null

// 测量内容真实宽度
function measureWidth() {
  if (!measureRef.value || props.block) return
  const w = measureRef.value.offsetWidth
  // 祖先 display:none（如 v-show 隐藏的 tab）时测得 0，跳过；
  // 变可见后由 ResizeObserver 补测
  if (w > 0) currentWidth.value = w
}

// 挂载和每次更新后都重新测量
onMounted(() => {
  nextTick(measureWidth)
  // 在 v-show 隐藏容器中挂载时初次测量为 0，可见后测量层尺寸变化触发补测
  if (typeof ResizeObserver !== 'undefined' && measureRef.value) {
    ro = new ResizeObserver(() => measureWidth())
    ro.observe(measureRef.value)
  }
})
onUpdated(() => nextTick(measureWidth))
onBeforeUnmount(() => { if (ro) ro.disconnect() })

// 主动测量触发点：slot 内容变化时
watch(() => props.active, () => nextTick(measureWidth))

// 将计算出的宽度注入按钮 style，让 CSS transition 接管过渡
const sizeStyle = computed(() => {
  if (props.block || currentWidth.value === null) return null
  const paddingMap = { sm: 36, md: 52, lg: 72 }
  const pad = paddingMap[props.size] || 52
  return { width: `${currentWidth.value + pad}px` }
})

function onEnter() { state.hovering = true }
function onMove(e) {
  if (!btnRef.value) return
  const r = btnRef.value.getBoundingClientRect()
  state.x = (e.clientX - r.left) / r.width
  state.y = (e.clientY - r.top) / r.height
}
function onLeave() { state.hovering = false; state.x = 0.5; state.y = 0.5 }

const refractionStyle = computed(() => {
  const cx = (state.x * 100).toFixed(1)
  const cy = (state.y * 100).toFixed(1)
  const i = state.hovering ? 0.7 : 0.4
  return {
    background: `radial-gradient(ellipse at ${cx}% ${cy}%, rgba(255,255,255,${(0.5*i).toFixed(2)}) 0%, rgba(180,200,255,${(0.25*i).toFixed(2)}) 20%, rgba(200,160,255,${(0.15*i).toFixed(2)}) 40%, rgba(255,180,200,${(0.1*i).toFixed(2)}) 60%, transparent 100%)`,
    opacity: state.hovering ? '1' : '0.6',
    transition: state.hovering ? 'opacity 0.1s' : 'opacity 0.4s',
  }
})

const chromaticStyle = computed(() => {
  if (!state.hovering) return { opacity: '0' }
  const cx = (state.x * 100).toFixed(1)
  const cy = (state.y * 100).toFixed(1)
  return {
    opacity: '1',
    background: `radial-gradient(ellipse at ${cx}% ${cy}%, rgba(255,100,100,0.08) 0%, rgba(100,255,100,0.06) 25%, rgba(100,100,255,0.08) 50%, transparent 100%)`,
  }
})
</script>

<style scoped>
.dew-btn {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: none;
  border-radius: 9999px;
  cursor: pointer;
  outline: none;
  overflow: hidden;
  isolation: isolate;
  backdrop-filter: blur(20px) saturate(1.5);
  -webkit-backdrop-filter: blur(20px) saturate(1.5);
  /* 水滴弹性过渡 */
  transition:
    width 0.4s var(--dew-bounce),
    transform 0.35s var(--dew-bounce),
    box-shadow 0.35s var(--dew-bounce),
    background 0.35s var(--dew-bounce),
    border-color 0.35s var(--dew-bounce),
    color 0.35s ease;
  color: var(--dew-text);
  font-family: var(--dew-font, inherit);
  -webkit-tap-highlight-color: transparent;
}

.dew-btn--block { width: 100% !important; }

/* 测量层：不可见但占据空间，用于精确测量内容宽度 */
.dew-btn__measure {
  position: absolute;
  visibility: hidden;
  white-space: nowrap;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-weight: 600;
  letter-spacing: 0.01em;
  pointer-events: none;
}

/* 可见内容层 */
.dew-btn__content {
  position: relative;
  z-index: 3;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  white-space: nowrap;
  font-family: inherit;
  font-weight: 600;
  letter-spacing: 0.01em;
  pointer-events: none;
  transition: text-shadow 0.25s ease;
}

/* loading 旋转指示（纯 CSS，不引图标） */
.dew-btn__spinner {
  width: 1em;
  height: 1em;
  border-radius: 50%;
  border: 2px solid currentColor;
  border-top-color: transparent;
  animation: dew-spin 0.7s linear infinite;
  flex-shrink: 0;
}
@keyframes dew-spin { to { transform: rotate(360deg); } }

.dew-btn__refraction {
  position: absolute;
  inset: -2px;
  z-index: 1;
  border-radius: inherit;
  mix-blend-mode: overlay;
  pointer-events: none;
}

.dew-btn__chromatic {
  position: absolute;
  inset: -1px;
  z-index: 1;
  border-radius: inherit;
  pointer-events: none;
  mix-blend-mode: screen;
  transition: opacity 0.4s ease;
}

/* ── 尺寸 ── */
.dew-btn--sm { height: 32px; }
.dew-btn--sm .dew-btn__content,
.dew-btn--sm .dew-btn__measure { font-size: 12px; }

.dew-btn--md { height: 40px; }
.dew-btn--md .dew-btn__content,
.dew-btn--md .dew-btn__measure { font-size: 14px; }

.dew-btn--lg { height: 50px; }
.dew-btn--lg .dew-btn__content,
.dew-btn--lg .dew-btn__measure { font-size: 15px; }

/* ━━━━ Glass（默认） ━━━━ */
.dew-btn--glass {
  background: var(--dew-btn-bg);
  border: 1px solid var(--dew-btn-border);
  color: var(--dew-text);
  box-shadow: var(--dew-btn-shadow);
}
.dew-btn--glass:hover {
  background: var(--dew-btn-bg-hover);
  box-shadow: var(--dew-btn-shadow-hover);
  transform: translateY(-1px);
}

/* ━━━━ Danger ━━━━ */
.dew-btn--danger {
  background: var(--dew-btn-danger-bg);
  border: 1px solid var(--dew-btn-danger-border);
  color: var(--dew-btn-danger-color);
  box-shadow: var(--dew-btn-danger-shadow);
}
.dew-btn--danger:hover {
  background: var(--dew-btn-danger-bg-hover);
  box-shadow: var(--dew-btn-danger-shadow-hover);
  transform: translateY(-1px);
}
.dew-btn--danger:hover .dew-btn__content { text-shadow: var(--dew-btn-danger-text-shadow); }

/* ━━━━ Ghost ━━━━ */
.dew-btn--ghost {
  background: transparent;
  border: 1px solid transparent;
  color: var(--dew-text-muted);
  box-shadow: none;
  backdrop-filter: none;
  -webkit-backdrop-filter: none;
}
.dew-btn--ghost .dew-btn__refraction,
.dew-btn--ghost .dew-btn__chromatic { display: none; }
.dew-btn--ghost:hover { background: var(--dew-ghost-hover-bg); color: var(--dew-ghost-hover-text); }

/* ━━━━ 点亮状态（可叠加在任意 type 上） ━━━━ */
.dew-btn--lit {
  background: var(--dew-btn-lit-bg) !important;
  border-color: var(--dew-btn-lit-border) !important;
  color: var(--dew-btn-lit-color) !important;
  box-shadow: var(--dew-btn-lit-shadow) !important;
}
.dew-btn--lit:hover {
  background: var(--dew-btn-lit-bg-hover) !important;
  box-shadow: var(--dew-btn-lit-shadow-hover) !important;
  transform: translateY(-1px);
}
.dew-btn--lit .dew-btn__content {
  text-shadow: var(--dew-btn-lit-text-shadow);
}

/* ━━━━ Danger 点亮态 — 红色光焰 ━━━━ */
.dew-btn--danger.dew-btn--lit {
  background: var(--dew-btn-danger-lit-bg) !important;
  border-color: var(--dew-btn-danger-lit-border) !important;
  color: var(--dew-btn-danger-lit-color) !important;
  box-shadow: var(--dew-btn-danger-lit-shadow) !important;
}
.dew-btn--danger.dew-btn--lit:hover {
  background: var(--dew-btn-danger-lit-bg-hover) !important;
  box-shadow: var(--dew-btn-danger-lit-shadow-hover) !important;
  transform: translateY(-1px);
}
.dew-btn--danger.dew-btn--lit .dew-btn__content {
  text-shadow: var(--dew-btn-danger-lit-text-shadow);
}

/* ── active 按下 ── */
.dew-btn:active:not(:disabled) { transform: translateY(0.5px) scale(0.97) !important; }

/* ── 禁用 ── */
.dew-btn:disabled {
  cursor: not-allowed;
  opacity: 0.35;
  transform: none !important;
  box-shadow: none !important;
  backdrop-filter: blur(8px);
}
.dew-btn:disabled .dew-btn__refraction,
.dew-btn:disabled .dew-btn__chromatic { opacity: 0 !important; }
</style>
