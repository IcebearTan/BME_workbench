<template>
  <span :style="badgeStyle">
    <slot />
  </span>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  value: { type: [Number, String], default: null },
  type: { type: String, default: 'primary' },  // primary | success | warning | danger | info | neutral
})

const colorMap = {
  primary:  { bg: 'var(--color-primary-light)', color: 'var(--color-primary)' },
  success:  { bg: 'var(--color-success-light)', color: 'var(--color-success)' },
  warning:  { bg: 'var(--color-warning-light)', color: 'var(--color-warning)' },
  danger:   { bg: 'var(--color-danger-light)',  color: 'var(--color-danger)' },
  info:     { bg: 'var(--color-info-light)',    color: 'var(--color-info)' },
  neutral:  { bg: 'var(--color-bg-muted)',      color: 'var(--color-text-secondary)' },
}

const badgeStyle = computed(() => {
  const c = colorMap[props.type]
  return {
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontFamily: 'var(--dew-font, inherit)',
    minWidth: props.value !== null ? '20px' : 'auto',
    height: '20px',
    padding: '0 6px',
    borderRadius: 'var(--radius-full)',
    fontSize: 'var(--text-xs)',
    fontWeight: '600',
    lineHeight: '1',
    background: c.bg,
    color: c.color,
    whiteSpace: 'nowrap',
  }
})
</script>
