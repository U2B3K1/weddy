// Asosiy ish kuni: smena → yangi zakaz → to'liq to'lov → libos berish (pul zalog) → qaytarish → smenani yopish.
// Kassadagi naqd oxirida aniq: 1 000 000 (ijara) + 500 000 (zalog) − 500 000 (zalog qaytdi) = 1 000 000.
import { expect, test } from '@playwright/test'
import { kirish, xatolarniKuzat } from './yordam.js'

const nav = (page) => page.getByRole('navigation', { name: "Bo'limlar" })
const iso = (kun) => { const t = new Date(); t.setDate(t.getDate() + kun); return t.toLocaleDateString('sv-SE') }

async function summaTer(joy, raqamlar) {
  const k = joy.getByRole('group', { name: 'Raqamli klaviatura' })
  for (const r of raqamlar) await k.getByRole('button', { name: r, exact: true }).click()
}

async function kunniBos(page, sana) {
  const kun = page.locator(`.kuz-kun[data-kun="${sana}"]`)
  for (let i = 0; i < 3 && await kun.count() === 0; i++) await page.getByRole('button', { name: 'Keyingi oy' }).click()
  await kun.click()
}

test('sotuvchi: zakazdan smena yopilishigacha', async ({ page }) => {
  const xatolar = xatolarniKuzat(page)
  const telefon = `+998 90 ${String(Date.now()).slice(-7, -4)} ${String(Date.now()).slice(-4, -2)} ${String(Date.now()).slice(-2)}`
  await kirish(page, 'Sotuvchi', '2222')

  await test.step('smenani ochish (0 so\'m)', async () => {
    await nav(page).getByRole('button', { name: 'Kassa', exact: true }).click()
    // smena yopiq: «Smenani ochish» bitta (To'lov qabulda — «Smena yopiq» varaqasida, varaq yo'q bo'limda — panelda)
    await page.getByRole('button', { name: 'Smenani ochish' }).click()
    const oyna = page.getByRole('dialog', { name: 'Smenani ochish' })
    await summaTer(oyna, ['0'])
    // C-11: oldingi testlar seyfda pul qoldirgan bo'lsa — farq jonli ko'rinadi va sababi so'raladi
    const izoh = oyna.getByLabel('Izoh (farq sababi — majburiy)')
    if (await izoh.count()) {
      await expect(oyna.getByRole('button', { name: 'Smenani ochish' })).toBeDisabled()
      await izoh.fill("E2E: seyfdagi pul oldingi testdan qolgan")
    }
    await oyna.getByRole('button', { name: 'Smenani ochish' }).click()
    await expect(page.getByText('Smena ochildi.')).toBeVisible()
  })

  let raqam
  await test.step('yangi zakaz: sana → libos → mijoz', async () => {
    await nav(page).getByRole('button', { name: 'Yangi zakaz', exact: true }).click()
    await kunniBos(page, iso(20))
    await kunniBos(page, iso(22))
    await page.getByRole('button', { name: 'Davom etish — liboslarni tanlash' }).click()
    await page.locator('ul.liboslar li', { hasText: 'E2E-1' }).getByRole('button', { name: "Qo'shish" }).click()
    await expect(page.locator('.zakaz-jami .varaq-jami')).toContainText("1 000 000 so'm")
    await page.getByRole('button', { name: 'Davom etish', exact: true }).click()
    await page.getByLabel('Mijoz telefoni').fill(telefon)
    await page.getByLabel('Mijoz telefoni').blur()
    // yangi mijoz ismsiz saqlanmaydi
    await expect(page.getByRole('button', { name: 'Zakazni saqlash' })).toBeDisabled()
    await page.getByLabel('Yangi mijoz — F.I.O.').fill('Sinov Kelin')
    await page.getByRole('button', { name: 'Zakazni saqlash' }).click()
    const sarlavha = page.getByRole('heading', { name: /Zakaz #\d+ saqlandi/ })
    await expect(sarlavha).toBeVisible()
    raqam = (await sarlavha.textContent()).match(/#(\d+)/)[1]
  })

  await test.step('to\'liq to\'lov (avans = jami)', async () => {
    await page.getByRole('button', { name: 'Avans qabul qilish' }).click()
    const chek = page.getByRole('region', { name: "To'lov" })
    await expect(chek).toContainText(`#${raqam}`)
    await chek.getByRole('button', { name: /^To'liq:/ }).click()
    await chek.getByRole('button', { name: "Qabul qilish · 1 000 000 so'm" }).click()
    await expect(chek.getByText("To'lov qabul qilindi")).toBeVisible()
  })

  await test.step('libosni berish: pul zalog, muddatidan oldin — tasdiq bilan', async () => {
    await page.getByRole('searchbox', { name: 'Zakaz qidirish' }).first().fill(raqam)
    await page.getByRole('searchbox', { name: 'Zakaz qidirish' }).first().press('Enter')
    await page.locator('.zakaz-katak', { hasText: `#${raqam}` }).click()
    await expect(page.getByRole('heading', { name: `Zakaz #${raqam}` })).toBeVisible()
    await page.getByLabel('Zalog summasi').fill('500000')
    await page.getByRole('button', { name: 'Zalogni qabul qilib berish' }).click()
    await page.getByRole('alertdialog', { name: 'Libos oldinroq beriladimi?' }).getByRole('button', { name: 'Ha, hozir berish' }).click()
    await expect(page.getByText('Libos berildi.')).toBeVisible()
  })

  await test.step('qaytarish: butun, jarimasiz', async () => {
    await page.getByRole('button', { name: 'Qaytarishni rasmiylashtirish' }).click()
    await expect(page.getByText('Qaytarish rasmiylashtirildi.')).toBeVisible()
    await expect(page.locator('.karta-bosh .holat')).not.toHaveText(/Berildi/)
  })

  await test.step('smena hisoboti va yopish — farq 0', async () => {
    await nav(page).getByRole('button', { name: 'Kassa', exact: true }).click()
    await expect(page.locator('.smena-naqd')).toContainText("1 000 000 so'm")
    await page.locator('.smena-panel').getByRole('button', { name: 'Smenani yopish' }).click()
    const oyna = page.getByRole('dialog', { name: 'Smenani yopish' })
    await summaTer(oyna, ['1', '000', '000'])
    await expect(oyna).toContainText("Farq yo'q")
    await oyna.getByRole('button', { name: 'Smenani yopish' }).click()
    await page.getByRole('alertdialog', { name: 'Smenani yopasizmi?' }).getByRole('button', { name: 'Smenani yopish' }).click()
    await expect(page.getByText("Smena yopildi. Farq: 0 so'm")).toBeVisible()
  })
  expect(xatolar).toEqual([])
})
