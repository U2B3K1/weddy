// Bandlik kalendari: bron — bir necha kunlik bitta tasma, kun sarlavhasida band liboslar soni, kun bosilsa — shu kun varaqasi.
// Sinov zakazi uzoq sanaga (200 kundan keyin) qo'yiladi — boshqa testlarning libos va sanalariga tegmaydi.
import { expect, test } from '@playwright/test'
import { kirish, xatolarniKuzat } from './yordam.js'

const nav = (page) => page.getByRole('navigation', { name: "Bo'limlar" })
const iso = (kun) => { const t = new Date(); t.setDate(t.getDate() + kun); return t.toLocaleDateString('sv-SE') }
const TELEFON = { width: 390, height: 844 }
const KENG = { width: 1280, height: 860 }
const apiSorov = (page, usul, yol, tana) => page.evaluate(async ([usul, yol, tana]) => {
  const r = await fetch(`http://127.0.0.1:8001/api${yol}`, {
    method: usul, body: tana ? JSON.stringify(tana) : undefined,
    headers: { 'Content-Type': 'application/json', 'X-Device-Token': localStorage.getItem('weddy.qurilma_token'),
               Authorization: `Bearer ${sessionStorage.getItem('weddy.token')}` },
  })
  return r.json()
}, [usul, yol, tana])

async function suratlar(page, nom) {
  await page.waitForLoadState('networkidle')
  await page.screenshot({ path: `test-results/kalendar/${nom}-keng.png`, fullPage: true, animations: 'disabled' })
  await page.setViewportSize(TELEFON)
  await page.waitForTimeout(400)
  await page.screenshot({ path: `test-results/kalendar/${nom}-telefon.png`, fullPage: true, animations: 'disabled' })
  const [kenglik, ekran] = await page.evaluate(() => [document.documentElement.scrollWidth, window.innerWidth])
  expect(kenglik, `${nom}: telefonda sahifa gorizontal surilmasin`).toBeLessThanOrEqual(ekran)
  await page.setViewportSize(KENG)
}

test('bandlik kalendari: bron tasmasi, kun soni va kun varaqasi', async ({ page }) => {
  const xatolar = xatolarniKuzat(page)
  await page.setViewportSize(KENG)
  await kirish(page, 'Rahbar', '1111')
  const [dan, gacha] = [iso(200), iso(202)]
  const bosh = (await apiSorov(page, 'GET', `/bronlar/bosh/?dan=${dan}&gacha=${gacha}`)).filter((l) => !l.band && !l.qulflangan)
  const libos = bosh[0]
  const z = await apiSorov(page, 'POST', '/zakazlar/', { telefon: '+998907770033', fio: 'Kalendar Sinov', dan, gacha, liboslar: [libos.id] })
  expect(z.raqam, JSON.stringify(z)).toBeTruthy()

  await nav(page).getByRole('button', { name: 'Zakazlar', exact: true }).click()
  await page.getByRole('tab', { name: 'Bandlik kalendari' }).click()
  await expect(page.getByRole('heading', { name: 'Bandlik' })).toBeVisible()
  await page.getByLabel('Davr boshi').fill(iso(199))

  // uch kunlik bron — bitta tasma (3 ustunni egallaydi), vaqtinchalik
  const tasma = page.locator('.bron-tasma', { hasText: `#${z.raqam} Kalendar Sinov` })
  await expect(tasma).toBeVisible()
  await expect(tasma).toHaveClass(/k-vaqtinchalik/)
  await expect(tasma.locator('..')).toHaveAttribute('colspan', '3')
  // kun sarlavhasida — shu kuni band liboslar soni
  const kun = page.locator('.kun-bosh').nth(1)
  await expect(kun).toHaveAttribute('aria-label', /1 libos band$/)

  await kun.click()
  const varaq = page.getByRole('region', { name: /kuni$/ })
  await expect(varaq.locator('.kun-olib')).toContainText('Kalendar Sinov')
  await expect(varaq.locator('.kun-olib')).toContainText(libos.artikul)
  await suratlar(page, '1-hafta-kun-varaq')

  // kun varaqasidan zakaz kartasi ochiladi, orqaga — yana bandlikka
  await varaq.getByRole('button', { name: /Kalendar Sinov/ }).click()
  await expect(page.getByText(`#${z.raqam}`).first()).toBeVisible()
  await expect(page.locator('.bandlik')).toHaveCount(0)
  await page.getByRole('button', { name: "Zakazlar ro'yxatiga qaytish" }).click()
  await expect(page.locator('.bandlik')).toBeVisible()

  await page.getByRole('tab', { name: 'Oy', exact: true }).click()
  await expect(page.locator('.bandlik thead th')).toHaveCount(32)
  await page.getByLabel('Davr boshi').fill(iso(199))
  await expect(tasma).toBeVisible()
  await suratlar(page, '2-oy')

  // erkin davr: «gacha» sanasi davr uzunligini o'zgartiradi — tayyor tablardan hech biri tanlanmagan bo'ladi
  await page.getByLabel('Davr oxiri').fill(iso(208))
  await expect(page.locator('.bandlik thead th')).toHaveCount(11)
  await expect(page.locator('.tezkor-tablar [aria-selected="true"]')).toHaveCount(0)
  await expect(page.locator('.davr-nomi')).toContainText('–')

  await page.getByRole('tab', { name: 'Kun', exact: true }).click()
  await page.getByLabel('Davr boshi').fill(dan)
  await expect(varaq.locator('.kun-olib')).toContainText('Kalendar Sinov')  // «Kun» ko'rinishida varaq doim ochiq
  await page.getByLabel('Libos qidirish').fill('yoqlibos')
  await expect(page.getByText("«yoqlibos» bo'yicha libos topilmadi.")).toBeVisible()
  expect(xatolar).toEqual([])
})
