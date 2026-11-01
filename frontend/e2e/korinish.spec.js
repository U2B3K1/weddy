// Ko'rinish: rahbar sahifalari (dashbord, «Kunlik kassa», «Xodimlar nazorati», «Foyda va zarar») keng ekranda va
// telefon kengligida — gorizontal sahifa skrolli bo'lmasligi kerak (keng jadval faqat o'z qutisida suriladi).
// kassa-topshirish.spec.js dan keyin ishlaydi (alifbo tartibi, workers: 1) — o'sha testning smena va to'lovlari ko'rinadi.
// Skrinshotlar: test-results/korinish/*.png (ko'z bilan tekshirish uchun).
import { expect, test } from '@playwright/test'
import { kirish, xatolarniKuzat } from './yordam.js'

const nav = (page) => page.getByRole('navigation', { name: "Bo'limlar" })
const TELEFON = { width: 390, height: 844 }
const KENG = { width: 1280, height: 860 }

// Ikki kenglikda skrinshot; telefonda sahifa gorizontal surilmasligi tekshiriladi
async function ikkiKenglik(page, nom) {
  await page.waitForLoadState('networkidle')
  await page.screenshot({ path: `test-results/korinish/${nom}-keng.png`, fullPage: true })
  await page.setViewportSize(TELEFON)
  await page.waitForTimeout(200)
  await page.screenshot({ path: `test-results/korinish/${nom}-telefon.png`, fullPage: true })
  const [kenglik, ekran] = await page.evaluate(() => [document.documentElement.scrollWidth, window.innerWidth])
  expect(kenglik, `${nom}: telefonda sahifa gorizontal surilmasin`).toBeLessThanOrEqual(ekran)
  await page.setViewportSize(KENG)
}

test('rahbar sahifalari keng ekranda va telefonda', async ({ page }) => {
  const xatolar = xatolarniKuzat(page)
  await kirish(page, 'Rahbar', '1111')

  await test.step('dashbord', async () => {
    await expect(page.getByRole('region', { name: /^Nazorat/ })).toBeVisible()
    await ikkiKenglik(page, '1-dashbord')
  })

  await nav(page).getByRole('button', { name: 'Hisobot', exact: true }).click()
  for (const [i, nom] of [[2, 'Kunlik kassa'], [3, 'Xodimlar nazorati']]) {
    await test.step(nom, async () => {
      await page.getByLabel('Hisobot turi').selectOption({ label: nom })
      await expect(page.getByRole('heading', { name: nom })).toBeVisible()
      await ikkiKenglik(page, `${i}-${nom.replace(' ', '-').toLowerCase()}`)
    })
  }

  await test.step('Foyda va zarar', async () => {
    await nav(page).getByRole('button', { name: 'Foyda va zarar', exact: true }).click()
    await expect(page.getByText('Kirgan pul (avans va qoldiq)')).toBeVisible()
    await ikkiKenglik(page, '4-foyda-zarar')
  })
  expect(xatolar).toEqual([])
})
