<template>
  <div :class="['dew-progress', `dew-progress--${size}`]">
    <div class="dew-progress__track">
      <div class="dew-progress__fill" :style="{ width: clamped + '%' }">
        <span class="dew-progress__shine"></span>
      </div>
    </div>
    <span v-if="showLabel" class="dew-progress__label">{{ Math.round(clamped) }}%</span>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  /** 进度百分比 0-100（自动夹取） */
  percentage: { type: Number, default: 0 },
  /** 尺寸 sm | md | lg */
  size: { type: String, default: 'md' },
  /** 是否在右侧显示百分比 */
  showLabel: { type: Boolean, default: false },
})

const clamped = computed(() => Math.max(0, Math.min(100, Number(props.percentage) || 0)))
</script>

<style scoped>
/*
 * DewProgress —— DewUI 进度条
 * light：透明如水的蓝青填充 + 玻璃高光（token：--dew-progress-fill-bg 等）
 * dark ：高亮发白光的填充 + 白色外发光
 * 亮/暗由父级 .theme-dark 决定（token 在 tokens.css 的 :root / .theme-dark 各定义一套）
 */
.dew-progress {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  font-family: var(--dew-font, inherit);
}

.dew-progress__track {
  position: relative;
  flex: 1;
  overflow: hidden;
  border-radius: var(--radius-full);
  background: var(--dew-progress-track-bg);
  box-shadow: var(--dew-progress-track-shadow);
}

.dew-progress--sm .dew-progress__track { height: 6px; }
.dew-progress--md .dew-progress__track { height: 9px; }
.dew-progress--lg .dew-progress__track { height: 13px; }

.dew-progress__fill {
  height: 100%;
  border-radius: var(--radius-full);
  background: var(--dew-progress-fill-bg);
  box-shadow: var(--dew-progress-fill-shadow);
  transition: width 0.6s var(--dew-bounce);
  position: relative;
  overflow: hidden;
}

/* 水面流光：一道高光带缓慢扫过（light 像水面反光，dark 像白光流动） */
.dew-progress__shine {
  position: absolute;
  inset: 0;
  background-image: linear-gradient(
    100deg,
    transparent 20%,
    var(--dew-progress-fill-highlight) 50%,
    transparent 80%
  );
  background-size: 250% 100%;
  background-repeat: no-repeat;
  animation: dew-progress-shine 3.2s ease-in-out infinite;
  pointer-events: none;
}

@keyframes dew-progress-shine {
  0%   { background-position: 180% 0; }
  100% { background-position: -120% 0; }
}

.dew-progress__label {
  font-size: 12px;
  font-weight: 600;
  color: var(--dew-text-heading);
  font-variant-numeric: tabular-nums;
  flex-shrink: 0;
}

/* 无障碍：尊重系统的减少动效偏好 */
@media (prefers-reduced-motion: reduce) {
  .dew-progress__shine { animation: none; }
}
</style>
