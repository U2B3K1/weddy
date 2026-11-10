// E2E yordamchilari: sinov saloni, xodim bilan kirish va sahifadagi xatolarni yig'ish.
import { readFileSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { expect } from '@playwright/test'

const papka = path.dirname(fileURLToPath(import.meta.url))
export const QURILMA_HOLATI = path.join(papka, '.qurilma.json')
export const salon = () => JSON.parse(readFileSync(path.join(papka, '.salon.json'), 'utf8'))

// Brauzer JS xatolari va server 5xx javoblari — test oxirida bo'sh bo'lishi kerak
export function xatolarniKuzat(page) {
  const xatolar = []
  page.on('pageerror', (e) => xatolar.push(`JS: ${e.message}`))
  page.on('console', (m) => { if (m.type() === 'error' && !/Failed to load resource/.test(m.text())) xatolar.push(`console: ${m.text()}`) })
  page.on('response', (r) => { if (r.status() >= 500) xatolar.push(`${r.status()} ${r.request().method()} ${r.url()}`) })
  return xatolar
}

// Qurilma tasdiqlangan (storageState) holatda: xodim kartasi → PIN klaviaturasi
export async function kirish(page, ism, pin) {
  await page.goto('/#kirish')
  await page.getByRole('button', { name: ism, exact: false }).first().click()
  for (const d of pin) await page.locator('.pin-klaviatura').getByRole('button', { name: d, exact: true }).click()
  await page.getByRole('button', { name: 'Kirish' }).click()
  await expect(page.getByRole('navigation', { name: "Bo'limlar" })).toBeVisible()
}

export const bolim = (page, nom) => page.getByRole('navigation', { name: "Bo'limlar" }).getByRole('button', { name: nom, exact: true })

// Asosiy menyudagi bo'limga o'tish. Keng ekranda (≥1200) Kassa, Hisobotlar, Liboslar va Sozlama ichida chap panel shu bo'lim
// ro'yxatiga aylanadi (2026-11-10) — avval «‹ Asosiy»
export async function bolimga(page, nom) {
  const nav = page.getByRole('navigation', { name: "Bo'limlar" })
  const asosiy = nav.getByRole('button', { name: 'Asosiy', exact: true })
  const tugma = nav.getByRole('button', { name: nom, exact: true })
  // kenglik endigina o'zgargan bo'lsa (skrinshotdan keyin) chap panel bir lahzadan so'ng bo'lim ro'yxatiga aylanadi — qayta uriniladi
  for (let i = 0; i < 3; i++) {
    if (await asosiy.isVisible()) await asosiy.click()
    try { await tugma.click({ timeout: 3000 }); return } catch { /* panel almashdi — yana */ }
  }
  await tugma.click()
}
