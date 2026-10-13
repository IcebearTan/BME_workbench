import { existsSync, readdirSync, readFileSync } from 'node:fs'
import { extname, join, relative } from 'node:path'

const roots = ['frontend/src', 'packages', 'backend/workbench']
const extensions = new Set(['.css', '.html', '.js', '.mjs', '.scss', '.ts', '.vue', '.py'])
const forbidden = /\p{Emoji_Presentation}|\uFE0F/u
const violations = []

function scan(directory) {
  if (!existsSync(directory)) return
  for (const entry of readdirSync(directory, { withFileTypes: true })) {
    if (['node_modules', '__pycache__', '.venv'].includes(entry.name)) continue
    const path = join(directory, entry.name)
    if (entry.isDirectory()) scan(path)
    else if (entry.isFile() && extensions.has(extname(path))) {
      readFileSync(path, 'utf8').split(/\r?\n/).forEach((line, i) => {
        if (forbidden.test(line)) violations.push(`${relative(process.cwd(), path)}:${i + 1}`)
      })
    }
  }
}

roots.forEach(scan)
if (violations.length) {
  console.error('请使用项目图标库或 SVG，移除以下源码中的 emoji：')
  violations.forEach((line) => console.error(line))
  process.exitCode = 1
} else {
  console.log('[check:no-emoji] PASS')
}
