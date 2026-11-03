// Rahbar kirishi: kod terish o'rniga Telegramdagi «Ruxsat berish» — ilova kutadi va ruxsat kelgach o'zi kiradi.
// E2E muhitida bot yo'q: birinchi javob («Telegram kerak») soxtalashtiriladi, kutish so'rovlari haqiqiy backendga boradi
// (u yerda Telegram sozlanmagan — PIN to'g'ri bo'lsa token qaytadi, ya'ni «ruxsat berildi» holati).
import { expect, test } from '@playwright/test'
import { xatolarniKuzat } from './yordam.js'

test("rahbar kirishi: Telegramda «Ruxsat berish»ni kutib, o'zi kiradi", async ({ page }) => {
  const xatolar = xatolarniKuzat(page)
  let birinchi = true
  await page.route('**/api/auth/pin-login/', async (route) => {
    const tana = route.request().postDataJSON()
    if (birinchi && !tana.telegram_kutish) {
      birinchi = false
      return route.fulfill({ status: 202, contentType: 'application/json', body: JSON.stringify({ telegram_kod_kerak: true }) })
    }
    return route.continue()
  })
  await page.goto('/#kirish')
  await page.getByRole('button', { name: 'Rahbar' }).first().click()
  for (const d of '1111') await page.locator('.pin-klaviatura').getByRole('button', { name: d, exact: true }).click()
  await page.getByRole('button', { name: 'Kirish' }).click()

  // kutish ekrani: tugmani bosish so'raladi, kod — yig'ilgan zaxira
  await expect(page.getByText('Telegramda ruxsat bering')).toBeVisible()
  await expect(page.getByRole('status')).toContainText('Ruxsat kutilmoqda')
  await expect(page.getByLabel('Xabardagi 6 raqamli kod')).toBeHidden()
  await page.screenshot({ path: 'test-results/kirish/telegram-kutish.png', animations: 'disabled' })
  // «ruxsat berildi» — keyingi kutish so'rovida token keladi, ilova o'zi ochiladi
  await expect(page.getByRole('navigation', { name: "Bo'limlar" })).toBeVisible({ timeout: 10_000 })
  expect(xatolar).toEqual([])
})
