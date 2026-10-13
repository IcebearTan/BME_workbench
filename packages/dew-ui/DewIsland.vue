<template>
  <div class="dew-island-wrapper" ref="wrapperRef">
    <!-- 触发器（收起态，点击切换；展开时被浮岛吸收隐藏） -->
    <div
      ref="triggerRef"
      class="dew-island__trigger"
      :class="{ 'dew-island__trigger--open': visible }"
      @click="onTriggerClick"
    >
      <slot name="trigger" />
    </div>

    <!-- 展开态浮岛：Teleport 到 body，定位居中于触发器、向下绽放 -->
    <Teleport to="body">
      <Transition name="dew-island">
        <div
          v-if="visible"
          ref="panelRef"
          class="dew-island"
          :style="panelStyle"
        >
          <slot />
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, reactive, computed, watch, nextTick, onMounted, onBeforeUnmount } from 'vue'

const props = defineProps({
  /** 展开/收起（v-model） */
  modelValue: { type: Boolean, default: false },
  /** 禁用点击展开 */
  disabled: { type: Boolean, default: false },
  /** 面板宽度（number → px，string 原样使用，如 'min(360px, calc(100vw - 24px))'） */
  panelWidth: { type: [String, Number], default: 360 },
  /** 视口边缘留白（px） */
  margin: { type: Number, default: 12 },
})

const emit = defineEmits(['update:modelValue'])

const wrapperRef = ref(null)
const triggerRef = ref(null)
const panelRef = ref(null)

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val),
})

const position = reactive({ left: 0, top: 0 })

// ── 点击触发器：切换展开/收起 ──
function onTriggerClick() {
  if (props.disabled) return
  visible.value = !visible.value
}

// ── 点击空白收起（capture 阶段；落在触发器/面板内则忽略） ──
// 注：展开那一下点击也落在此监听里，但因 triggerRef.contains(target) 为 true 会提前 return，
// 不会把自己关掉——故无需标志位/定时器。
function onDocumentClick(e) {
  if (!visible.value) return
  const target = e.target
  if (
    triggerRef.value?.contains(target) ||
    panelRef.value?.contains(target)
  ) return
  visible.value = false
}

// ── 定位：面板中心对齐触发器中心（从正中间绽放） ──
function updatePosition() {
  if (!triggerRef.value || !panelRef.value) return
  const t = triggerRef.value.getBoundingClientRect() // 触发器视口位置（无 transform，准确）
  const el = panelRef.value
  // 用 offsetWidth/offsetHeight 取「未缩放」的真实尺寸——getBoundingClientRect 会
  // 带上 enter-from 的 transform scale(0.4)，量到 0.4× 尺寸导致居中算错
  const pw = el.offsetWidth
  const ph = el.offsetHeight
  const vw = window.innerWidth
  const vh = window.innerHeight
  const m = props.margin

  // 水平：面板中心 == 触发器中心（从中间对称展开）
  let left = t.left + t.width / 2 - pw / 2
  // 垂直：面板顶边 == 触发器顶边（iOS 岛逻辑：顶边对齐、向下生长，避免顶部溢出）
  let top = t.top

  // 钳制到视口（留 margin 边距），保证整块可见
  if (left < m) left = m
  if (left + pw > vw - m) left = vw - pw - m
  if (top < m) top = m
  if (top + ph > vh - m) top = vh - ph - m

  position.left = left
  position.top = top
}

const panelStyle = computed(() => ({
  left: `${position.left}px`,
  top: `${position.top}px`,
  width: typeof props.panelWidth === 'number' ? `${props.panelWidth}px` : props.panelWidth,
}))

// ── 滚动/resize 重定位 ──
function onScroll() {
  if (visible.value) updatePosition()
}

watch(visible, (val) => {
  if (val) nextTick(updatePosition)
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
})
</script>

<style scoped>
.dew-island-wrapper {
  display: inline-flex;
}

.dew-island__trigger {
  display: inline-flex;
  transition: opacity 0.12s ease;
}

/* 展开时触发器被浮岛吸收：淡出 + 不拦截点击（避免双层重叠） */
.dew-island__trigger--open {
  opacity: 0;
  pointer-events: none;
}

/* ── 浮岛面板（液态玻璃 Dynamic Island） ── */
.dew-island {
  position: fixed;
  z-index: 2000;
  background: var(--dew-island-bg);
  border: 1px solid var(--dew-island-border);
  border-radius: var(--dew-island-radius);
  box-shadow: var(--dew-island-shadow);
  -webkit-backdrop-filter: blur(30px) saturate(160%);
  backdrop-filter: blur(30px) saturate(160%);
  overflow: hidden;
  box-sizing: border-box;
  color: var(--dew-text);
  font-family: var(--dew-font, inherit);
}

/* ── 水滴绽放：从顶边中心缩放（水平对称、向下生长）+ 圆角 morph ── */
.dew-island-enter-active {
  transition:
    opacity 0.3s var(--dew-bounce),
    transform 0.34s var(--dew-bounce),
    border-radius 0.3s cubic-bezier(0.16, 1, 0.3, 1);
  transform-origin: top center;
}
.dew-island-leave-active {
  transition:
    opacity 0.2s ease-in,
    transform 0.2s ease-in,
    border-radius 0.2s ease-in;
  transform-origin: top center;
}
/* 起始/终止：缩成胶囊大小 + 全圆角，模拟「胶囊长成面板」 */
.dew-island-enter-from,
.dew-island-leave-to {
  opacity: 0;
  transform: scale(0.4);
  border-radius: 999px;
}
</style>
