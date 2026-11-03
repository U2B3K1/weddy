// Telefon (390px): «+» va «Kassa» har xil ekran; «Ko'proq» menyusi yuqori panel ustida; shapkadagi belgi — menyu
// (profil rasmi va «Chiqish»).
import { expect, test } from '@playwright/test'
import { kirish, xatolarniKuzat } from './yordam.js'

test('telefon: pastki panel, chap menyu va xodim menyusi', async ({ page }) => {
  const xatolar = xatolarniKuzat(page)
  await page.setViewportSize({ width: 390, height: 844 })
  await kirish(page, 'Rahbar', '1111')
  const tab = page.getByRole('navigation', { name: "Asosiy bo'limlar" })

  await test.step("«+» — yangi zakaz, «Kassa» — to'lov qabul", async () => {
    await tab.getByRole('button', { name: 'Yangi zakaz' }).click()
    await expect(page.getByRole('tab', { name: 'Yangi zakaz', selected: true })).toBeVisible()
    await tab.getByRole('button', { name: 'Kassa' }).click()
    await expect(page.getByRole('tab', { name: "To'lov qabul", selected: true })).toBeVisible()
    await expect(tab.getByRole('button', { name: 'Kassa' })).toHaveClass(/faol/)
  })

  await test.step("«Ko'proq» menyusi yuqori panel ustida", async () => {
    await tab.getByRole('button', { name: "Ko'proq" }).click()
    await expect(page.locator('nav.pastki.ochiq')).toBeInViewport()
    await page.waitForTimeout(400)  // chiqish animatsiyasi
    // yuqori panel (sahifa nomi) turgan nuqtada eng ustida — chap menyu
    const ustida = await page.evaluate(() => {
      const b = document.querySelector('.ustki').getBoundingClientRect()
      return !!document.elementFromPoint(b.left + 40, b.top + b.height / 2)?.closest('nav.pastki')
    })
    expect(ustida, 'chap menyu yuqori panel ostida qolmasin').toBe(true)
    await page.screenshot({ path: 'test-results/mobil/koproq.png' })
    await page.locator('.menyu-parda').click({ position: { x: 370, y: 400 } })
  })

  await test.step('shapkadagi belgi — profil rasmi va «Chiqish» menyusi', async () => {
    await page.getByRole('button', { name: 'Rahbar: profil va chiqish' }).click()
    const menyu = page.getByRole('menu')
    await expect(menyu.getByRole('menuitem', { name: 'Profil rasmini yuklash' })).toBeVisible()
    await menyu.getByRole('menuitem', { name: 'Chiqish' }).click({ trial: true, timeout: 5000 })
    await page.screenshot({ path: 'test-results/mobil/xodim-menyu.png' })
    await menyu.locator('input[type=file]').setInputFiles('public/kelinlar/2.jpg')
    await expect(page.locator('.shapka-xodim img')).toBeVisible()
    await page.getByRole('button', { name: 'Rahbar: profil va chiqish' }).click()
    await page.getByRole('menu').getByRole('menuitem', { name: 'Rasmni olib tashlash' }).click()
    await expect(page.locator('.shapka-xodim img')).toHaveCount(0)
  })
  expect(xatolar).toEqual([])
})
