// Only actual application routes may be restored after a server-side SSO callback.
const key = 'bme-workbench:return-path'
const paths = new Set(['/', '/manage'])
export function safeReturnPath(value) {
  if (typeof value !== 'string' || !value.startsWith('/') || value.startsWith('//') || /[\\\u0000-\u0020]/.test(value)) return '/'
  const url = new URL(value, 'http://workbench.invalid')
  if (!paths.has(url.pathname) && !/^\/work(?:\/(?:items(?:\/[1-9][0-9]*)?|board|members|summary|files|records|governance))?$/.test(url.pathname)) return '/'
  for (const [key, entry] of url.searchParams) {
    if (!(key === 'ws' && /^[0-9]+$/.test(entry)) && !(key === 'tab' && /^(todo|group|board|summary|files|records)$/.test(entry))) return '/'
  }
  return url.pathname + url.search
}

export function rememberReturnPath(value) {
  try { sessionStorage.setItem(key, safeReturnPath(value)) } catch { /* Private browsing can disable storage. */ }
}

export function takeReturnPath() {
  try {
    const value = sessionStorage.getItem(key)
    sessionStorage.removeItem(key)
    return safeReturnPath(value)
  } catch { return '/' }
}
