export function assetUrl(value) {
  if (!value) return ''
  if (/^https?:\/\//i.test(value)) return value
  return (import.meta.env.VITE_TRAINING_URL || '') + '/' + value.replace(/^\//, '')
}
