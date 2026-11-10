// Ko'rinish: rahbar sahifalari (dashbord, «Kunlik kassa», «Xodimlar nazorati», «Oylik foyda») keng ekranda va
// telefon kengligida — gorizontal sahifa skrolli bo'lmasligi kerak (keng jadval faqat o'z qutisida suriladi).
// kassa-topshirish.spec.js dan keyin ishlaydi (alifbo tartibi, workers: 1) — o'sha testning smena va to'lovlari ko'rinadi.
// Skrinshotlar: test-results/korinish/*.png (ko'z bilan tekshirish uchun).
import { expect, test } from '@playwright/test'
import { bolimga, QURILMA_HOLATI, kirish, xatolarniKuzat } from './yordam.js'

const nav = (page) => page.getByRole('navigation', { name: "Bo'limlar" })
// Sozlama ochiq bo'lsa keng ekranda chap panel Sozlama ro'yxatiga aylanadi (2026-11-10) — boshqa bo'limga «‹ Asosiy» orqali
const asosiyga = async (page) => {
  const asosiy = nav(page).getByRole('button', { name: 'Asosiy', exact: true })
  if (await asosiy.isVisible()) await asosiy.click()
}
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
    await expect(page.getByRole('region', { name: 'Egasining savollari' })).toBeVisible()
    await ikkiKenglik(page, '1-dashbord')
  })

  await bolimga(page, 'Hisobotlar')
  for (const [i, nom] of [[2, 'Kunlik kassa'], [3, 'Xodimlar nazorati']]) {
    await test.step(nom, async () => {
      await page.getByLabel('Hisobot turi').selectOption({ label: nom })
      await expect(page.getByRole('region', { name: nom })).toBeVisible()  // sarlavha — hisobot tanlovining o'zi
      await ikkiKenglik(page, `${i}-${nom.replace(' ', '-').toLowerCase()}`)
    })
  }

  await test.step('Oylik foyda', async () => {
    await page.getByRole('tab', { name: 'Oylik foyda', exact: true }).click()
    // kanvas (FoydaShisha): «Qayerdan keldi, qayerga ketdi» — kirdi va chiqdi guruhlari, sharshara grafigi
    await expect(page.getByRole('region', { name: 'Qayerdan keldi, qayerga ketdi' }).getByRole('button', { name: 'Avans va qoldiq' })).toBeVisible()
    await expect(page.getByRole('region', { name: "Foyda qanday hosil bo'ldi" })).toBeVisible()
    // tepada 3 ko'rsatkich: kirgan, chiqqan, sof foyda (o'tgan oyning shu kunigacha bilan taqqoslanadi)
    const kpi = page.getByRole('region', { name: "Oylik foyda ko'rsatkichlari" })
    await expect(kpi.locator('.dash-kpi-karta')).toHaveCount(3)
    await expect(kpi.locator('.dash-kpi-karta').first()).toContainText('Kirgan pul')
    await ikkiKenglik(page, '4-foyda-zarar')
  })

  await test.step('Sotuvchi bonusi va Umumiy hisobot', async () => {
    // seed'da bonus o'chiq — jadvalni ko'rish uchun vaqtincha 5% yoqiladi
    await apiSorov(page, 'PATCH', '/sozlamalar/', { sotuvchi_bonusi: true, bonus_foiz: '5' })
    try {
      await page.getByRole('tab', { name: 'Sotuvchi bonusi', exact: true }).click()
      await expect(page.getByRole('region', { name: "Bonus ko'rsatkichlari" })).toContainText('5%')  // kanvas: stavka — ko'rsatkich kartasida
      await expect(page.getByRole('columnheader', { name: 'Stavka' })).toBeVisible()
      await ikkiKenglik(page, '4b-sotuvchi-bonusi')
    } finally {
      await apiSorov(page, 'PATCH', '/sozlamalar/', { sotuvchi_bonusi: false, bonus_foiz: '0' })
    }
    await page.getByRole('tab', { name: 'Umumiy hisobot', exact: true }).click()
    await ikkiKenglik(page, '4c-umumiy-hisobot')
    // seed: o'tgan oyda to'langan, shu oyda bekor qilingan zakaz — sotuvchi tushumidan ayiriladi
    await page.getByLabel('Hisobot turi').selectOption({ label: 'Sotuvchilar' })
    await page.getByRole('row', { name: /Sotuvchi/ }).getByRole('button', { name: 'Sotuvchi' }).click()
    // tafsilot — ustunli jadval (B-19); storno «Bekor qilindi» belgisi bilan, «#raqam» zakazga havola
    await expect(page.locator('.tafsilot')).toContainText('Bekor qilindi')
    await expect(page.locator('.tafsilot')).toContainText("Storno Mijoz")
    await expect(page.locator('.tafsilot')).toContainText("-500 000 so'm")
    await ikkiKenglik(page, '4c-storno')
  })

  await test.step('kirgach manzilda #kirish qolmaydi; ichki bo\'limlar bir joyda', async () => {
    expect(new URL(page.url()).hash).toBe('')
    // keng ekranda Hisobotlar bo'limlari chap panelda (vertikal tablar), tepadagi tablar yashirin (2026-11-10)
    await expect(nav(page).getByRole('tablist', { name: "Hisobotlar bo'limlari" })).toBeVisible()
    await expect(page.locator('main .ichki-segment')).toBeHidden()
    await bolimga(page, 'Sozlama')
    // keng ekranda Sozlama bo'limlari chap panelda («‹ Asosiy» bilan); sahifada ro'yxat ustuni va ☰ yo'q
    await expect(nav(page).getByRole('navigation', { name: 'Sozlama menyusi' })).toBeVisible()
    await expect(page.locator('.sozlama-joy > .sozlama-yon')).toHaveCount(0)
    await expect(page.locator('.sozlama-menu')).toBeHidden()  // keng ekranda ☰ menyu kerak emas
    await page.waitForLoadState('networkidle')
    await page.screenshot({ path: 'test-results/korinish/4d-sozlama-keng.png', fullPage: true })
    await asosiyga(page)
    await expect(nav(page).getByRole('button', { name: 'Zakazlar', exact: true })).toBeVisible()  // asosiy menyu qaytdi
  })

  await test.step('zakaz kartasi keng ekranda', async () => {
    await bolimga(page, 'Zakazlar')
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
  await bolimga(page, 'Liboslar')
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
    // raqamning bir qismi terilsa mos buyumlar chiqadi: bosish yoki ↓ + Enter — darhol «topildi»
    await k.fill('02')
    const takliflar = page.getByRole('listbox', { name: 'Mos buyumlar' })
    await expect(takliflar.getByRole('option')).toHaveCount(1)
    await expect(takliflar).toContainText('FT-02')
    await k.press('ArrowDown')
    await k.press('Enter')
    await expect(page.getByText('✓ FT-02 Fata Klassik')).toBeVisible()
    await expect(k).toHaveValue('')
    await expect(k).toBeFocused()
    await ikkiKenglik(page, '5-sanoq-ochiq')
  })

  await test.step('yakun: topilmagan libos «yo\'q» bo\'lib chiqadi', async () => {
    await page.getByRole('button', { name: 'Yakunlash' }).click()
    await page.getByRole('alertdialog').getByRole('button', { name: 'Ha, yakunlash' }).click()  // yakunlash tasdiq bilan (B-24)
    const natija = page.locator('.blok', { hasText: 'Sanoq yakunlandi' })
    // «Yo'q» ro'yxati — jadval (B-24): skaner qilinmagan E2E-2 bor, skaner qilinganlar yo'q. Aniq son tekshirilmaydi —
    // oldingi spec'lar o'z liboslarini salonda qoldiradi (masalan, `kassa-davomi` QA16 — qaytarilgan zakaz broni arxivni to'sadi)
    await expect(natija).toContainText(/Yo'q \(\d+\)/)
    await expect(natija.locator('tbody tr', { hasText: 'E2E-2' })).toContainText('Libos E2E-2')
    for (const bor of ['E2E-1', 'FT-01', 'FT-02']) await expect(natija.locator('tbody tr', { hasText: bor })).toHaveCount(0)
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
    await bolimga(s, 'Zakazlar')
    await s.locator('input.jadval-qidiruv').fill('Naqdsiz Sinov')
    await s.locator('.zakaz-jadval tbody tr', { hasText: 'Naqdsiz Sinov' }).first().click()
    await expect(s.getByRole('heading', { name: /^Zakaz #\d+$/ })).toBeVisible()
    // berishda faqat hujjat/tillo garov — pul garovni kassir oladi
    const berish = s.locator('#asosiy-amal')
    await expect(berish).toContainText('Libosni berish (garov)')
    await expect(berish.locator('option', { hasText: /^Pul$/ })).toHaveCount(0)
    await expect(s.getByLabel('Garov summasi')).toHaveCount(0)
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
    await bolimga(page, 'Kassa')
    await page.getByRole('tab', { name: "To'lov qabul", exact: true }).click()
    await page.locator('.pos-zakaz', { hasText: 'Bepul Kelin' }).click()
    const chek = page.getByRole('region', { name: "To'lov" })
    await expect(chek).toContainText("Ijara summasi:0 so'm")  // chek yozuvlari kanvasdagidek («Ijara summasi:»)
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
    await bolimga(page, 'Zakazlar')
    await page.locator('input.jadval-qidiruv').fill('Tuzatish Sinov')
    await page.locator('.zakaz-jadval tbody tr', { hasText: 'Tuzatish Sinov' }).first().click()
    const tolovlar = page.locator('.karta-tolovlar')
    const avans = tolovlar.locator('.tolov-qator', { hasText: 'Avans' })
    await expect(avans).toContainText("400 000 so'm")
    await expect(avans).toContainText('Terminal')
    await tolovlar.getByText('Tuzatish', { exact: true }).click()
    await tolovlar.getByLabel("To'lov usuli").selectOption('naqd')
    await tolovlar.getByLabel('Sabab').fill('naqd edi, terminal deb yozilgan')
    await ikkiKenglik(page, '9-tolov-tuzatish')
    await tolovlar.getByRole('button', { name: 'Tuzatishni saqlash' }).click()
    await expect(page.getByText("To'lov tuzatildi.")).toBeVisible()
    await expect(avans).toContainText('Naqd')
  } finally {
    await apiSorov(page, 'POST', '/kassa/smena/yopish/', { summa: 400_000, izoh: '' })
  }
  expect(xatolar).toEqual([])
})

test('yetkazib beruvchi: libos qisman to\'lab olinadi, qarz to\'lanadi', async ({ page }) => {
  const xatolar = xatolarniKuzat(page)
  await kirish(page, 'Rahbar', '1111')
  await bolimga(page, 'Liboslar')
  await page.getByRole('tab', { name: 'Yetkazib beruvchilar' }).click()
  await page.getByText("Yetkazib beruvchi qo'shish").click()
  await page.getByLabel('Nomi').fill('Istanbul Bridal')
  await page.getByRole('button', { name: "Qo'shish", exact: true }).click()
  await expect(page.getByText("Yetkazib beruvchi qo'shildi.")).toBeVisible()

  await test.step('libos qo\'shishda: qayerdan olingan va hozir qancha to\'landi', async () => {
    await page.getByRole('tab', { name: "Ro'yxat" }).click()
    await page.getByRole('button', { name: 'Libos qo\'shish' }).click()
    const oyna = page.getByRole('dialog')
    await oyna.getByLabel('Artikul').fill('YB-1')
    await oyna.getByLabel('Nomi').fill('Turk libosi')
    await oyna.getByLabel('Tannarx').fill('10000000')
    await oyna.getByLabel('Ijara narxi').fill('2500000')  // rahbar libosi narx va tannarxsiz qo'shilmaydi (2026-11-10)
    await oyna.getByLabel('Qayerdan olingan').selectOption({ label: 'Istanbul Bridal' })
    await oyna.getByLabel("Hozir to'landi").fill('4000000')
    await expect(oyna).toContainText("Yetkazib beruvchiga qarz: 6 000 000 so'm")
    // rasmlar qo'shish oynasining o'zida tanlanadi (galereyadan; kompyuterda kamera tugmasi yo'q) va libos bilan yuklanadi
    const rasm = oyna.getByRole('group', { name: "Rasm qo'shish" })
    await rasm.locator('input[type=file]:not([capture])').setInputFiles(['public/kelinlar/1.jpg', 'public/kelinlar/2.jpg'])
    await expect(oyna.locator('.rasm-katak img')).toHaveCount(2)
    await expect(rasm.getByRole('button', { name: 'Kamera bilan' })).toBeHidden()
    await ikkiKenglik(page, '10-libos-yetkazib-beruvchi')
    await oyna.getByRole('button', { name: "Qo'shish · 2 ta rasm bilan" }).click()
    await expect(page.getByText("Libos katalogga qo'shildi.")).toBeVisible()
    await expect(page.locator('.libos-karta', { hasText: 'YB-1' }).locator('img')).toBeVisible()
  })

  await test.step('libos artikuli: sozlamada prefiks va avto raqam, formada «i»', async () => {
    try {
      await bolimga(page, 'Sozlama')
      await page.getByRole('navigation', { name: 'Sozlama menyusi' }).getByRole('button', { name: 'Libos artikuli', exact: true }).click()  // B-36: «Liboslar» guruhida
      await page.getByLabel('Prefiks').fill('E-')
      await page.getByLabel("Raqam avtomatik qo'yilsin").check()
      await page.getByLabel('Sanoq nechidan boshlansin').fill('5')
      await page.getByLabel('Raqam necha xonali').selectOption('3')
      await expect(page.locator('.blok', { hasText: 'Libos artikuli' })).toContainText('Namuna: E-005, E-006, E-007')
      await page.getByRole('button', { name: 'Saqlash', exact: true }).click()
      await expect(page.getByText('Sozlamalar saqlandi.')).toBeVisible()
      await ikkiKenglik(page, '13-artikul-sozlama')

      await asosiyga(page)
      await bolimga(page, 'Liboslar')
      await page.getByRole('tab', { name: "Ro'yxat" }).click()
      await page.getByRole('button', { name: 'Libos qo\'shish' }).click()
      const oyna = page.getByRole('dialog')
      await expect(oyna.getByLabel('Artikul')).toHaveAttribute('placeholder', 'avtomatik: E-005')
      await oyna.locator('label', { hasText: /^Artikul/ }).getByRole('button', { name: 'Izoh' }).click()  // kanvas tartibi: Nomi, keyin Artikul
      await expect(oyna.getByRole('note')).toContainText("tizim keyingi raqamni o'zi beradi: E-005")
      await page.screenshot({ path: 'test-results/korinish/14-artikul-info.png' })
      await oyna.getByLabel('Nomi').fill('Avto libos')  // artikul bo'sh qoldiriladi
      await oyna.getByLabel('Ijara narxi').fill('1500000')
      await oyna.getByLabel('Tannarx').fill('4000000')
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
    const t = page.locator('.aks-tafsilot')  // kanvas: tanlangan aksessuar o'ng panelda
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
    await expect(qator).toContainText('6 440 000')  // «Kimdan olamiz»: qarz qizil summa
    await qator.getByRole('button', { name: /Istanbul Bridal/ }).click()
    const hisob = page.getByRole('region', { name: 'Istanbul Bridal hisobi' })  // kanvas: tanlangani o'ng panelda
    await expect(hisob).toContainText('YB-1')
    // olingan aksessuarlar — jadval (B-35): har partiya alohida qator, soni × narx = jami
    const tj = hisob.locator('tbody tr', { hasText: 'TJ Toj Oltin' })
    for (const [soni, narx, jami] of [['3', "100 000 so'm", "300 000 so'm"], ['2', "120 000 so'm", "240 000 so'm"]]) {
      const katak = tj.filter({ hasText: jami }).locator('td')
      await expect(katak.nth(2)).toHaveText(soni)
      await expect(katak.nth(3)).toHaveText(narx)
    }
    await ikkiKenglik(page, '12-yetkazib-qarz')
    await hisob.getByLabel("To'lov summasi").fill('6440000')
    await hisob.getByRole('button', { name: "To'lov yozish" }).click()
    await expect(qator).toContainText("qarz yo'q")
  })
  expect(xatolar).toEqual([])
})
