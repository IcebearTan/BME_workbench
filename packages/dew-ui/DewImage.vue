<template>
  <!--
    DewImage：全站图片加载统一入口（静态资源 /media/ 链路的加载态方案）。
    三态：loading（骨架呼吸占位，尺寸先占住防 CLS）→ loaded（淡入）→ error（兜底：circle 显首字 / rect 显占位图标）。
    数据图、头像、封面、勋章、轮播底图一律走这里，业务页不再裸 <img>。
  -->
  <span
    class="dew-image"
    :class="[`dew-image--${shape}`, { 'dew-image--loaded': state === 'loaded' }]"
    :style="boxStyle"
    :aria-hidden="state !== 'loaded'"
  >
    <!-- 图片本体：淡入由容器 class 驱动；原生懒加载 + 异步解码 -->
    <img
      v-if="src"
      ref="imgRef"
      class="dew-image__img"
      :src="src"
      :alt="alt || ''"
      :loading="lazy ? 'lazy' : 'eager'"
      :decoding="decoding"
      :style="imgStyle"
      @load="onLoad"
      @error="onError"
    >

    <!-- 占位层：loading 骨架 / error 兜底（loaded 后让位） -->
    <span v-if="state !== 'loaded'" class="dew-image__placeholder" :class="`dew-image__placeholder--${state}`">
      <template v-if="state === 'error'">
        <span v-if="shape === 'circle'" class="dew-image__initial">{{ initial }}</span>
        <svg v-else class="dew-image__broken" viewBox="0 0 24 24" fill="none" stroke="currentColor"
             stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
          <rect x="3" y="5" width="18" height="14" rx="2" />
          <circle cx="9" cy="10" r="1.4" />
          <path d="m3 17 5.2-4.6a1.6 1.6 0 0 1 2.1 0L14 16" />
          <path d="m14.5 14.5 1.6-1.4a1.6 1.6 0 0 1 2.1 0L21 16" />
        </svg>
      </template>
    </span>
  </span>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'

const props = defineProps({
  /** 图片地址；null/空直接进 error 兜底态 */
  src: { type: String, default: null },
  alt: { type: String, default: '' },
  /** 形态：rect（封面/勋章/轮播） | circle（头像） */
  shape: { type: String, default: 'rect' },
  /** circle 直径（数字=px），与 DewSkeleton 口径一致；rect 可只给宽高或 ratio */
  size: { type: [String, Number], default: null },
  width: { type: [String, Number], default: null },
  height: { type: [String, Number], default: null },
  /** 宽高比盒（如 '16/9'、'1/1'），配合 width 单边即可占住版位防 CLS */
  ratio: { type: String, default: null },
  /** object-fit，默认 cover */
  fit: { type: String, default: 'cover' },
  /** object-position（如 '50% 30%'，banner 显示焦点） */
  position: { type: String, default: null },
  /** 错误/空 src 兜底显示的字符（circle 头像首字；缺省取 alt 首字） */
  initial: { type: String, default: null },
  /** 原生懒加载（默认开；首屏关键图可关） */
  lazy: { type: Boolean, default: true },
  decoding: { type: String, default: 'async' },
  /** 淡入时长（ms，0=关） */
  fadeDuration: { type: Number, default: 350 },
})

const emit = defineEmits(['loaded', 'error'])

const imgRef = ref(null)
const state = ref('loading')          // loading | loaded | error

const toPx = (v) => (typeof v === 'number' ? `${v}px` : v)

const boxStyle = computed(() => {
  const s = {}
  if (props.ratio) s.aspectRatio = props.ratio
  if (props.size != null) {
    s.width = toPx(props.size)
    s.height = toPx(props.size)
    // 首字兜底按直径缩放：__initial 用 0.42em，根字号锚定直径后随头像大小走
    // （此前根字号靠页面继承 ≈13px，任何头像下首字都只有 ~5px）
    s.fontSize = toPx(props.size)
  }
  if (props.width != null) s.width = toPx(props.width)
  if (props.height != null) s.height = toPx(props.height)
  if (props.fadeDuration) s['--dew-image-fade'] = `${props.fadeDuration}ms`
  return s
})

const imgStyle = computed(() => {
  const s = { objectFit: props.fit }
  if (props.position) s.objectPosition = props.position
  return s
})

const initial = computed(() => {
  const raw = props.initial ?? (props.alt || '?').trim()
  return raw ? raw.slice(0, 1).toUpperCase() : '?'
})

function onLoad() {
  state.value = 'loaded'
  emit('loaded')
}

function onError() {
  state.value = 'error'
  emit('error')
}

// 缓存命中时 load 可能在监听器挂上前就完成（img.complete 兜底）
function syncFromComplete() {
  const el = imgRef.value
  if (el && el.complete) {
    if (el.naturalWidth > 0) state.value = 'loaded'
    else if (el.src) state.value = 'error'
  }
}

onMounted(syncFromComplete)

// 换图（轮播复用、头像更新）：重置三态；空 src 直接兜底不发请求
watch(() => props.src, (v) => {
  state.value = v ? 'loading' : 'error'
  if (v) requestAnimationFrame(syncFromComplete)
}, { immediate: true })
</script>

<style scoped>
.dew-image {
  position: relative;
  display: inline-block;
  overflow: hidden;
  flex-shrink: 0;
  /* 兜底背景：加载中透过半透明骨架能看到，也防 error 态露底 */
  background: var(--dew-skeleton-bg);
}

.dew-image--circle {
  border-radius: 50%;
}

.dew-image--rect {
  border-radius: var(--radius-md, 10px);
}

.dew-image__img {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  opacity: 0;
  transition: opacity var(--dew-image-fade, 350ms) ease;
}

.dew-image--loaded .dew-image__img {
  opacity: 1;
}

/* 占位层：与骨架同源 token，呼吸节奏对齐 DewSkeleton */
.dew-image__placeholder {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--dew-skeleton-bg);
  animation: dew-image-breathe 1.4s ease-in-out infinite;
}

.dew-image__placeholder--error {
  animation: none;
  opacity: 0.9;
}

@keyframes dew-image-breathe {
  0%, 100% { opacity: 0.5; }
  50% { opacity: 1; }
}

/* circle 错误兜底：首字符 */
.dew-image__initial {
  font-size: 0.42em;
  font-weight: 600;
  color: var(--dew-text-muted, #98a2b3);
  user-select: none;
}

/* rect 错误兜底：占位山图标（尺寸随容器） */
.dew-image__broken {
  width: 32%;
  height: 32%;
  color: var(--dew-text-muted, #98a2b3);
  opacity: 0.6;
}

@media (prefers-reduced-motion: reduce) {
  .dew-image__img { transition: none; }
  .dew-image__placeholder { animation: none; opacity: 0.7; }
}
</style>
