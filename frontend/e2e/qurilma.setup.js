// Salon logini (FT-1.1) va qurilmaga ruxsat (FT-22.2). Birinchi qurilma o'zi ishonchli bo'ladi — uning holati boshqa
// testlarga saqlanadi; ikkinchi qurilma «ruxsat kutmoqda» bo'ladi va rahbar PIN bilan ochadi.
import { expect, test } from '@playwright/test'
import { QURILMA_HOLATI, salon, xatolarniKuzat } from './yordam.js'

async function salonKirish(page, login, parol) {
  await page.goto('/#kirish')  // «/» — reklama sahifasi
  await page.getByLabel('Salon logini').fill(login)
  await page.getByLabel('Parol').fill(parol)
  await page.getByRole('button', { name: 'Davom etish' }).click()
}

test('salon logini va qurilmaga rahbar PIN bilan ruxsat', async ({ page, browser }) => {
  const xatolar = xatolarniKuzat(page)
  const s = salon()
  await salonKirish(page, s.login, 'notogri')
  await expect(page.getByRole('alert')).toHaveText("Login yoki parol noto'g'ri.")
  await page.getByLabel('Parol').fill(s.parol)
  await page.getByRole('button', { name: 'Davom etish' }).click()
  await expect(page.getByText('Kim kirmoqda?')).toBeVisible()  // birinchi qurilma
  await page.context().storageState({ path: QURILMA_HOLATI })

  const ikkinchi = await browser.newPage()
  const xatolar2 = xatolarniKuzat(ikkinchi)
  await salonKirish(ikkinchi, s.login, s.parol)
  await expect(ikkinchi.getByText('ruxsat kutmoqda')).toBeVisible()
  await ikkinchi.getByRole('button', { name: 'Rahbar' }).click()
  await ikkinchi.getByLabel('Shaxsiy PIN kodingiz').fill('9999')
  await ikkinchi.getByRole('button', { name: 'Ruxsat berish' }).click()
  await expect(ikkinchi.getByRole('alert')).toHaveText("PIN noto'g'ri.")
  await ikkinchi.getByLabel('Shaxsiy PIN kodingiz').fill('1111')
  await ikkinchi.getByRole('button', { name: 'Ruxsat berish' }).click()
  await expect(ikkinchi.getByText('Kim kirmoqda?')).toBeVisible()
  await ikkinchi.close()
  expect([...xatolar, ...xatolar2]).toEqual([])
})
