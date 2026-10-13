/**
 * md-editor-v3 自托管配置（禁外网 CDN 红线）。
 * side-effect 模块：编辑器(ArticleEditorV2)与阅读页(ArticleDetailComponentV2)各自 `import './md-setup'` 即生效。
 * config 幂等，多次 import 无副作用。
 *
 * md-editor-v3 v6 默认从 unpkg 拉 highlight.js / prettier / cropper / screenfull / mermaid / katex。
 * 这里把 highlight.js 本地化到 public/md-ext/（源自 @highlightjs/cdn-assets@11.11.1）。
 * prettier 由各组件用 noPrettier 关闭；mermaid/katex 等从工具栏排除——均不走外网。
 */
import { config } from 'md-editor-v3'

const BASE = import.meta.env.BASE_URL // '/AMEII/'

config({
  editorExtensions: {
    highlight: {
      js: `${BASE}md-ext/highlight.min.js`,
      css: {
        atom: {
          light: `${BASE}md-ext/atom-one-light.min.css`,
          dark: `${BASE}md-ext/atom-one-dark.min.css`,
        },
      },
    },
  },
})
