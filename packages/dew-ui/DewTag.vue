<template>
  <span :style="tagStyle">
    <slot />
  </span>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  type: { type: String, default: 'primary' },   // primary | success | warning | danger | info | neutral
  size: { type: String, default: 'md' },         // sm | md
  round: { type: Boolean, default: false },
})

const sizeMap = {
  sm: { height: '22px', paddingH: '8px', fontSize: 'var(--text-xs)' },
  md: { height: '26px', paddingH: '12px', fontSize: 'var(--text-sm)' },
}

const colorMap = {
  primary:  { bg: 'var(--color-primary-light)', color: 'var(--color-primary)' },
  success:  { bg: 'var(--color-success-light)', color: 'var(--color-success)' },
  warning:  { bg: 'var(--color-warning-light)', color: 'var(--color-warning)' },
  danger:   { bg: 'var(--color-danger-light)',  color: 'var(--color-danger)' },
  info:     { bg: 'var(--color-info-light)',    color: 'var(--color-info)' },
  neutral:  { bg: 'var(--color-bg-muted)',      color: 'var(--color-text-secondary)' },
}

const tagStyle = computed(() => {
  const s = sizeMap[props.size]
  const c = colorMap[props.type]
  return {
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontFamily: 'var(--dew-font, inherit)',
    height: s.height,
    padding: `0 ${s.paddingH}`,
    borderRadius: props.round ? 'var(--radius-full)' : 'var(--radius-sm)',
    fontSize: s.fontSize,
    fontWeight: '500',
    lineHeight: '1',
    background: c.bg,
    color: c.color,
    whiteSpace: 'nowrap',
  }
})
</script>
