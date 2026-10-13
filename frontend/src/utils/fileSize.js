// 字节数人性化文本 — 工作台附件尺寸展示的共享口径（B/KB/MB/GB，一位小数）。
// 供事项附件区（WorkFileList）与工作资料索引（WorkFilesIndex）共用，
// 替代此前两处手写且口径不一的 sizeText。
export function formatFileSize(n) {
  if (n == null) return ''
  if (n < 1024) return `${n} B`
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`
  if (n < 1024 * 1024 * 1024) return `${(n / 1024 / 1024).toFixed(1)} MB`
  return `${(n / 1024 / 1024 / 1024).toFixed(1)} GB`
}
