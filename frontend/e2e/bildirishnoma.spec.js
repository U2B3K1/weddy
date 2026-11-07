// R2: sotuvchi qo'ng'iroqchasi — rahbar chegirmani tasdiqlasa, so'ragan sotuvchi bildirishnomani ko'radi, bosilsa zakaz
// kartasi ochiladi va shu natija qayta chiqmaydi (qurilmada «ko'rildi»). Ma'lumot API orqali, uzoq sanada — boshqa testlarga tegmaydi.
import { expect, test } from '@playwright/test'
import { QURILMA_HOLATI, kirish, xatolarniKuzat } from './yordam.js'

const iso = (kun) => { const t = new Date(); t.setDate(t.getDate() + kun); return t.toLocaleDateString('sv-SE') }
const apiSorov = (page, usul, yol, tana) => page.evaluate(async ([usul, yol, tana]) => {
  const r = await fetch(`http://127.0.0.1:8001/api${yol}`, {
    method: usul, body: tana ? JSON.stringify(tana) : undefined,
    headers: { 'Content-Type': 'application/json', 'X-Device-Token': localStorage.getItem('weddy.qurilma_token'),
               Authorization: `Bearer ${sessionStorage.getItem('weddy.token')}` },
  })
  return r.json()
}, [usul, yol, tana])

test("sotuvchi qo'ng'iroqchasi: chegirma natijasi zakaz kartasiga olib boradi", async ({ page, browser }) => {
  const xatolar = xatolarniKuzat(page)
  await page.setViewportSize({ width: 1280, height: 860 })
  await kirish(page, 'Sotuvchi', '2222')
  const [dan, gacha] = [iso(240), iso(241)]
  const libos = (await apiSorov(page, 'GET', `/bronlar/bosh/?dan=${dan}&gacha=${gacha}`)).find((l) => !l.band && !l.qulflangan)
  const z = await apiSorov(page, 'POST', '/zakazlar/', { telefon: '+998907770066', fio: "Qo'ng'iroq Sinov", dan, gacha, liboslar: [libos.id] })
  expect(z.raqam, JSON.stringify(z)).toBeTruthy()
  const s = await apiSorov(page, 'POST', `/zakazlar/${z.id}/chegirma/`, { summa: 100_000, sabab: 'doimiy_mijoz' })
  expect(s.sorov?.id, JSON.stringify(s)).toBeTruthy()

  const ctx = await browser.newContext({ storageState: QURILMA_HOLATI })
  try {
    const rahbar = await ctx.newPage()
    await kirish(rahbar, 'Rahbar', '1111')
    const q = await apiSorov(rahbar, 'POST', `/chegirma-sorovlari/${s.sorov.id}/qaror/`, { qaror: 'tasdiq' })
    expect(q.holat, JSON.stringify(q)).toBe('tasdiqlandi')
  } finally {
    await ctx.close()
  }

  try {
    await page.reload()  // qo'ng'iroqcha 2 daqiqada yangilanadi — sinovda darhol
    const tugma = page.getByRole('button', { name: /^Bildirishnomalar/ })
    await expect(tugma).toHaveAccessibleName(/Bildirishnomalar: [1-9]/)
    await tugma.click()
    const band = page.getByRole('menuitem', { name: new RegExp(`#${z.raqam} Qo'ng'iroq Sinov — chegirma tasdiqlandi: 100 000 so'm`) })
    await expect(band).toBeVisible()
    await page.screenshot({ path: 'test-results/bildirishnoma/1-sotuvchi-qongiroqcha.png' })
    await band.click()
    await expect(page.getByRole('heading', { name: `Zakaz #${z.raqam}` })).toBeVisible()
    // ochilgan natija qayta chiqmaydi (shu qurilmada)
    await tugma.click()
    await expect(page.getByRole('menu')).toBeVisible()
    await expect(page.getByRole('menuitem', { name: new RegExp(`#${z.raqam} `) })).toHaveCount(0)
    await page.keyboard.press('Escape')
  } finally {
    await apiSorov(page, 'POST', `/zakazlar/${z.id}/bekor/`, { sabab: 'E2E sinov' })  // libos bo'shaydi
  }
  expect(xatolar).toEqual([])
})
