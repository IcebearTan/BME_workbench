// 把共享样式资产复制到调用方 app 的 public/。
// TinyMCE iframe（content_css）与 md-editor-v3 本地高亮（md-ext）在运行时
// 通过 URL 加载这些文件，因此每个 app 的 public/ 必须有一份副本；
// 由各 app 的 predev/prebuild 自动执行，替代原 sync-richtext.js 跨仓手工同步。
//
// 用法（在 app 目录下）：node ../../packages/styles/copy-to-public.mjs
import { copyFileSync, mkdirSync, readdirSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const pkgDir = dirname(fileURLToPath(import.meta.url))
const appPublic = join(process.cwd(), 'public')

mkdirSync(appPublic, { recursive: true })
copyFileSync(join(pkgDir, 'article-content.css'), join(appPublic, 'article-content.css'))

function copyDirectory(source, target) {
  mkdirSync(target, { recursive: true })
  for (const entry of readdirSync(source, { withFileTypes: true })) {
    const sourcePath = join(source, entry.name)
    const targetPath = join(target, entry.name)
    if (entry.isDirectory()) copyDirectory(sourcePath, targetPath)
    else if (entry.isFile()) copyFileSync(sourcePath, targetPath)
  }
}

// Node 24 的 cpSync 在部分 Windows 中文路径上会无异常信息直接退出，逐文件复制更稳定。
copyDirectory(join(pkgDir, 'public'), appPublic)
console.log('[copy-shared-assets] article-content.css + public/ ->', appPublic)
