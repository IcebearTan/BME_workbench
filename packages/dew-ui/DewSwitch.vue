<template>
  <button
    ref="switchRef"
    type="button"
    role="switch"
    :aria-checked="modelValue"
    :disabled="disabled"
    class="dew-switch"
    :class="[
      `dew-switch--${size}`,
      { 'dew-switch--active': modelValue, 'dew-switch--disabled': disabled }
    ]"
    @click="toggle"
    @mouseenter="onEnter"
    @mousemove="onMove"
    @mouseleave="onLeave"
  >
    <!-- 折射层 -->
    <span class="dew-switch__refraction" :style="refractionStyle"></span>
    <!-- 滑块 -->
    <span class="dew-switch__thumb" :style="thumbStyle"></span>
  </button>
</template>

<script setup>
import { ref, reactive, computed } from 'vue'

const props = defineProps({
  /** v-model 绑定，布尔值 */
  modelValue: { type: Boolean, default: false },
  /** 禁用 */
  disabled: { type: Boolean, default: false },
  /** 尺寸 sm | md */
  size: { type: String, default: 'md' },
  /** 激活态轨道颜色，默认跟随主题色 */
  activeColor: { type: String, default: '' },
})

const emit = defineEmits(['update:modelValue', 'change'])

function toggle() {
  if (props.disabled) return
  const val = !props.modelValue
  emit('update:modelValue', val)
  emit('change', val)
}

// ── 鼠标追踪 ──
const switchRef = ref(null)
const state = reactive({ hovering: false, x: 0.5, y: 0.5 })

function onEnter() { state.hovering = true }
function onMove(e) {
  if (!switchRef.value) return
  const r = switchRef.value.getBoundingClientRect()
  state.x = (e.clientX - r.left) / r.width
  state.y = (e.clientY - r.top) / r.height
}
function onLeave() { state.hovering = false; state.x = 0.5; state.y = 0.5 }

// ── 折射光 ──
const refractionStyle = computed(() => {
  const cx = (state.x * 100).toFixed(1)
  const cy = (state.y * 100).toFixed(1)
  const i = state.hovering ? 0.6 : 0.3
  return {
    background: `radial-gradient(ellipse at ${cx}% ${cy}%, rgba(255,255,255,${(0.4*i).toFixed(2)}) 0%, rgba(180,200,255,${(0.2*i).toFixed(2)}) 30%, rgba(200,160,255,${(0.1*i).toFixed(2)}) 50%, transparent 100%)`,
    opacity: state.hovering ? '0.8' : '0.5',
    transition: state.hovering ? 'opacity 0.1s' : 'opacity 0.4s',
  }
})

// ── 滑块位移（用 left 定位，百分比相对父元素） ──
const thumbStyle = computed(() => ({
  left: props.modelValue
    ? 'calc(100% - var(--dew-switch-thumb-w) - var(--dew-switch-gap))'
    : 'var(--dew-switch-gap)',
}))
</script>

<style scoped>
.dew-switch {
  position: relative;
  display: inline-flex;
  align-items: center;
  border: none;
  border-radius: 9999px;
  cursor: pointer;
  outline: none;
  padding: 0;
  font-family: var(--dew-font, inherit);
  isolation: isolate;
  overflow: hidden;
  backdrop-filter: blur(20px) saturate(1.5);
  -webkit-backdrop-filter: blur(20px) saturate(1.5);
  background: var(--dew-switch-bg);
  border: 1px solid var(--dew-switch-border);
  box-shadow: var(--dew-switch-shadow);
  transition:
    background 0.35s var(--dew-bounce),
    border-color 0.35s var(--dew-bounce),
    box-shadow 0.35s var(--dew-bounce);
}

/* ── 尺寸 ── */
.dew-switch--md {
  --dew-switch-gap: 2px;
  --dew-switch-thumb-w: 26px;
  --dew-switch-thumb-h: 20px;
  width: 44px;
  height: 24px;
}
.dew-switch--sm {
  --dew-switch-gap: 2px;
  --dew-switch-thumb-w: 20px;
  --dew-switch-thumb-h: 16px;
  width: 36px;
  height: 20px;
}

/* ── 激活态 ── */
.dew-switch--active {
  background: var(--dew-switch-bg-active);
  border-color: var(--dew-switch-border-active);
  box-shadow: var(--dew-switch-shadow-active);
}

/* ── 折射层 ── */
.dew-switch__refraction {
  position: absolute;
  inset: -2px;
  z-index: 1;
  border-radius: inherit;
  mix-blend-mode: overlay;
  pointer-events: none;
}

/* ── 滑块 ── */
.dew-switch__thumb {
  position: absolute;
  top: 50%;
  margin-top: calc(var(--dew-switch-thumb-h) / -2);
  z-index: 2;
  width: var(--dew-switch-thumb-w);
  height: var(--dew-switch-thumb-h);
  border-radius: 9999px;
  background: var(--dew-switch-thumb-bg);
  box-shadow: var(--dew-switch-thumb-shadow);
  /* 水滴弹性滑动 */
  transition:
    left 0.4s var(--dew-bounce),
    box-shadow 0.35s var(--dew-bounce),
    transform 0.15s ease;
}

/* 滑块 hover 放大 */
.dew-switch:not(.dew-switch--disabled):hover .dew-switch__thumb {
  transform: var(--dew-switch-thumb-transform);
  box-shadow: var(--dew-switch-thumb-shadow-hover);
}

/* 激活态滑块发光 */
.dew-switch--active .dew-switch__thumb {
  box-shadow: var(--dew-switch-thumb-shadow-active);
}

/* 按下缩小 */
.dew-switch:not(.dew-switch--disabled):active .dew-switch__thumb {
  transform: var(--dew-switch-thumb-transform) scale(0.9);
  transition-duration: 0.1s;
}

/* ── 禁用 ── */
.dew-switch--disabled {
  opacity: 0.45;
  cursor: not-allowed;
}
.dew-switch--disabled .dew-switch__refraction {
  opacity: 0 !important;
}

/* ── focus-visible ── */
.dew-switch:focus-visible {
  outline: 2px solid var(--color-primary);
  outline-offset: 2px;
}
</style>
