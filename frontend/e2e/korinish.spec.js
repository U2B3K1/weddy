// Ko'rinish: rahbar sahifalari (dashbord, «Kunlik kassa», «Xodimlar nazorati», «Foyda va zarar») keng ekranda va
// telefon kengligida — gorizontal sahifa skrolli bo'lmasligi kerak (keng jadval faqat o'z qutisida suriladi).
// kassa-topshirish.spec.js dan keyin ishlaydi (alifbo tartibi, workers: 1) — o'sha testning smena va to'lovlari ko'rinadi.
// Skrinshotlar: test-results/korinish/*.png (ko'z bilan tekshirish uchun).
import { expect, test } from '@playwright/test'
import { QURILMA_HOLATI, kirish, xatolarniKuzat } from './yordam.js'

const nav = (page) => page.getByRole('navigation', { name: "Bo'limlar" })
const TELEFON = { width: 390, height: 844 }
const KENG = { width: 1280, height: 860 }
const iso = (kun) => { const t = new Date(); t.setDate(t.getDate() + kun); return t.toLocaleDateString('sv-SE') }

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

  await test.step('Sotuvchi bonusi va Umumiy hisobot', async () => {
    // seed'da bonus o'chiq — jadvalni ko'rish uchun vaqtincha 5% yoqiladi
    await apiSorov(page, 'PATCH', '/sozlamalar/', { sotuvchi_bonusi: true, bonus_foiz: '5' })
    try {
      await nav(page).getByRole('button', { name: 'Sotuvchi bonusi', exact: true }).click()
      await expect(page.getByRole('columnheader', { name: 'Bonus (5%)' })).toBeVisible()
      await ikkiKenglik(page, '4b-sotuvchi-bonusi')
    } finally {
      await apiSorov(page, 'PATCH', '/sozlamalar/', { sotuvchi_bonusi: false, bonus_foiz: '0' })
    }
    await nav(page).getByRole('button', { name: 'Umumiy hisobot', exact: true }).click()
    await ikkiKenglik(page, '4c-umumiy-hisobot')
    // seed: o'tgan oyda to'langan, shu oyda bekor qilingan zakaz — sotuvchi tushumidan ayiriladi
    await page.getByLabel('Hisobot turi').selectOption({ label: 'Sotuvchilar' })
    await page.getByRole('row', { name: /Sotuvchi/ }).getByRole('button', { name: 'Sotuvchi' }).click()
    await expect(page.locator('.tafsilot')).toContainText('Bekor qilindi (storno)')
    await expect(page.locator('.tafsilot')).toContainText("Storno Mijoz")
    await expect(page.locator('.tafsilot')).toContainText("-500 000 so'm")
    await ikkiKenglik(page, '4c-storno')
  })

  await test.step('kirgach manzilda #kirish qolmaydi; ichki bo\'limlar bir joyda', async () => {
    expect(new URL(page.url()).hash).toBe('')
    const segment = page.locator('.ichki-segment')
    await expect(segment).toBeHidden()  // Hisobot bo'limlari chap panelda
    await nav(page).getByRole('button', { name: 'Asosiy' }).click()
    await expect(segment).toBeVisible()  // chap panel asosiy menyuda — bo'limlar tepada qaytadi
    await nav(page).getByRole('button', { name: 'Sozlama', exact: true }).click()
    await expect(page.locator('.sozlama-menu')).toBeHidden()  // Sozlama menyusi chap panelda
    await page.waitForLoadState('networkidle')
    await page.screenshot({ path: 'test-results/korinish/4d-sozlama-keng.png', fullPage: true })
    await nav(page).getByRole('button', { name: 'Asosiy' }).click()
    await expect(page.locator('.sozlama-menu')).toBeVisible()
  })

  await test.step('zakaz kartasi keng ekranda', async () => {
    await nav(page).getByRole('button', { name: 'Zakazlar', exact: true }).click()
    // kassa-topshirish.spec.js dagi zakaz
    await page.locator('.zakaz-jadval tbody tr', { hasText: 'Naqdsiz Sinov' }).first().click()
    await expect(page.getByRole('heading', { name: /^Zakaz #\d+$/ })).toBeVisible()
    await ikkiKenglik(page, '4e-zakaz-kartasi')
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
    await k.fill('ft-01')  // aksessuar donasi — yorlig'i bo'yicha
    await k.press('Enter')
    await expect(page.getByText('✓ FT-01 Fata Klassik')).toBeVisible()
    await k.fill('YOQ-999')
    await k.press('Enter')
    await expect(page.locator('p.xato')).toBeVisible()
    await ikkiKenglik(page, '5-sanoq-ochiq')
  })

  await test.step('yakun: topilmagan libos «yo\'q» bo\'lib chiqadi', async () => {
    await page.getByRole('button', { name: 'Yakunlash' }).click()
    const natija = page.locator('.blok', { hasText: 'Sanoq yakunlandi' })
    await expect(natija).toContainText("Yo'q (2): E2E-2 Libos E2E-2, FT-02 Fata Klassik")
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

test('to\'liq chegirmali (0 so\'m) bron kassada to\'lovsiz tasdiqlanadi', async ({ page }) => {
  const xatolar = xatolarniKuzat(page)
  await kirish(page, 'Rahbar', '1111')
  const libos = (await apiSorov(page, 'GET', '/liboslar/')).find((l) => l.artikul === 'E2E-1')
  const z = await apiSorov(page, 'POST', '/zakazlar/', { telefon: `+99893${String(Date.now()).slice(-7)}`, fio: 'Bepul Kelin',
    dan: iso(60), gacha: iso(62), liboslar: [libos.id] })
  const ch = await apiSorov(page, 'POST', `/zakazlar/${z.id}/chegirma/`, { sabab: 'boshqa', foiz: 100, izoh: 'homiylik' })
  await apiSorov(page, 'POST', `/chegirma-sorovlari/${ch.sorov.id}/qaror/`, { qaror: 'tasdiq' })
  await apiSorov(page, 'POST', '/kassa/smena/ochish/', { boshlangich_qoldiq: 0 })
  try {
    await nav(page).getByRole('button', { name: 'Kassa', exact: true }).click()
    await nav(page).getByRole('button', { name: "To'lov qabul", exact: true }).click()
    await page.locator('.pos-zakaz', { hasText: 'Bepul Kelin' }).click()
    const chek = page.getByRole('region', { name: "To'lov" })
    await expect(chek).toContainText("Jami0 so'm")
    await ikkiKenglik(page, '8-bepul-bron-kassada')
    await chek.getByRole('button', { name: /^Bronni tasdiqlash/ }).click()
    await expect(page.locator('.pos-zakaz', { hasText: 'Bepul Kelin' })).toHaveCount(0)
    expect((await apiSorov(page, 'GET', `/zakazlar/${z.id}/`)).holat).toBe('bron')
  } finally {  // keyingi test (zakaz-oqimi) smenani o'zi ochadi
    await apiSorov(page, 'POST', '/kassa/smena/yopish/', { summa: 0, izoh: '' })
  }
  expect(xatolar).toEqual([])
})

test('rahbar xato yozilgan to\'lovni tuzatadi (Terminal → Naqd)', async ({ page }) => {
  const xatolar = xatolarniKuzat(page)
  await kirish(page, 'Rahbar', '1111')
  const libos = (await apiSorov(page, 'GET', '/liboslar/')).find((l) => l.artikul === 'E2E-2')
  const z = await apiSorov(page, 'POST', '/zakazlar/', { telefon: `+99894${String(Date.now()).slice(-7)}`, fio: 'Tuzatish Sinov',
    dan: iso(70), gacha: iso(72), liboslar: [libos.id] })
  await apiSorov(page, 'POST', '/kassa/smena/ochish/', { boshlangich_qoldiq: 0 })
  try {
    await apiSorov(page, 'POST', '/kassa/tolovlar/', { zakaz: z.id, tur: 'avans', summa: 400_000, usul: 'karta' })
    await nav(page).getByRole('button', { name: 'Zakazlar', exact: true }).click()
    await page.locator('input.jadval-qidiruv').fill('Tuzatish Sinov')
    await page.locator('.zakaz-jadval tbody tr', { hasText: 'Tuzatish Sinov' }).first().click()
    const tolovlar = page.locator('.karta-tolovlar')
    await expect(tolovlar).toContainText("Avans · 400 000 so'm · Terminal")
    await tolovlar.getByText('Tuzatish', { exact: true }).click()
    await tolovlar.getByLabel("To'lov usuli").selectOption('naqd')
    await tolovlar.getByLabel('Sabab').fill('naqd edi, terminal deb yozilgan')
    await ikkiKenglik(page, '9-tolov-tuzatish')
    await tolovlar.getByRole('button', { name: 'Tuzatishni saqlash' }).click()
    await expect(page.getByText("To'lov tuzatildi.")).toBeVisible()
    await expect(tolovlar).toContainText("Avans · 400 000 so'm · Naqd")
  } finally {
    await apiSorov(page, 'POST', '/kassa/smena/yopish/', { summa: 400_000, izoh: '' })
  }
  expect(xatolar).toEqual([])
})

test('yetkazib beruvchi: libos qisman to\'lab olinadi, qarz to\'lanadi', async ({ page }) => {
  const xatolar = xatolarniKuzat(page)
  await kirish(page, 'Rahbar', '1111')
  await nav(page).getByRole('button', { name: 'Katalog', exact: true }).click()
  await page.getByRole('tab', { name: 'Yetkazib beruvchilar' }).click()
  await page.getByText("Yetkazib beruvchi qo'shish").click()
  await page.getByLabel('Nomi').fill('Istanbul Bridal')
  await page.getByRole('button', { name: "Qo'shish", exact: true }).click()
  await expect(page.getByText("Yetkazib beruvchi qo'shildi.")).toBeVisible()

  await test.step('libos qo\'shishda: qayerdan olingan va hozir qancha to\'landi', async () => {
    await page.getByRole('tab', { name: 'Liboslar' }).click()
    await page.getByRole('button', { name: 'Libos qo\'shish' }).click()
    const oyna = page.getByRole('dialog')
    await oyna.getByLabel('Artikul').fill('YB-1')
    await oyna.getByLabel('Nomi').fill('Turk libosi')
    await oyna.getByLabel('Tannarx').fill('10000000')
    await oyna.getByLabel('Qayerdan olingan').selectOption({ label: 'Istanbul Bridal' })
    await oyna.getByLabel("Hozir to'landi").fill('4000000')
    await expect(oyna).toContainText("Yetkazib beruvchiga qarz: 6 000 000 so'm")
    await ikkiKenglik(page, '10-libos-yetkazib-beruvchi')
    await oyna.getByRole('button', { name: "Qo'shish", exact: true }).click()
    await expect(page.getByText("Libos katalogga qo'shildi.")).toBeVisible()
  })

  await test.step('libos artikuli: sozlamada prefiks va avto raqam, formada «i»', async () => {
    try {
      await nav(page).getByRole('button', { name: 'Sozlama', exact: true }).click()
      const guruh = nav(page).getByRole('button', { name: "Ko'rinish va xabarlar" })
      if (await guruh.getAttribute('aria-expanded') !== 'true') await guruh.click()
      await nav(page).getByRole('button', { name: 'Libos artikuli', exact: true }).click()
      await page.getByLabel('Prefiks').fill('E-')
      await page.getByLabel("Raqam avtomatik qo'yilsin").check()
      await page.getByLabel('Sanoq nechidan boshlansin').fill('5')
      await page.getByLabel('Raqam necha xonali').selectOption('3')
      await expect(page.locator('.blok', { hasText: 'Libos artikuli' })).toContainText('Namuna: E-005, E-006, E-007')
      await page.getByRole('button', { name: 'Saqlash', exact: true }).click()
      await expect(page.getByText('Sozlamalar saqlandi.')).toBeVisible()
      await ikkiKenglik(page, '13-artikul-sozlama')

      await nav(page).getByRole('button', { name: 'Asosiy', exact: true }).click()  // Sozlama menyusida ham «Katalog» bo'limi bor
      await nav(page).getByRole('button', { name: 'Katalog', exact: true }).click()
      await page.getByRole('tab', { name: 'Liboslar' }).click()
      await page.getByRole('button', { name: 'Libos qo\'shish' }).click()
      const oyna = page.getByRole('dialog')
      await expect(oyna.getByLabel('Artikul')).toHaveAttribute('placeholder', 'avtomatik: E-005')
      await oyna.getByRole('button', { name: 'Izoh' }).first().click()
      await expect(oyna.getByRole('note')).toContainText("tizim keyingi raqamni o'zi beradi: E-005")
      await page.screenshot({ path: 'test-results/korinish/14-artikul-info.png' })
      await oyna.getByLabel('Nomi').fill('Avto libos')  // artikul bo'sh qoldiriladi
      await expect(oyna.getByRole('note')).toHaveCount(0)  // boshqa joy bosilsa izoh yopiladi
      await oyna.getByRole('button', { name: "Qo'shish", exact: true }).click()
      await expect(page.getByText("Libos katalogga qo'shildi.")).toBeVisible()
      await expect(page.getByText('E-005').first()).toBeVisible()
    } finally {
      await apiSorov(page, 'PATCH', '/sozlamalar/', { artikul_avto: false, artikul_prefiks: '' })
    }
  })

  await test.step('aksessuar ham: 3 dona × 100 000, 100 000 to\'landi', async () => {
    await page.getByRole('tab', { name: 'Aksessuarlar' }).click()
    await page.getByRole('button', { name: "Aksessuar qo'shish" }).click()
    const oyna = page.getByRole('dialog')
    await oyna.getByLabel('Nomi').fill('Toj Oltin')
    await oyna.getByLabel(/^Kod/).fill('TJ')
    await oyna.getByLabel('Dona soni').fill('3')
    await oyna.getByLabel('Tannarx (1 dona)').fill('100000')
    await oyna.getByLabel('Qayerdan olingan').selectOption({ label: 'Istanbul Bridal' })
    await oyna.getByLabel("Hozir to'landi").fill('100000')
    await expect(oyna).toContainText("Yetkazib beruvchiga qarz: 200 000 so'm")
    await oyna.getByRole('button', { name: "Qo'shish", exact: true }).click()
    await expect(page.getByText("Aksessuar qo'shildi.")).toBeVisible()
  })

  await test.step('yangi partiya qimmatroq: 2 dona × 120 000, to\'lanmadi', async () => {
    await page.getByRole('button', { name: /Toj Oltin/ }).click()
    const t = page.locator('.tafsilot-qator')
    await t.getByText("Dona qo'shish", { exact: true }).click()
    await t.getByLabel('Soni').fill('2')
    await t.getByLabel('Bir dona narxi').fill('120000')
    await t.getByLabel('Qayerdan olingan').selectOption({ label: 'Istanbul Bridal' })
    await t.getByLabel("Hozir to'landi").fill('0')
    await expect(t).toContainText("Yetkazib beruvchiga qarz: 240 000 so'm")
    await t.getByRole('button', { name: "Qo'shish", exact: true }).click()
    await expect(page.getByText("Donalar qo'shildi.")).toBeVisible()
    await t.getByText('Partiyalar (2)').click()
    await expect(t).toContainText("3 dona × 100 000 so'm = 300 000 so'm")
    await expect(t).toContainText("2 dona × 120 000 so'm = 240 000 so'm")
    await ikkiKenglik(page, '11-aksessuar-partiyalar')
  })

  await test.step('qarz ko\'rinadi va to\'lanadi', async () => {
    await page.getByRole('tab', { name: 'Yetkazib beruvchilar' }).click()
    const qator = page.locator('.yetkazib-qator', { hasText: 'Istanbul Bridal' })
    await expect(qator).toContainText("qarz 6 440 000 so'm")
    await qator.getByRole('button', { name: /Istanbul Bridal/ }).click()
    await expect(qator).toContainText('YB-1')
    await expect(qator).toContainText("TJ Toj Oltin · 3 dona × 100 000 so'm = 300 000 so'm")
    await expect(qator).toContainText("TJ Toj Oltin · 2 dona × 120 000 so'm = 240 000 so'm")
    await ikkiKenglik(page, '12-yetkazib-qarz')
    await qator.getByLabel("To'lov summasi").fill('6440000')
    await qator.getByRole('button', { name: "To'lov qilish" }).click()
    await expect(qator).toContainText("qarz yo'q")
  })
  expect(xatolar).toEqual([])
})
