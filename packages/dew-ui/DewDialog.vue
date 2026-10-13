<template>
  <Teleport to="body">
    <!-- 遮罩：半透明深色 + backdrop-blur；:duration 兜底——两弹窗同时开合时
         transitionend 偶发不触发，离场元素滞留 DOM 且遮挡点击，强制到时移除 -->
    <Transition name="dew-dialog-scrim" :duration="320">
      <div v-if="modelValue" class="dew-dialog-scrim"></div>
    </Transition>

    <!-- 弹窗面板：居中容器 + 点击空白关闭 -->
    <Transition name="dew-dialog-panel" :duration="320">
      <div v-if="modelValue" class="dew-dialog-panel" @click.self="onBackdropClick">
        <div class="dew-dialog" role="dialog" aria-modal="true" ref="dialogRef" tabindex="-1"
             :class="{ 'dew-dialog--glass': glass }" :style="dialogStyle">
          <!-- 标题栏 -->
          <div class="dew-dialog__header">
            <slot name="header">
              <h3 class="dew-dialog__title">{{ title }}</h3>
            </slot>
            <button v-if="showClose" class="dew-dialog__close" @click="close" aria-label="关闭">
              <el-icon><Close /></el-icon>
            </button>
          </div>

          <!-- 正文 -->
          <div class="dew-dialog__body">
            <slot />
          </div>

          <!-- 底部操作 -->
          <div v-if="$slots.footer" class="dew-dialog__footer">
            <slot name="footer" />
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import { Close } from '@element-plus/icons-vue'

const props = defineProps({
  /** 显隐（v-model） */
  modelValue: { type: Boolean, default: false },
  /** 标题 */
  title: { type: String, default: '' },
  /** 宽度（number → px） */
  width: { type: [String, Number], default: 500 },
  /** 点遮罩关闭 */
  closeOnClickModal: { type: Boolean, default: true },
  /** Esc 关闭 */
  closeOnPressEscape: { type: Boolean, default: true },
  /** 显示右上角关闭按钮 */
  showClose: { type: Boolean, default: true },
  /** 液态玻璃表面——09-15 默认关：玻璃容器叠玻璃按钮/输入框对比度不足（用户反馈看不清），
      容器改扁平纯色（--dew-card-bg），内部按钮保留 glass 质感形成「容器实、操作玻璃」层次 */
  glass: { type: Boolean, default: false },
})

const emit = defineEmits(['update:modelValue', 'close'])

const dialogRef = ref(null)
const restoreFocusEl = ref(null)

const dialogStyle = computed(() => ({
  width: typeof props.width === 'number' ? `${props.width}px` : props.width,
}))

function close() {
  emit('update:modelValue', false)
  emit('close')
}

function onBackdropClick() {
  if (props.closeOnClickModal) close()
}

// ── 焦点圈定（a11y：aria-modal 的语义兑现）──────────────────────
// 弹窗内可聚焦元素（可见且未禁用）；Tab/Shift+Tab 在其中循环不跑出弹窗；
// 打开时聚焦正文区首个控件（无则面板自身），关闭时焦点还原触发元素。
const FOCUSABLE_SEL = [
  'button:not([disabled])', '[href]', 'input:not([disabled])',
  'select:not([disabled])', 'textarea:not([disabled])',
  '[contenteditable="true"]', '[tabindex]:not([tabindex="-1"])',
].join(', ')

function focusableIn(el) {
  if (!el) return []
  return [...el.querySelectorAll(FOCUSABLE_SEL)].filter(
    (n) => !n.disabled && !n.getAttribute('aria-hidden') && n.getClientRects().length > 0
  )
}

// 多弹窗同开时只有最顶层（DOM 顺序最后）的实例响应键盘圈定，
// 避免嵌套弹窗的两个 keydown 处理器互相抢焦点
function isTopDialog() {
  const panels = document.querySelectorAll('.dew-dialog')
  return panels.length === 0 || panels[panels.length - 1] === dialogRef.value
}

function onKeydown(e) {
  if (!isTopDialog()) return
  if (e.key === 'Escape' && props.closeOnPressEscape) {
    close()
    return
  }
  if (e.key !== 'Tab') return
  const items = focusableIn(dialogRef.value)
  if (!items.length) return
  const first = items[0]
  const last = items[items.length - 1]
  const active = document.activeElement
  if (e.shiftKey) {
    if (active === first || !dialogRef.value.contains(active)) {
      e.preventDefault()
      last.focus()
    }
  } else if (active === last || !dialogRef.value.contains(active)) {
    e.preventDefault()
    first.focus()
  }
}

// 打开：锁 body 滚动 + 键盘圈定 + 初始聚焦；关闭：焦点还原
watch(
  () => props.modelValue,
  (val) => {
    if (val) {
      restoreFocusEl.value = document.activeElement
      document.body.style.overflow = 'hidden'
      document.addEventListener('keydown', onKeydown, true)
      nextTick(() => {
        if (!dialogRef.value) return
        const body = dialogRef.value.querySelector('.dew-dialog__body')
        const target = focusableIn(body)[0] || dialogRef.value
        target.focus({ preventScroll: true })
      })
    } else {
      document.body.style.overflow = ''
      document.removeEventListener('keydown', onKeydown, true)
      const el = restoreFocusEl.value
      restoreFocusEl.value = null
      if (el && typeof el.focus === 'function' && document.contains(el)) {
        el.focus({ preventScroll: true })
      }
    }
  }
)

onBeforeUnmount(() => {
  document.body.style.overflow = ''
  document.removeEventListener('keydown', onKeydown)
})
</script>

<style scoped>
/* 遮罩 */
.dew-dialog-scrim {
  position: fixed;
  inset: 0;
  z-index: 2000;
  background: rgba(0, 0, 0, 0.4);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
}

/* 居中容器（点击空白=点遮罩） */
.dew-dialog-panel {
  position: fixed;
  inset: 0;
  z-index: 2001;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}

/* 弹窗表面 */
.dew-dialog {
  outline: none; /* tabindex=-1 兜底聚焦容器不显焦点环（键盘导航仍走内部控件） */
  position: relative;
  display: flex;
  flex-direction: column;
  max-width: calc(100vw - 40px);
  max-height: calc(100vh - 40px);
  overflow: hidden;
  border-radius: var(--radius-xl);
  border: 1px solid var(--dew-card-border);
  /* 09-15：不透明实色（--dew-card-bg 是半透明玻璃配方，此前透底「看不清」）；
     glass 模式（显式传 glass）仍覆盖为玻璃底 */
  background: var(--dew-dialog-bg, #ffffff);
  box-shadow: 0 24px 64px rgba(0, 0, 0, 0.2);
  color: var(--dew-text);
  font-family: var(--dew-font, inherit);
}

.dew-dialog--glass {
  background: var(--dew-card-glass-bg);
  border-color: var(--dew-card-glass-border);
  backdrop-filter: blur(28px) saturate(1.6);
  -webkit-backdrop-filter: blur(28px) saturate(1.6);
  box-shadow: 0 24px 64px rgba(0, 0, 0, 0.25), inset 0 0 0 0.5px rgba(255, 255, 255, 0.2);
}

/* 标题栏 */
.dew-dialog__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18px 24px 12px;
  flex-shrink: 0;
}

.dew-dialog__title {
  font-size: 18px;
  font-weight: 700;
  color: var(--dew-text-heading);
  margin: 0;
}

.dew-dialog__close {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  flex-shrink: 0;
  margin-left: 12px;
  border: none;
  background: none;
  border-radius: 8px;
  cursor: pointer;
  color: var(--dew-text-muted);
  font-size: 18px;
  transition: background 0.2s ease, color 0.2s ease;
}

.dew-dialog__close:hover {
  background: var(--dew-popover-item-hover);
  color: var(--dew-text-heading);
}

/* 正文 */
.dew-dialog__body {
  padding: 0 24px 20px;
  overflow-y: auto;
  overflow-x: hidden;   /* 单轴滚动须显式关掉横轴：overflow-y 非 visible 时横轴会被算成 auto，内容横向溢 1px 就出底部横滚动条 */
  flex: 1;
  font-size: 14px;
  line-height: 1.6;
}

/* 底部 */
.dew-dialog__footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding: 12px 24px 18px;
  flex-shrink: 0;
}

/* ── 过渡动画 ── */
/* 遮罩：淡入淡出 */
.dew-dialog-scrim-enter-active,
.dew-dialog-scrim-leave-active {
  transition: opacity 0.3s ease;
}
.dew-dialog-scrim-enter-from,
.dew-dialog-scrim-leave-to {
  opacity: 0;
}

/* 面板：淡入淡出（09-15 撤 scale——transform 动画期间面板处于合成层，内部 glass
   按钮/输入框的 backdrop-filter 采样异常，动画结束采样突变=「亮一下再恢复」闪烁） */
.dew-dialog-panel-enter-active {
  transition: opacity 0.25s ease;
}
.dew-dialog-panel-leave-active {
  transition: opacity 0.18s ease-in;
}
.dew-dialog-panel-enter-from,
.dew-dialog-panel-leave-to {
  opacity: 0;
}
</style>
