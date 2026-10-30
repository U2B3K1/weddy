// E2E bazasini tayyorlaydi (migratsiya) va yangi sinov saloni yaratadi; login e2e/.salon.json ga yoziladi.
import { execFileSync } from 'node:child_process'
import { writeFileSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { E2E_BAZA } from '../playwright.config.js'

const papka = path.dirname(fileURLToPath(import.meta.url))
const backend = path.resolve(papka, '../../backend')
const python = path.join(backend, process.platform === 'win32' ? '.venv/Scripts/python.exe' : '.venv/bin/python')

function bazaniYarat() {
  const bor = execFileSync('docker', ['exec', 'weddy-db-1', 'psql', '-U', 'weddy', '-d', 'postgres', '-tAc',
    "SELECT 1 FROM pg_database WHERE datname='weddy_e2e'"], { encoding: 'utf8' }).trim()
  if (bor !== '1') execFileSync('docker', ['exec', 'weddy-db-1', 'createdb', '-U', 'weddy', 'weddy_e2e'])
}

export default function globalSetup() {
  bazaniYarat()
  const env = { ...process.env, DATABASE_URL: E2E_BAZA, DEBUG: 'True', PYTHONIOENCODING: 'utf-8' }
  execFileSync(python, ['manage.py', 'migrate', '--noinput'], { cwd: backend, env, stdio: 'ignore' })
  const chiqish = execFileSync(python, ['manage.py', 'shell', '-c',
    `exec(open(r'${path.join(papka, 'seed.py')}', encoding='utf-8').read())`], { cwd: backend, env, encoding: 'utf8' })
  const qator = chiqish.split('\n').find((q) => q.startsWith('E2E_SALON='))
  if (!qator) throw new Error(`Seed natijasi topilmadi:\n${chiqish}`)
  writeFileSync(path.join(papka, '.salon.json'), qator.slice('E2E_SALON='.length))
}
