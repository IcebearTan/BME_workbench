// Only actual application routes may be restored after a server-side SSO callback.
const key = 'bme-workbench:return-path'
const paths = new Set(['/', '/manage'])
export const safeReturnPath = (value) => typeof value === 'string' && paths.has(value) ? value : '/'

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
