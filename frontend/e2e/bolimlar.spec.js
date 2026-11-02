// Tutun testi: rahbar va sotuvchi har bir bo'lim va ichki bo'limni ochadi — JS xatosi va 5xx bo'lmasligi kerak.
import { expect, test } from '@playwright/test'
import { GURUHLAR, SOZLAMA_BOLIMLAR } from '../src/pages/sozlamaBolimlari.js'
import { bolim, kirish, xatolarniKuzat } from './yordam.js'

// Chap paneldagi o'z menyusiga ega bo'limlar (App.jsx: kassaRoyxat, HISOBOT_ROYXAT)
const ICHKI = {
  Kassa: ['Yangi zakaz', "To'lov qabul", 'Xarajat', 'Inkassatsiya', 'Zaloglar', 'Smena hisoboti', 'Smenalar tarixi'],
  Hisobot: ['Umumiy hisobot', 'Foyda va zarar', 'Xarajatlar', 'Sotuvchi bonusi', 'Bank solishtirish', 'Grafik'],
}

const nav = (page) => page.getByRole('navigation', { name: "Bo'limlar" })

async function och(page, nomi) {
  await nav(page).getByRole('button', { name: nomi, exact: true }).click()
  await page.waitForLoadState('networkidle')
}

test('rahbar: barcha bo\'limlar va ichki bo\'limlar ochiladi', async ({ page }) => {
  const xatolar = xatolarniKuzat(page)
  await kirish(page, 'Rahbar', '1111')
  for (const nom of ['Dashboard', 'Katalog', 'Zakazlar', 'Mijozlar', 'Kassa', 'Hisobot']) {
    await test.step(nom, async () => {
      await och(page, nom)
      for (const ichki of ICHKI[nom] || []) await test.step(ichki, () => och(page, ichki))
      if (ICHKI[nom]) await och(page, 'Asosiy')
    })
  }
  await test.step('Sozlama', async () => {
    await och(page, 'Sozlama')
    for (const g of GURUHLAR) {
      const guruh = nav(page).getByRole('button', { name: g.nomi })
      if (await guruh.getAttribute('aria-expanded') !== 'true') await guruh.click()  // joriy bo'lim guruhi ochiq turadi
      for (const b of SOZLAMA_BOLIMLAR.filter((x) => x.guruh === g.nomi)) {
        await test.step(b.nomi, () => och(page, b.nomi))
      }
    }
  })
  expect(xatolar).toEqual([])
})

test('sotuvchi: rahbar bo\'limlari ko\'rinmaydi, o\'zinikilari ochiladi', async ({ page }) => {
  const xatolar = xatolarniKuzat(page)
  await kirish(page, 'Sotuvchi', '2222')
  await expect(bolim(page, 'Hisobot')).toHaveCount(0)
  await expect(bolim(page, 'Sozlama')).toHaveCount(0)
  for (const nom of ['Dashboard', 'Katalog', 'Zakazlar', 'Mijozlar']) await och(page, nom)
  await och(page, 'Kassa')
  for (const ichki of ICHKI.Kassa.filter((x) => x !== 'Smenalar tarixi')) await och(page, ichki)
  await expect(nav(page).getByRole('button', { name: 'Smenalar tarixi' })).toHaveCount(0)
  // shapkada ismga bosish — chiqish: PIN ekraniga qaytadi
  await page.getByRole('button', { name: 'Sotuvchi, chiqish' }).click()
  await expect(page.locator('.pin-klaviatura, .kirish').first()).toBeVisible()
  await expect(nav(page)).toHaveCount(0)
  expect(xatolar).toEqual([])
})
