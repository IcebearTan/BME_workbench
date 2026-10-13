<template>
  <!-- 多行文本：容器内渲染多根灰条，末行自动收窄 -->
  <div v-if="variant === 'text' && lines > 1"
       class="dew-skeleton-group"
       :style="{ gap: toPx(gap) }"
       aria-hidden="true">
    <span v-for="i in lines"
          :key="i"
          class="dew-skeleton dew-skeleton--text"
          :class="{ 'dew-skeleton--static': !animated }"
          :style="lineStyle(i)" />
  </div>
  <!-- 单形态：text / rect / circle -->
  <span v-else
        class="dew-skeleton"
        :class="[`dew-skeleton--${variant}`, { 'dew-skeleton--static': !animated }]"
        :style="baseStyle"
        aria-hidden="true" />
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  /** 形态：text 文本行 | rect 矩形块 | circle 圆形（头像） */
  variant: { type: String, default: 'text' },
  /** 宽度（数字=px，字符串原样如 '60%'） */
  width: { type: [String, Number], default: null },
  /** 高度（同上） */
  height: { type: [String, Number], default: null },
  /** circle 的直径 */
  size: { type: [String, Number], default: null },
  /** text 变体渲染的行数 */
  lines: { type: Number, default: 1 },
  /** 多行间距（px） */
  gap: { type: [String, Number], default: 10 },
  /** 呼吸动画（false=静态占位） */
  animated: { type: Boolean, default: true },
  /** 自定义圆角 */
  rounded: { type: String, default: null },
})

// 尺寸归一：数字→px，字符串→原样
const toPx = (v) => (typeof v === 'number' ? `${v}px` : v)

const baseStyle = computed(() => {
  const s = {}
  if (props.variant === 'circle') {
    const d = props.size != null ? toPx(props.size) : '40px'
    s.width = d
    s.height = d
    s.borderRadius = '50%'
  } else if (props.variant === 'rect') {
    s.width = props.width != null ? toPx(props.width) : '100%'
    s.height = props.height != null ? toPx(props.height) : '80px'
    s.borderRadius = props.rounded || 'var(--radius-md)'
  } else {
    // text
    s.width = props.width != null ? toPx(props.width) : '100%'
    s.height = props.height != null ? toPx(props.height) : '14px'
    s.borderRadius = props.rounded || 'var(--radius-full)'
  }
  return s
})

// 多行：末行收窄到 60%（除非显式指定 width）
const lineStyle = (i) => {
  const isLast = i === props.lines
  return {
    width: isLast && props.width == null ? '60%' : (props.width != null ? toPx(props.width) : '100%'),
    height: props.height != null ? toPx(props.height) : '14px',
  }
}
</script>

<style scoped>
.dew-skeleton {
  display: block;
  background: var(--dew-skeleton-bg);
  animation: dew-skeleton-breathe 1.4s ease-in-out infinite;
}

/* 静态占位（关动画） */
.dew-skeleton--static {
  animation: none;
  opacity: 0.7;
}

.dew-skeleton-group {
  display: flex;
  flex-direction: column;
}

@keyframes dew-skeleton-breathe {
  0%, 100% { opacity: 0.5; }
  50% { opacity: 1; }
}
</style>
