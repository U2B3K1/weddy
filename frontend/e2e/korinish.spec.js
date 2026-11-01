// Ko'rinish: rahbar sahifalari (dashbord, «Kunlik kassa», «Xodimlar nazorati», «Foyda va zarar») keng ekranda va
// telefon kengligida — gorizontal sahifa skrolli bo'lmasligi kerak (keng jadval faqat o'z qutisida suriladi).
// kassa-topshirish.spec.js dan keyin ishlaydi (alifbo tartibi, workers: 1) — o'sha testning smena va to'lovlari ko'rinadi.
// Skrinshotlar: test-results/korinish/*.png (ko'z bilan tekshirish uchun).
import { expect, test } from '@playwright/test'
import { QURILMA_HOLATI, kirish, xatolarniKuzat } from './yordam.js'

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

// Ilovaning o'z tokenlari bilan API so'rovi (sozlamani tez almashtirish uchun)
const apiSorov = (page, usul, yol, tana) => page.evaluate(async ([usul, yol, tana]) => {
  const r = await fetch(`http://127.0.0.1:8001/api${yol}`, {
    method: usul, body: tana ? JSON.stringify(tana) : undefined,
    headers: { 'Content-Type': 'application/json', 'X-Device-Token': localStorage.getItem('weddy.qurilma_token'),
               Authorization: `Bearer ${sessionStorage.getItem('weddy.token')}` },
  })
  return r.json()
}, [usul, yol, tana])

test('libos sanog\'i: boshlash, skaner, yakun', async ({ page }) => {
  const xatolar = xatolarniKuzat(page)
  await kirish(page, 'Rahbar', '1111')
  await nav(page).getByRole('button', { name: 'Katalog', exact: true }).click()
  await page.getByRole('tab', { name: 'Sanoq', exact: true }).click()
  await page.getByRole('button', { name: 'Sanoqni boshlash' }).click()

  await test.step('artikul skaner qilinadi (Enter), noto\'g\'risi xato beradi', async () => {
    const k = page.getByLabel('Artikul')
    await k.fill('e2e-1')  // katta-kichik harf farqi yo'q
    await k.press('Enter')
    await expect(page.getByText('✓ E2E-1 Libos E2E-1')).toBeVisible()
    await expect(k).toBeFocused()  // skaner keyingi artikulni darhol yozadi
    await k.fill('YOQ-999')
    await k.press('Enter')
    await expect(page.locator('p.xato')).toBeVisible()
    await ikkiKenglik(page, '5-sanoq-ochiq')
  })

  await test.step('yakun: topilmagan libos «yo\'q» bo\'lib chiqadi', async () => {
    await page.getByRole('button', { name: 'Yakunlash' }).click()
    const natija = page.locator('.blok', { hasText: 'Sanoq yakunlandi' })
    await expect(natija).toContainText("Yo'q (1): E2E-2 Libos E2E-2")
    await ikkiKenglik(page, '6-sanoq-natija')
  })
  expect(xatolar).toEqual([])
})

test('kassir rejimi: sotuvchining zakaz kartasida pul formalari yo\'q', async ({ page, browser }) => {
  // kassa-topshirish.spec.js dagi «Naqdsiz Sinov» zakazi: to'liq to'langan bron, smenalar yopiq
  await kirish(page, 'Rahbar', '1111')
  const r = await apiSorov(page, 'PATCH', '/sozlamalar/', { kassa_rejimi: 'kassir' })
  expect(r.kassa_rejimi).toBe('kassir')
  try {
    const ctx = await browser.newContext({ storageState: QURILMA_HOLATI })
    const s = await ctx.newPage()
    const xatolar = xatolarniKuzat(s)
    await kirish(s, 'Sotuvchi', '2222')
    await nav(s).getByRole('button', { name: 'Zakazlar', exact: true }).click()
    await s.locator('input.jadval-qidiruv').fill('Naqdsiz Sinov')
    await s.locator('.zakaz-jadval tbody tr', { hasText: 'Naqdsiz Sinov' }).first().click()
    await expect(s.getByRole('heading', { name: /^Zakaz #\d+$/ })).toBeVisible()
    // berishda faqat hujjat/tillo zalog — pul zalogni kassir oladi
    const berish = s.locator('#asosiy-amal')
    await expect(berish).toContainText('Libosni berish (zalog)')
    await expect(berish.locator('option', { hasText: /^Pul$/ })).toHaveCount(0)
    await expect(s.getByLabel('Zalog summasi')).toHaveCount(0)
    await s.getByText('Boshqa amallar').click()
    await expect(s.getByText("To'lov qilingan zakazni kassir bekor qiladi")).toBeVisible()
    await ikkiKenglik(s, '7-kassir-rejimi-zakaz-karta')
    expect(xatolar).toEqual([])
  } finally {
    await apiSorov(page, 'PATCH', '/sozlamalar/', { kassa_rejimi: 'sotuvchi' })
  }
})
