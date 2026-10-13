import { existsSync } from 'node:fs'
import { spawn } from 'node:child_process'
import { fileURLToPath } from 'node:url'

const directory = fileURLToPath(new URL('../backend/', import.meta.url))
const python = fileURLToPath(new URL(
  process.platform === 'win32' ? '../backend/.venv/Scripts/python.exe' : '../backend/.venv/bin/python',
  import.meta.url,
))
const commands = {
  dev: ['-m', 'flask', '--app', 'workbench:create_app', 'run', '--host', '127.0.0.1', '--port', '5003'],
  migrate: ['-m', 'flask', '--app', 'workbench:create_app', 'db', 'upgrade'],
  test: ['-m', 'pytest', '-q'],
}
const args = commands[process.argv[2]]
if (!args || !existsSync(python)) {
  console.error('请按 README 创建 backend/.venv 并安装依赖；可用操作为 dev、migrate、test。')
  process.exit(1)
}
const child = spawn(python, args, { cwd: directory, stdio: 'inherit', env: process.env })
child.on('error', (error) => { console.error(error.message); process.exitCode = 1 })
child.on('exit', (code) => { process.exitCode = code ?? 1 })
for (const signal of ['SIGINT', 'SIGTERM']) process.on(signal, () => child.kill(signal))
