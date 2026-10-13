<template>
  <div class="dew-popover-wrapper" ref="wrapperRef">
    <div
      ref="triggerRef"
      class="dew-popover__trigger"
      @click="onTriggerClick"
      @mouseenter="onTriggerEnter"
      @mouseleave="onTriggerLeave"
    >
      <slot name="trigger" />
    </div>

    <Teleport to="body">
      <Transition
        :name="transitionName"
        @before-enter="onBeforeEnter"
        @enter="onEnter"
        @after-leave="onAfterLeave"
      >
        <div
          v-if="visible"
          ref="popoverRef"
          class="dew-popover"
          :class="[`dew-popover--${actualPlacement}`, { 'dew-popover--arrow': showArrow }]"
          :style="popoverStyle"
          @mouseenter="onPopoverEnter"
          @mouseleave="onPopoverLeave"
        >
          <div v-if="showArrow" class="dew-popover__arrow" :style="arrowStyle" />
          <slot />
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, reactive, computed, watch, nextTick, onMounted, onBeforeUnmount } from 'vue'

const props = defineProps({
  /** v-model 控制显隐（不绑时走内部状态，支持 hover tooltip 等非受控用法） */
  modelValue: { type: Boolean, default: undefined },
  /** 触发方式 click | hover */
  trigger: { type: String, default: 'click' },
  /** 弹出位置 bottom | top */
  placement: { type: String, default: 'bottom' },
  /** 是否显示箭头 */
  showArrow: { type: Boolean, default: true },
  /** 浮层宽度 */
  width: { type: [String, Number], default: '' },
  /** 距触发器间距 */
  offset: { type: Number, default: 8 },
  /** 禁用 */
  disabled: { type: Boolean, default: false },
})

const emit = defineEmits(['update:modelValue', 'show', 'hide'])

const wrapperRef = ref(null)
const triggerRef = ref(null)
const popoverRef = ref(null)

// 未绑 v-model（modelValue === undefined）时用内部状态，实现非受控（hover tooltip）
const internalVisible = ref(false)
const visible = computed({
  get: () => (props.modelValue !== undefined ? props.modelValue : internalVisible.value),
  set: (val) => {
    if (props.modelValue !== undefined) emit('update:modelValue', val)
    else internalVisible.value = val
  },
})

// 实际 placement（可能因视口翻转而改变）
const actualPlacement = ref(props.placement)
const position = reactive({ left: 0, top: 0 })
const arrowPos = reactive({ left: '', top: '' })

// hover 模式用
let hideTimer = null

function onTriggerClick() {
  if (props.disabled || props.trigger !== 'click') return
  visible.value = !visible.value
}

function onTriggerEnter() {
  if (props.disabled || props.trigger !== 'hover') return
  clearTimeout(hideTimer)
  visible.value = true
}

function onTriggerLeave() {
  if (props.trigger !== 'hover') return
  scheduleHide()
}

function onPopoverEnter() {
  if (props.trigger !== 'hover') return
  clearTimeout(hideTimer)
}

function onPopoverLeave() {
  if (props.trigger !== 'hover') return
  scheduleHide()
}

function scheduleHide() {
  hideTimer = setTimeout(() => { visible.value = false }, 150)
}

// ── 定位逻辑 ──
function updatePosition() {
  if (!triggerRef.value || !popoverRef.value) return

  const triggerRect = triggerRef.value.getBoundingClientRect()
  const popRect = popoverRef.value.getBoundingClientRect()
  const gap = props.offset + (props.showArrow ? 6 : 0)
  const vw = window.innerWidth
  const vh = window.innerHeight

  let placement = props.placement

  // 计算主轴位置
  let top, left

  // 水平居中
  left = triggerRect.left + triggerRect.width / 2 - popRect.width / 2

  if (placement === 'bottom') {
    top = triggerRect.bottom + gap
    // 视口翻转：下方空间不足且上方够
    if (top + popRect.height > vh && triggerRect.top - gap - popRect.height > 0) {
      placement = 'top'
      top = triggerRect.top - gap - popRect.height
    }
  } else {
    top = triggerRect.top - gap - popRect.height
    // 视口翻转：上方空间不足且下方够
    if (top < 0 && triggerRect.bottom + gap + popRect.height <= vh) {
      placement = 'bottom'
      top = triggerRect.bottom + gap
    }
  }

  // 水平边界约束
  if (left < 8) left = 8
  if (left + popRect.width > vw - 8) left = vw - popRect.width - 8

  actualPlacement.value = placement
  position.left = left
  position.top = top

  // 箭头水平位置（指向 trigger 中心）
  const arrowLeft = triggerRect.left + triggerRect.width / 2 - left
  arrowPos.left = `${Math.max(12, Math.min(arrowLeft, popRect.width - 12))}px`
}

const popoverStyle = computed(() => {
  const style = {
    left: `${position.left}px`,
    top: `${position.top}px`,
  }
  if (props.width) {
    style.width = typeof props.width === 'number' ? `${props.width}px` : props.width
  }
  return style
})

const arrowStyle = computed(() => ({
  left: arrowPos.left,
}))

const transitionName = computed(() =>
  `dew-popover--${actualPlacement.value}`
)

// ── 过渡钩子 ──
function onBeforeEnter() {
  // 进入前先定位（此时元素还不可见，用 v-if 会在下一帧渲染）
}

function onEnter() {
  nextTick(updatePosition)
}

function onAfterLeave() {
  // 清理
}

// ── 点击外部关闭 ──
function onDocumentClick(e) {
  if (props.trigger !== 'click' || !visible.value) return
  const target = e.target
  if (
    triggerRef.value?.contains(target) ||
    popoverRef.value?.contains(target)
  ) return
  visible.value = false
}

// ── 滚动/resize 时更新位置 ──
function onScroll() {
  if (visible.value) updatePosition()
}

// 监听 visible 变化来更新位置（show/hide 供懒加载等内容按需拉取）
watch(visible, (val) => {
  if (val) {
    emit('show')
    nextTick(updatePosition)
  } else {
    emit('hide')
  }
})

// 监听 placement prop 变化
watch(() => props.placement, () => {
  actualPlacement.value = props.placement
})

onMounted(() => {
  document.addEventListener('click', onDocumentClick, true)
  window.addEventListener('resize', onScroll)
  window.addEventListener('scroll', onScroll, true)
})

onBeforeUnmount(() => {
  document.removeEventListener('click', onDocumentClick, true)
  window.removeEventListener('resize', onScroll)
  window.removeEventListener('scroll', onScroll, true)
  clearTimeout(hideTimer)
})
</script>

<style scoped>
.dew-popover-wrapper {
  display: inline-flex;
}

.dew-popover__trigger {
  display: inline-flex;
}

/* ── 浮层本体（iOS 风格） ── */
.dew-popover {
  position: fixed;
  /* 2200：须盖过 DewDialog 面板（2001）——弹窗内 DewSelect 下拉否则被面板压住隔玻璃透字 */
  z-index: 2200;
  background: var(--dew-popover-bg);
  border: 1px solid var(--dew-popover-border);
  border-radius: var(--dew-popover-radius);
  box-shadow: var(--dew-popover-shadow);
  color: var(--dew-popover-text);
  font-family: var(--dew-font, inherit);
  overflow: visible;
}

/* ── 箭头 ── */
.dew-popover__arrow {
  position: absolute;
  width: 12px;
  height: 12px;
  background: var(--dew-popover-bg);
  transform: rotate(45deg);
  z-index: -1;
}

/* bottom 箭头在顶部 */
.dew-popover--bottom .dew-popover__arrow {
  top: -7px;
  border-bottom: none;
  border-right: none;
}

/* top 箭头在底部 */
.dew-popover--top .dew-popover__arrow {
  bottom: -7px;
  border-top: none;
  border-left: none;
}

/* ── 过渡动画 ── */
.dew-popover--bottom-enter-active,
.dew-popover--top-enter-active {
  transition: opacity 0.2s cubic-bezier(0.16, 1, 0.3, 1), transform 0.2s cubic-bezier(0.16, 1, 0.3, 1);
}
.dew-popover--bottom-leave-active,
.dew-popover--top-leave-active {
  transition: opacity 0.15s ease-in, transform 0.15s ease-in;
}

/* bottom: 从上方缩放进入 */
.dew-popover--bottom-enter-from {
  opacity: 0;
  transform: scaleY(0.92) translateY(-4px);
  transform-origin: top center;
}
.dew-popover--bottom-leave-to {
  opacity: 0;
  transform: scaleY(0.95) translateY(-2px);
  transform-origin: top center;
}

/* top: 从下方缩放进入 */
.dew-popover--top-enter-from {
  opacity: 0;
  transform: scaleY(0.92) translateY(4px);
  transform-origin: bottom center;
}
.dew-popover--top-leave-to {
  opacity: 0;
  transform: scaleY(0.95) translateY(2px);
  transform-origin: bottom center;
}
</style>
