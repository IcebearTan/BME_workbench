<template>
  <div
    ref="barRef"
    class="dew-bar"
    :class="[`dew-bar--${size}`, { 'dew-bar--stretch': stretch }]"
    @mouseenter="onEnter"
    @mousemove="onMove"
    @mouseleave="onLeave"
  >
    <!-- 折射层 -->
    <span class="dew-bar__refraction" :style="refractionStyle"></span>
    <!-- 滑动指示器 -->
    <span class="dew-bar__indicator" :style="indicatorStyle"></span>
    <!-- 选项 -->
    <button
      v-for="item in items"
      :key="item.value"
      type="button"
      class="dew-bar__item"
      :class="{ 'dew-bar__item--active': modelValue === item.value }"
      @click="$emit('update:modelValue', item.value)"
    >
      <component v-if="item.icon" :is="item.icon" class="dew-bar__icon" />
      <span class="dew-bar__label">{{ item.label }}</span>
      <span
        v-if="hasBadge(item)"
        class="dew-bar__badge"
        :class="{
          'dew-bar__badge--active-count': badgeMode === 'active-count',
          'dew-bar__badge--visible': badgeMode !== 'active-count' || modelValue === item.value,
        }"
      >{{ badgeMode === 'active-count' ? `（${item.badge}）` : item.badge }}</span>
    </button>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUpdated, nextTick, watch } from 'vue'

const props = defineProps({
  /**
   * 选项列表
   * [{ value: 'all', label: '全部', icon: Component, badge?: number }]
   */
  items: { type: Array, required: true },
  modelValue: { type: [String, Number], default: null },
  size: { type: String, default: 'md' },  // sm | md | lg
  /** 占满容器宽：条体拉到 100%、选项均分（筛选栏对齐列宽用） */
  stretch: { type: Boolean, default: false },
  badgeMode: {
    type: String,
    default: 'pill',
    validator: (value) => ['pill', 'active-count'].includes(value),
  },
})

defineEmits(['update:modelValue'])

const barRef = ref(null)
const state = reactive({ hovering: false, x: 0.5, y: 0.5 })
const indicator = reactive({ left: 0, width: 0 })

const hasBadge = (item) => props.badgeMode === 'active-count'
  ? item.badge !== undefined && item.badge !== null
  : Number(item.badge) > 0

// 测量选中项的位置，让指示器滑动过去
function measureIndicator() {
  if (!barRef.value) return
  const idx = props.items.findIndex(i => i.value === props.modelValue)
  if (idx < 0) return
  const btn = barRef.value.querySelectorAll('.dew-bar__item')[idx]
  if (!btn) return
  indicator.left = btn.offsetLeft
  indicator.width = btn.offsetWidth
}

onMounted(() => nextTick(measureIndicator))
onUpdated(() => nextTick(measureIndicator))
watch(() => props.modelValue, () => nextTick(measureIndicator))

const indicatorStyle = computed(() => ({
  left: `${indicator.left}px`,
  width: `${indicator.width}px`,
}))

function onEnter() { state.hovering = true }
function onMove(e) {
  if (!barRef.value) return
  const r = barRef.value.getBoundingClientRect()
  state.x = (e.clientX - r.left) / r.width
  state.y = (e.clientY - r.top) / r.height
}
function onLeave() { state.hovering = false; state.x = 0.5; state.y = 0.5 }

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
</script>

<style scoped>
.dew-bar {
  position: relative;
  display: inline-flex;
  align-items: center;
  border-radius: 9999px;
  font-family: var(--dew-font, inherit);
  overflow: hidden;
  isolation: isolate;
  backdrop-filter: blur(20px) saturate(1.5);
  -webkit-backdrop-filter: blur(20px) saturate(1.5);
  background: var(--dew-bar-bg);
  border: 1px solid var(--dew-bar-border);
  box-shadow: var(--dew-bar-shadow);
  padding: 3px;
}

/* ── 尺寸 ── */
.dew-bar--sm { gap: 2px; }
.dew-bar--md { gap: 3px; }
.dew-bar--lg { gap: 4px; }

/* ── 占满容器：条体 100% 宽，选项均分（指示器按 offsetWidth 定位，不受影响） ── */
.dew-bar--stretch {
  display: flex;
  width: 100%;
}

.dew-bar--stretch .dew-bar__item {
  flex: 1;
}

/* ── 折射层 ── */
.dew-bar__refraction {
  position: absolute;
  inset: -2px;
  z-index: 1;
  border-radius: inherit;
  mix-blend-mode: overlay;
  pointer-events: none;
}

/* ── 滑动指示器（点亮背景） ── */
.dew-bar__indicator {
  position: absolute;
  top: 3px;
  bottom: 3px;
  z-index: 2;
  border-radius: 9999px;
  background: var(--dew-glow-indicator-bg);
  box-shadow: var(--dew-glow-indicator-shadow);
  /* 水滴弹性滑动 */
  transition:
    left 0.4s var(--dew-bounce),
    width 0.4s var(--dew-bounce);
  pointer-events: none;
}

/* ── 选项按钮 ── */
.dew-bar__item {
  position: relative;
  z-index: 3;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 5px;
  border: none;
  border-radius: 9999px;
  background: transparent;
  cursor: pointer;
  outline: none;
  white-space: nowrap;
  font-family: inherit;
  font-weight: 500;
  color: var(--dew-bar-text);
  transition: color 0.35s ease;
}

.dew-bar--sm .dew-bar__item {
  height: 28px;
  padding: 0 12px;
  font-size: 12px;
}
.dew-bar--md .dew-bar__item {
  height: 34px;
  padding: 0 16px;
  font-size: 13px;
}
.dew-bar--lg .dew-bar__item {
  height: 40px;
  padding: 0 19px;
  font-size: 14px;
}

.dew-bar__icon {
  width: 14px;
  height: 14px;
}

.dew-bar__label {
  line-height: 1;
}

/* ── 未读 badge ── */
.dew-bar__badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 16px;
  height: 16px;
  padding: 0 4px;
  border-radius: 9999px;
  font-size: 10px;
  font-weight: 600;
  line-height: 1;
  background: var(--dew-bar-badge-bg);
  color: var(--dew-bar-badge-color);
}
.dew-bar__badge--active-count {
  min-width: 0;
  max-width: 0;
  height: auto;
  padding: 0;
  overflow: hidden;
  color: inherit;
  background: transparent;
  opacity: 0;
  transform: translateX(-4px);
  white-space: nowrap;
  transition:
    max-width 0.32s var(--dew-bounce),
    opacity 0.2s ease,
    transform 0.32s var(--dew-bounce);
}
.dew-bar__badge--active-count.dew-bar__badge--visible {
  max-width: 44px;
  opacity: 1;
  transform: translateX(0);
}

/* ── 选中态 ── */
.dew-bar__item--active {
  color: var(--dew-bar-text-active);
  font-weight: 600;
  text-shadow: var(--dew-glow-text-active);
}

/* ── hover（非选中项） ── */
.dew-bar__item:not(.dew-bar__item--active):hover {
  color: var(--dew-bar-text-hover);
}

@media (prefers-reduced-motion: reduce) {
  .dew-bar__indicator,
  .dew-bar__badge--active-count { transition: none; }
}
</style>
