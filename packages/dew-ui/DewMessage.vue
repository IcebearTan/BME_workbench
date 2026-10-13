<template>
  <div class="dew-message-container">
    <TransitionGroup name="dew-message" tag="div" class="dew-message-list">
      <div
        v-for="t in toasts"
        :key="t.id"
        class="dew-message"
        :class="`dew-message--${t.type}`"
      >
        <el-icon class="dew-message__icon"><component :is="iconFor(t.type)" /></el-icon>
        <span class="dew-message__text">{{ t.text }}</span>
        <button class="dew-message__close" aria-label="关闭" @click="emit('close', t.id)">
          <el-icon><Close /></el-icon>
        </button>
      </div>
    </TransitionGroup>
  </div>
</template>

<script setup>
import { CircleCheckFilled, WarningFilled, CircleCloseFilled, InfoFilled, Close } from '@element-plus/icons-vue'

defineProps({
  toasts: { type: Array, default: () => [] },
})
const emit = defineEmits(['close'])

const ICONS = {
  success: CircleCheckFilled,
  warning: WarningFilled,
  error: CircleCloseFilled,
  info: InfoFilled,
}
const iconFor = (type) => ICONS[type] || InfoFilled
</script>

<!-- 非 scoped：toast 挂在 body，需命中祖先 body 上的 .theme-dark -->
<style>
.dew-message-container {
  position: fixed;
  top: 24px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 3000;
  pointer-events: none;
}
.dew-message-list {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  position: relative;
}
.dew-message {
  pointer-events: auto;
  display: flex;
  align-items: center;
  gap: 9px;
  min-width: 220px;
  max-width: 380px;
  padding: 11px 14px;
  border-radius: 14px;
  font-size: 13px;
  line-height: 1.5;
  font-weight: 500;
  color: var(--dew-text-heading, #1f2937);
  background: rgba(255, 255, 255, 0.72);
  backdrop-filter: blur(20px) saturate(180%);
  -webkit-backdrop-filter: blur(20px) saturate(180%);
  border: 0.5px solid rgba(255, 255, 255, 0.6);
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.1), inset 0 1px 0 rgba(255, 255, 255, 0.55);
}
.dew-message__icon {
  font-size: 18px;
  flex-shrink: 0;
}
.dew-message--success .dew-message__icon { color: #22c55e; }
.dew-message--warning .dew-message__icon { color: #f59e0b; }
.dew-message--error   .dew-message__icon { color: #ef4444; }
.dew-message--info    .dew-message__icon { color: #3b82f6; }
.dew-message__text {
  flex: 1;
}
.dew-message__close {
  border: none;
  background: transparent;
  cursor: pointer;
  padding: 2px;
  display: flex;
  align-items: center;
  border-radius: 6px;
  color: var(--dew-text-faint, #9ca3af);
  transition: color 0.15s;
}
.dew-message__close:hover {
  color: var(--dew-text-heading, #1f2937);
}
.dew-message__close .el-icon {
  font-size: 14px;
}

/* 暗色模式（应用切暗色时 body 带 .theme-dark） */
.theme-dark .dew-message {
  background: rgba(40, 40, 48, 0.78);
  border-color: rgba(255, 255, 255, 0.12);
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.4), inset 0 1px 0 rgba(255, 255, 255, 0.08);
  color: rgba(255, 255, 255, 0.9);
}

/* 进出场：水滴弹性进场 + 离场让位 */
.dew-message-enter-active {
  transition:
    opacity 0.35s var(--dew-bounce, cubic-bezier(0.34, 1.56, 0.64, 1)),
    transform 0.35s var(--dew-bounce, cubic-bezier(0.34, 1.56, 0.64, 1));
}
.dew-message-leave-active {
  transition: opacity 0.25s ease, transform 0.25s ease;
  position: absolute;
}
.dew-message-move {
  transition: transform 0.35s var(--dew-bounce, cubic-bezier(0.34, 1.56, 0.64, 1));
}
.dew-message-enter-from {
  opacity: 0;
  transform: translateY(-20px);
}
.dew-message-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}
</style>
