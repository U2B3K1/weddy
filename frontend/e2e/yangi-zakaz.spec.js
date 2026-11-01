// «Yangi zakaz» sahifasi: sana → libos → mijoz → saqlandi → zakaz kartasi. Har qadam keng ekranda va telefonda suratga olinadi
// (test-results/yangi-zakaz/*.png), telefonda sahifa gorizontal surilmasligi tekshiriladi.
// zakaz-oqimi.spec.js dan oldin ishlaydi: boshqa sanalar (40–41 kun) va E2E-1 dan boshqa libos — u testga tegmaydi.
import { expect, test } from '@playwright/test'
import { kirish, xatolarniKuzat } from './yordam.js'

const nav = (page) => page.getByRole('navigation', { name: "Bo'limlar" })
const iso = (kun) => { const t = new Date(); t.setDate(t.getDate() + kun); return t.toLocaleDateString('sv-SE') }
const TELEFON = { width: 390, height: 844 }
const KENG = { width: 1280, height: 860 }

async function suratlar(page, nom) {
  await page.waitForLoadState('networkidle')
  // to'liq sahifa suratida Chrome animatsiyali qatlamning eski kadrini oladi — animatsiyalar oxiriga o'tkaziladi
  await page.screenshot({ path: `test-results/yangi-zakaz/${nom}-keng.png`, fullPage: true, animations: 'disabled' })
  await page.setViewportSize(TELEFON)
  await page.waitForTimeout(400)
  await page.screenshot({ path: `test-results/yangi-zakaz/${nom}-telefon.png`, fullPage: true, animations: 'disabled' })
  const [kenglik, ekran] = await page.evaluate(() => [document.documentElement.scrollWidth, window.innerWidth])
  expect(kenglik, `${nom}: telefonda sahifa gorizontal surilmasin`).toBeLessThanOrEqual(ekran)
  await page.setViewportSize(KENG)
}

// Ilovaning o'z tokenlari bilan API so'rovi (smenani tez ochish/yopish uchun)
const apiSorov = (page, usul, yol, tana) => page.evaluate(async ([usul, yol, tana]) => {
  const r = await fetch(`http://127.0.0.1:8001/api${yol}`, {
    method: usul, body: tana ? JSON.stringify(tana) : undefined,
    headers: { 'Content-Type': 'application/json', 'X-Device-Token': localStorage.getItem('weddy.qurilma_token'),
               Authorization: `Bearer ${sessionStorage.getItem('weddy.token')}` },
  })
  return r.json()
}, [usul, yol, tana])

async function kunniBos(page, sana) {
  const kun = page.locator(`.kuz-kun[data-kun="${sana}"]`)
  for (let i = 0; i < 3 && await kun.count() === 0; i++) await page.getByRole('button', { name: 'Keyingi oy' }).click()
  await kun.click()
}

test('yangi zakaz: har qadam ikki kenglikda', async ({ page }) => {
  const xatolar = xatolarniKuzat(page)
  await kirish(page, 'Sotuvchi', '2222')
  // aksessuarga rasm (Katalog → Aksessuarlar → Rasm) — yangi zakazda ko'ylaklar kabi rasmli kartochka bo'lib chiqadi
  await nav(page).getByRole('button', { name: 'Katalog', exact: true }).click()
  await page.getByRole('tab', { name: 'Aksessuarlar' }).click()
  await page.locator('.zakaz-katak', { hasText: 'Fata Klassik' }).click()
  await page.locator('.aks-tafsilot input[type=file]').first().setInputFiles('public/kelinlar/2.jpg')
  await expect(page.getByText('Rasm saqlandi.')).toBeVisible()
  await expect(page.locator('.aks-tafsilot img.aks-rasm')).toBeVisible()
  await suratlar(page, '0-aksessuar-rasm')

  await nav(page).getByRole('button', { name: 'Kassa', exact: true }).click()  // «Yangi zakaz» — Kassa menyusida
  await nav(page).getByRole('button', { name: 'Yangi zakaz', exact: true }).click()
  await suratlar(page, '1-sana-bosh')
  await kunniBos(page, iso(40))
  await kunniBos(page, iso(41))
  await suratlar(page, '1-sana-tanlandi')

  await page.getByRole('button', { name: 'Davom etish — liboslarni tanlash' }).click()
  // oldingi testlar ba'zi liboslarni band qilgan bo'lishi mumkin — E2E-1 dan boshqa birinchi bo'sh libos olinadi
  const libos = page.locator('ul.liboslar li').filter({ hasNotText: 'E2E-1' }).filter({ has: page.getByRole('button', { name: "Qo'shish" }) }).first()
  await expect(libos).toBeVisible()
  await suratlar(page, '2-libos')
  await libos.getByRole('button', { name: "Qo'shish" }).click()
  await expect(page.locator('.varaq-royxat li')).toHaveCount(1)
  // aksessuar: kartochkada «Qo'shish» → soni va hisob, varaqqa ham yoziladi
  const aks = page.locator('.aks-kartalar li').first()
  await aks.getByRole('button', { name: "Qo'shish" }).click()
  await expect(aks.locator('.aks-jami')).toContainText('1 ×')
  await expect(page.locator('.varaq-royxat li')).toHaveCount(2)
  await suratlar(page, '2-libos-tanlandi')

  await page.getByRole('button', { name: 'Davom etish', exact: true }).click()
  await page.getByLabel('Mijoz telefoni').fill('+998 91 555 40 41')
  await page.getByLabel('Mijoz telefoni').blur()
  await page.getByLabel('Yangi mijoz — F.I.O.').fill('Dizayn Kelin')
  await suratlar(page, '3-mijoz')

  await page.getByRole('button', { name: 'Zakazni saqlash' }).click()
  await expect(page.getByRole('heading', { name: /Zakaz #\d+ saqlandi/ })).toBeVisible()
  await suratlar(page, '4-saqlandi')

  // zakaz kartasi: vaqtinchalik bron — muhr hali bosilmagan (bo'sh joy), varaqda mijoz va sanalar
  await page.getByRole('button', { name: 'Zakaz kartasini ochish' }).click()
  await expect(page.locator('.karta-asosiy.varaq')).toContainText('Dizayn Kelin')
  await expect(page.locator('.karta-asosiy .muhr-joy')).toBeVisible()
  await suratlar(page, '5-karta-vaqtinchalik')

  // avans olinganda (bron tasdiqlanganda) bo'sh joy o'rniga muhr shu zahoti bosiladi
  await apiSorov(page, 'POST', '/kassa/smena/ochish/', { boshlangich_qoldiq: 0 })
  let tolandi = 0
  try {
    const tasdiq = page.getByRole('button', { name: /^Bronni tasdiqlash/ })
    if (await tasdiq.isVisible()) await tasdiq.click()  // 0 so'mlik libos tanlangan bo'lsa
    else {
      tolandi = Number((await page.locator('.varaq-qoldiq dd').textContent()).replace(/\D/g, ''))
      await page.getByLabel(/^Summa \(maks/).fill(String(tolandi))
      await page.getByRole('button', { name: 'Qabul qilish', exact: true }).click()
    }
    await expect(page.locator('.karta-asosiy .muhr-karta.muhr-bosildi')).toBeVisible()
    await expect(page.locator('.karta-asosiy .muhr-joy')).toHaveCount(0)
    await suratlar(page, '6-karta-muhr-bosildi')
  } finally {
    await apiSorov(page, 'POST', '/kassa/smena/yopish/', { summa: tolandi, izoh: '' })
  }

  // bekor qilingan zakaz (seed: «Storno Mijoz»): muhr o'rniga kulrang shtamp
  const qidiruv = page.getByRole('searchbox', { name: 'Zakaz qidirish' }).first()
  await qidiruv.fill('Storno Mijoz')
  await qidiruv.press('Enter')
  await page.locator('.zakaz-katak', { hasText: 'Storno Mijoz' }).first().click()
  await expect(page.locator('.karta-asosiy .shtamp')).toHaveText('Bekor qilindi')
  await suratlar(page, '7-karta-bekor')
  expect(xatolar).toEqual([])
})
