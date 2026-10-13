<template>
  <div
    ref="wrapRef"
    class="dew-input"
    :class="[
      `dew-input--${size}`,
      {
        'dew-input--focused': focused,
        'dew-input--disabled': disabled,
        'dew-input--error': hasError,
        'dew-input--round': round,
        'dew-input--expand': expandOnFocus,
        'dew-input--expanded': expandOnFocus && focused,
        'dew-input--has-prefix': prefixIcon,
        'dew-input--has-suffix': suffixIcon,
        'dew-input--has-clear': clearable && modelValue,
        'dew-input--has-toggle': type === 'password',
        'dew-input--textarea': type === 'textarea',
      }
    ]"
    :style="expandStyle"
    @mouseenter="onEnter"
    @mousemove="onMove"
    @mouseleave="onLeave"
  >
    <!-- 折射层（聚焦时显现） -->
    <span class="dew-input__refraction" :style="refractionStyle"></span>
    <!-- 色散层（聚焦时显现） -->
    <span class="dew-input__chromatic" :style="chromaticStyle"></span>
    <!-- 聚焦外发光层 -->
    <span class="dew-input__glow" :style="glowStyle"></span>

    <!-- 前缀图标 -->
    <span v-if="prefixIcon" class="dew-input__prefix">
      <component :is="prefixIcon" class="dew-input__icon" />
    </span>

    <!-- 多行输入框 -->
    <textarea
      v-if="type === 'textarea'"
      ref="inputRef"
      class="dew-input__inner dew-input__textarea"
      v-model="inputModel"
      :placeholder="placeholder"
      :disabled="disabled"
      :rows="rows"
      @input="onInput"
      @focus="onFocus"
      @blur="onBlur"
      @compositionstart="composing = true"
      @compositionend="onCompositionEnd"
    ></textarea>
    <!-- 单行输入框 -->
    <input
      v-else
      ref="inputRef"
      class="dew-input__inner"
      :type="showPassword ? 'text' : nativeType"
      v-model="inputModel"
      :placeholder="placeholder"
      :disabled="disabled"
      @input="onInput"
      @focus="onFocus"
      @blur="onBlur"
      @keyup.enter="$emit('enter', $event)"
      @compositionstart="composing = true"
      @compositionend="onCompositionEnd"
    />

    <!-- 后缀图标 -->
    <span v-if="suffixIcon && !(!disabled && ((clearable && modelValue) || type === 'password'))" class="dew-input__suffix">
      <component :is="suffixIcon" class="dew-input__icon" />
    </span>

    <!-- 清除按钮 -->
    <span v-if="clearable && modelValue && !disabled" class="dew-input__clear" @mousedown.prevent @click="onClear">
      <svg viewBox="0 0 16 16" width="14" height="14" fill="currentColor">
        <path d="M4.646 4.646a.5.5 0 0 1 .708 0L8 7.293l2.646-2.647a.5.5 0 0 1 .708.708L8.707 8l2.647 2.646a.5.5 0 0 1-.708.708L8 8.707l-2.646 2.647a.5.5 0 0 1-.708-.708L7.293 8 4.646 5.354a.5.5 0 0 1 0-.708z"/>
      </svg>
    </span>

    <!-- 密码切换 -->
    <span v-if="type === 'password' && !disabled" class="dew-input__toggle" @mousedown.prevent @click="showPassword = !showPassword">
      <svg v-if="showPassword" viewBox="0 0 16 16" width="16" height="16" fill="currentColor">
        <path d="M10.5 8a2.5 2.5 0 1 1-5 0 2.5 2.5 0 0 1 5 0z"/>
        <path d="M0 8s3-5.5 8-5.5S16 8 16 8s-3 5.5-8 5.5S0 8 0 8zm8 3.5a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7z"/>
      </svg>
      <svg v-else viewBox="0 0 16 16" width="16" height="16" fill="currentColor">
        <path d="m10.79 12.912-1.614-1.615a3.5 3.5 0 0 1-4.474-4.474l-2.186-2.186C1.832 5.917 1 7.254 1 8s3 5.5 8 5.5c.95 0 1.84-.133 2.637-.364l-.847-.224zM5.21 3.088A7.04 7.04 0 0 1 8 2.5c5 0 8 5.5 8 5.5s-.892 1.486-2.637 2.962l-.847-.224 1.614-1.615A3.5 3.5 0 0 0 6.08 5.562l-2.186-2.186z"/>
        <path fill-rule="evenodd" d="M13.354 2.354a.5.5 0 0 0-.708-.708l-10 10a.5.5 0 0 0 .708.708l10-10z"/>
      </svg>
    </span>
  </div>
</template>

<script setup>
import { ref, reactive, computed, nextTick, onMounted, onBeforeUnmount } from 'vue'

const props = defineProps({
  modelValue: { type: String, default: '' },
  placeholder: { type: String, default: '' },
  type: { type: String, default: 'text' },
  size: { type: String, default: 'md' },
  clearable: { type: Boolean, default: false },
  disabled: { type: Boolean, default: false },
  error: { type: Boolean, default: false },
  round: { type: Boolean, default: false },
  expandOnFocus: { type: Boolean, default: false },
  prefixIcon: { type: [Object, null], default: null },
  suffixIcon: { type: [Object, null], default: null },
  /** 多行输入框行数（type='textarea' 时生效） */
  rows: { type: Number, default: 4 },
})

const emit = defineEmits(['update:modelValue', 'focus', 'blur', 'input', 'clear', 'enter'])

const inputModel = computed({
  get: () => props.modelValue,
  set: value => emit('update:modelValue', value),
})

const wrapRef = ref(null)
const inputRef = ref(null)
const focused = ref(false)
const showPassword = ref(false)
const formError = ref(false)
const state = reactive({ hovering: false, x: 0.5, y: 0.5 })

// 综合错误状态：手动传 error prop OR 自动检测 el-form-item 的 is-error
const hasError = computed(() => props.error || formError.value)

// 自动感知父级 el-form-item 的验证状态
// el-form 校验失败时会给 form-item 加上 .is-error class
let observer = null
onMounted(() => {
  const el = wrapRef.value
  if (!el) return
  const formItem = el.closest('.el-form-item')
  if (!formItem) return

  formError.value = formItem.classList.contains('is-error')
  observer = new MutationObserver(() => {
    formError.value = formItem.classList.contains('is-error')
  })
  observer.observe(formItem, { attributes: true, attributeFilter: ['class'] })
})
onBeforeUnmount(() => observer?.disconnect())

const nativeType = computed(() => {
  // 09-15 修：此前只认 email/password，其余（含 number/date）全降级 text——评分弹窗
  // 因此一直显示为文本框。白名单透传原生 type，未知回退 text
  const allowed = ['email', 'password', 'number', 'date', 'tel', 'url', 'search']
  return allowed.includes(props.type) ? props.type : 'text'
})

// 聚焦展开动画（宽度通过 CSS 自定义属性驱动，transition 在 CSS 中用 --dew-bounce）
const expandStyle = computed(() => {
  if (!props.expandOnFocus) return null
  return {
    width: focused.value ? 'var(--dew-input-expand-width-focus)' : 'var(--dew-input-expand-width)',
  }
})

const composing = ref(false)

function onInput(e) {
  // 中文输入法组合期间不更新 modelValue，避免打断拼音输入
  // composing ref 与原生 e.isComposing 双保险（ref 不再进模板，避免 compositionstart 触发重渲染清空输入框）
  if (composing.value || e.isComposing) return
  emit('input', e.target.value)
  // 转发事件到根元素，让 el-form-item 能监听到
  wrapRef.value?.dispatchEvent(new Event('input', { bubbles: true }))
}

function onCompositionEnd(e) {
  composing.value = false
  // v-model 负责同步最终值，这里只广播组件级 input 事件
  emit('input', e.target.value)
  wrapRef.value?.dispatchEvent(new Event('input', { bubbles: true }))
}

function onFocus(e) {
  if (props.disabled) return
  focused.value = true
  emit('focus', e)
  wrapRef.value?.dispatchEvent(new Event('focus', { bubbles: true }))
}

function onBlur(e) {
  focused.value = false
  emit('blur', e)
  wrapRef.value?.dispatchEvent(new Event('blur', { bubbles: true }))
}

function onClear() {
  emit('update:modelValue', '')
  emit('clear')
}

function onEnter() { state.hovering = true }
function onMove(e) {
  if (!wrapRef.value) return
  const r = wrapRef.value.getBoundingClientRect()
  state.x = (e.clientX - r.left) / r.width
  state.y = (e.clientY - r.top) / r.height
}
function onLeave() { state.hovering = false; state.x = 0.5; state.y = 0.5 }

// 折射层 — 仅聚焦时显现
const refractionStyle = computed(() => {
  if (!focused.value) return { opacity: '0' }
  const cx = (state.x * 100).toFixed(1)
  const cy = (state.y * 100).toFixed(1)
  const i = state.hovering ? 0.5 : 0.3
  return {
    background: `radial-gradient(ellipse at ${cx}% ${cy}%, rgba(255,255,255,${(0.4*i).toFixed(2)}) 0%, rgba(180,200,255,${(0.2*i).toFixed(2)}) 25%, rgba(200,160,255,${(0.1*i).toFixed(2)}) 45%, rgba(255,180,200,${(0.06*i).toFixed(2)}) 65%, transparent 100%)`,
    opacity: '1',
    transition: 'opacity 0.35s ease',
  }
})

// 色散层
const chromaticStyle = computed(() => {
  if (!focused.value) return { opacity: '0' }
  const cx = (state.x * 100).toFixed(1)
  const cy = (state.y * 100).toFixed(1)
  return {
    opacity: '0.8',
    background: `radial-gradient(ellipse at ${cx}% ${cy}%, rgba(255,200,200,0.06) 0%, rgba(200,255,200,0.05) 30%, rgba(200,200,255,0.07) 60%, transparent 100%)`,
    transition: 'opacity 0.35s ease',
  }
})

// 外发光层
const glowStyle = computed(() => ({
  opacity: focused.value ? '1' : '0',
}))

function focus() { inputRef.value?.focus() }

function insertText(text) {
  const element = inputRef.value
  if (!element || props.disabled) return false

  const value = String(props.modelValue ?? '')
  const insertion = String(text ?? '')
  const end = element.selectionEnd ?? value.length
  const start = element.selectionStart ?? end
  const nextValue = value.slice(0, start) + insertion + value.slice(end)
  const caret = start + insertion.length

  inputModel.value = nextValue
  nextTick(() => {
    element.focus()
    element.setSelectionRange(caret, caret)
  })
  return true
}
defineExpose({ focus, insertText })
</script>

<style scoped>
.dew-input {
  position: relative;
  display: inline-flex;
  align-items: center;
  isolation: isolate;
  backdrop-filter: blur(20px) saturate(1.5);
  -webkit-backdrop-filter: blur(20px) saturate(1.5);
  background: var(--dew-input-bg);
  border: 1px solid var(--dew-input-border);
  box-shadow: var(--dew-input-shadow);
  font-family: var(--dew-font, inherit);
  width: 100%;
  transition:
    background 0.35s var(--dew-bounce),
    border-color 0.35s var(--dew-bounce),
    box-shadow 0.35s var(--dew-bounce);
}

.dew-input:hover:not(.dew-input--disabled):not(.dew-input--focused) {
  background: var(--dew-input-bg-hover);
  border-color: var(--dew-input-border-hover);
}

/* ━━━━ 聚焦态 ━━━━ */
.dew-input--focused:not(.dew-input--disabled) {
  background: var(--dew-input-bg-focus);
  border-color: var(--dew-input-border-focus);
  box-shadow: var(--dew-input-shadow-focus);
}

/* ━━━━ 错误态 ━━━━ */
.dew-input--error:not(.dew-input--disabled) {
  border-color: var(--dew-input-error-border);
  box-shadow: var(--dew-input-error-shadow);
}
.dew-input--error.dew-input--focused:not(.dew-input--disabled) {
  border-color: var(--dew-input-error-border);
  box-shadow: var(--dew-input-error-shadow);
}

/* ━━━━ 禁用态 ━━━━ */
.dew-input--disabled {
  cursor: not-allowed;
  opacity: 0.4;
  backdrop-filter: blur(8px);
}

/* ━━━━ 全圆角 ━━━━ */
.dew-input--round { border-radius: 9999px !important; }
.dew-input--round .dew-input__inner { border-radius: 9999px; }

/* ━━━━ 聚焦展开 ━━━━ */
.dew-input--expand {
  width: var(--dew-input-expand-width);
  transition:
    width 0.5s var(--dew-bounce),
    background 0.35s var(--dew-bounce),
    border-color 0.35s var(--dew-bounce),
    box-shadow 0.35s var(--dew-bounce);
}
.dew-input--expanded {
  width: var(--dew-input-expand-width-focus) !important;
}

/* ━━━━ 尺寸 ━━━━ */
.dew-input--sm { height: 32px; border-radius: 10px; }
.dew-input--sm .dew-input__inner { font-size: 12px; padding: 0 10px; }
.dew-input--sm .dew-input__prefix { left: 10px; }
.dew-input--sm .dew-input__suffix { right: 10px; }
.dew-input--sm .dew-input__icon { width: 14px; height: 14px; }
.dew-input--sm.dew-input--has-prefix .dew-input__inner { padding-left: 30px; }
.dew-input--sm.dew-input--has-suffix .dew-input__inner { padding-right: 30px; }

.dew-input--md { height: 40px; border-radius: 12px; }
.dew-input--md .dew-input__inner { font-size: 14px; padding: 0 12px; }
.dew-input--md .dew-input__prefix { left: 12px; }
.dew-input--md .dew-input__suffix { right: 12px; }
.dew-input--md .dew-input__icon { width: 16px; height: 16px; }
.dew-input--md.dew-input--has-prefix .dew-input__inner { padding-left: 36px; }
.dew-input--md.dew-input--has-suffix .dew-input__inner { padding-right: 36px; }

.dew-input--lg { height: 48px; border-radius: 14px; }
.dew-input--lg .dew-input__inner { font-size: 15px; padding: 0 14px; }
.dew-input--lg .dew-input__prefix { left: 14px; }
.dew-input--lg .dew-input__suffix { right: 14px; }
.dew-input--lg .dew-input__icon { width: 18px; height: 18px; }
.dew-input--lg.dew-input--has-prefix .dew-input__inner { padding-left: 40px; }
.dew-input--lg.dew-input--has-suffix .dew-input__inner { padding-right: 40px; }

/* 后缀区域留白（clearable / password toggle / suffix icon） */
.dew-input--has-clear .dew-input__inner,
.dew-input--has-toggle .dew-input__inner {
  padding-right: 32px;
}
.dew-input--has-clear.dew-input--has-toggle .dew-input__inner {
  padding-right: 56px;
}

/* ━━━━ 折射层 ━━━━ */
.dew-input__refraction {
  position: absolute;
  inset: 0;
  z-index: 1;
  border-radius: inherit;
  mix-blend-mode: overlay;
  pointer-events: none;
}

/* ━━━━ 色散层 ━━━━ */
.dew-input__chromatic {
  position: absolute;
  inset: 0;
  z-index: 1;
  border-radius: inherit;
  pointer-events: none;
  mix-blend-mode: screen;
}

/* ━━━━ 外发光层 ━━━━ */
.dew-input__glow {
  position: absolute;
  inset: -4px;
  z-index: 0;
  border-radius: inherit;
  pointer-events: none;
  background: radial-gradient(ellipse at var(--glow-x, 50%) var(--glow-y, 50%),
    var(--dew-input-glow-color) 0%,
    transparent 70%);
  transition: opacity 0.35s ease;
}

.dew-input--error .dew-input__glow {
  background: radial-gradient(ellipse at var(--glow-x, 50%) var(--glow-y, 50%),
    var(--dew-input-glow-error) 0%,
    transparent 70%);
}

/* ━━━━ 前缀图标 ━━━━ */
.dew-input__prefix {
  position: absolute;
  z-index: 3;
  display: flex;
  align-items: center;
  color: var(--dew-input-placeholder);
  pointer-events: none;
  transition: color 0.35s ease;
}

.dew-input--focused .dew-input__prefix {
  color: var(--dew-input-text);
}

/* ━━━━ 后缀图标 ━━━━ */
.dew-input__suffix {
  position: absolute;
  z-index: 3;
  display: flex;
  align-items: center;
  color: var(--dew-input-placeholder);
  pointer-events: none;
  transition: color 0.35s ease;
}

.dew-input--focused .dew-input__suffix {
  color: var(--dew-input-text);
}

/* ━━━━ 输入框 ━━━━ */
.dew-input__inner {
  position: relative;
  z-index: 3;
  width: 100%;
  height: 100%;
  border: none;
  outline: none;
  background: transparent;
  font-family: inherit;
  font-weight: 500;
  color: var(--dew-input-text);
  caret-color: var(--dew-text);
  transition: color 0.35s ease;
  /* 消除浏览器原生验证样式 */
  box-shadow: none !important;
}

/* 彻底禁止浏览器原生验证气泡和虚线 */
.dew-input__inner:invalid {
  box-shadow: none !important;
  outline: none !important;
}
.dew-input__inner:out-of-range,
.dew-input__inner:valid {
  box-shadow: none !important;
}

.dew-input__inner::placeholder {
  color: var(--dew-input-placeholder);
  transition: color 0.35s ease;
}

.dew-input__inner:focus::placeholder {
  color: var(--dew-input-placeholder);
  opacity: 0.6;
}

/* ━━━━ 清除按钮 ━━━━ */
.dew-input__clear {
  position: absolute;
  right: 8px;
  z-index: 4;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  color: var(--dew-input-placeholder);
  cursor: pointer;
  transition: background 0.2s ease, color 0.2s ease;
}

.dew-input__clear:hover {
  background: var(--dew-input-clear-hover-bg);
  color: var(--dew-input-text);
}

.dew-input--has-toggle .dew-input__clear {
  right: 34px;
}

/* ━━━━ 密码切换 ━━━━ */
.dew-input__toggle {
  position: absolute;
  right: 8px;
  z-index: 4;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border-radius: 6px;
  color: var(--dew-input-placeholder);
  cursor: pointer;
  transition: color 0.2s ease;
}

.dew-input__toggle:hover {
  color: var(--dew-input-text);
}

/* ── 禁用时隐藏所有交互层 ── */
.dew-input--disabled .dew-input__refraction,
.dew-input--disabled .dew-input__chromatic,
.dew-input--disabled .dew-input__glow { opacity: 0 !important; }

/* ━━━━ textarea 模式 ━━━━ */
.dew-input--textarea {
  display: block;
  height: auto;
  align-items: stretch;
}
.dew-input__textarea {
  display: block;
  width: 100%;
  min-height: 80px;
  resize: vertical;
  border: none;
  outline: none;
  background: transparent;
  font-family: inherit;
  font-weight: 500;
  line-height: 1.6;
  color: var(--dew-input-text);
  caret-color: var(--dew-text);
  box-shadow: none !important;
}
.dew-input--sm .dew-input__textarea { font-size: 12px; padding: 8px 10px; }
.dew-input--md .dew-input__textarea { font-size: 14px; padding: 10px 12px; }
.dew-input--lg .dew-input__textarea { font-size: 15px; padding: 12px 14px; }
.dew-input__textarea::placeholder { color: var(--dew-input-placeholder); }
.dew-input__textarea:invalid { box-shadow: none !important; outline: none !important; }
</style>
