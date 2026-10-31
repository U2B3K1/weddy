// Kassa: har kim o'z qo'lidagi naqdga javob beradi. Rahbar smenani ochib pul oladi, sotuvchi qo'shiladi;
// rahbar pulini sotuvchiga topshirib chiqadi → sotuvchi «Sizga topshirilgan pul» dan qabul qiladi →
// sotuvchi yopib pulni rahbarga beradi (seyfda 0 qoladi). Keyin «Alohida kassir» rejimida sotuvchi ekrani.
// Skrinshotlar: test-results/kassa/*.png (ko'z bilan tekshirish uchun).
import { expect, test } from '@playwright/test'
import { QURILMA_HOLATI, kirish, xatolarniKuzat } from './yordam.js'

const nav = (page) => page.getByRole('navigation', { name: "Bo'limlar" })
const rasm = (page, nom) => page.screenshot({ path: `test-results/kassa/${nom}.png`, fullPage: true })
// Sahifa yangilansa Dashboard ochiladi — kassa holatini qayta yuklash uchun yangilab, Kassaga o'tamiz
const kassaga = async (p) => { await p.reload(); await nav(p).getByRole('button', { name: 'Kassa', exact: true }).click() }
const iso = (kun) => { const t = new Date(); t.setDate(t.getDate() + kun); return t.toLocaleDateString('sv-SE') }

async function summaTer(joy, raqamlar) {
  const k = joy.getByRole('group', { name: 'Raqamli klaviatura' })
  for (const r of raqamlar) await k.getByRole('button', { name: r, exact: true }).click()
}

// Ilovaning o'z tokenlari bilan API so'rovi (zakazni tez yaratish uchun — UI oqimi zakaz-oqimi.spec.js da)
const apiSorov = (page, usul, yol, tana) => page.evaluate(async ([usul, yol, tana]) => {
  const r = await fetch(`http://127.0.0.1:8001/api${yol}`, {
    method: usul, body: tana ? JSON.stringify(tana) : undefined,
    headers: { 'Content-Type': 'application/json', 'X-Device-Token': localStorage.getItem('weddy.qurilma_token'),
               Authorization: `Bearer ${sessionStorage.getItem('weddy.token')}` },
  })
  return r.json()
}, [usul, yol, tana])

test('pul topshirish: rahbar → sotuvchi → rahbar; kassir rejimi', async ({ page, browser }) => {
  const xatolar = xatolarniKuzat(page)
  await kirish(page, 'Rahbar', '1111')
  await nav(page).getByRole('button', { name: 'Kassa', exact: true }).click()

  await test.step('rahbar smenani ochadi va 2 000 000 avans oladi', async () => {
    await page.locator('.smena-panel').getByRole('button', { name: 'Smenani ochish' }).click()
    const oyna = page.getByRole('dialog', { name: 'Smenani ochish' })
    await summaTer(oyna, ['0'])
    await oyna.getByRole('button', { name: 'Smenani ochish' }).click()
    await expect(page.getByText('Smena ochildi.')).toBeVisible()
    const libos = (await apiSorov(page, 'GET', '/liboslar/')).find((l) => l.artikul === 'E2E-2')
    const z = await apiSorov(page, 'POST', '/zakazlar/', { telefon: `+99890${String(Date.now()).slice(-7)}`, fio: 'Kassa Sinov',
      dan: iso(40), gacha: iso(42), liboslar: [libos.id] })
    await apiSorov(page, 'POST', '/kassa/tolovlar/', { zakaz: z.id, tur: 'avans', summa: 2_000_000 })
  })

  const ctx = await browser.newContext({ storageState: QURILMA_HOLATI })
  const sotuvchi = await ctx.newPage()
  const xatolar2 = xatolarniKuzat(sotuvchi)
  await kirish(sotuvchi, 'Sotuvchi', '2222')
  await nav(sotuvchi).getByRole('button', { name: 'Kassa', exact: true }).click()

  await test.step('sotuvchi qo\'shiladi; rahbar pulini unga topshirib chiqadi', async () => {
    await sotuvchi.locator('.smena-panel').getByRole('button', { name: "Smenaga qo'shilish" }).click()
    await expect(sotuvchi.locator('.smena-naqd')).toContainText("Sizda naqd0 so'm")
    await kassaga(page)
    await expect(page.locator('.smena-naqd')).toContainText("2 000 000 so'm")
    await rasm(page, '1-rahbar-sizda-naqd')
    await page.locator('.smena-panel').getByRole('button', { name: 'Pulni topshirib chiqish' }).click()
    const oyna = page.getByRole('dialog', { name: 'Pulni topshirib chiqish' })
    await oyna.getByLabel('Kimga').selectOption({ label: 'Sotuvchi (smenada qoladi)' })
    await summaTer(oyna, ['1', '9', '9', '0', '000'])
    await expect(oyna).toContainText("Farq: -10 000 so'm")
    await rasm(page, '2-topshirish-oynasi')
    await oyna.getByRole('button', { name: 'Topshirib chiqish' }).click()
    await expect(page.getByText(/Pul Sotuvchiga topshirildi.*Farq: -10 000/)).toBeVisible()
  })

  await test.step('sotuvchi qabul qilmaguncha yopa olmaydi; qabul qiladi', async () => {
    await kassaga(sotuvchi)
    const kut = sotuvchi.locator('.blok', { hasText: 'Sizga topshirilgan pul' })
    await expect(kut).toContainText("Rahbar · 1 990 000 so'm")
    await rasm(sotuvchi, '3-sizga-topshirilgan-pul')
    await kut.getByRole('button', { name: "1 990 000 so'm qabul qildim" }).click()
    await expect(sotuvchi.getByText("Qabul qilindi: 1 990 000 so'm.")).toBeVisible()
    await expect(sotuvchi.locator('.smena-naqd')).toContainText("1 990 000 so'm")
  })

  await test.step('naqdsiz: o\'tkazmani rahbar tasdiqlaydi, terminal pulga sverka kerak', async () => {
    const libos = (await apiSorov(sotuvchi, 'GET', '/liboslar/')).find((l) => l.artikul === 'E2E-1')
    const z = await apiSorov(sotuvchi, 'POST', '/zakazlar/', { telefon: `+99891${String(Date.now()).slice(-7)}`, fio: 'Naqdsiz Sinov',
      dan: iso(50), gacha: iso(52), liboslar: [libos.id] })
    await apiSorov(sotuvchi, 'POST', '/kassa/tolovlar/', { zakaz: z.id, tur: 'avans', summa: 700_000, usul: 'otkazma' })
    await apiSorov(sotuvchi, 'POST', '/kassa/tolovlar/', { zakaz: z.id, tur: 'qoldiq', summa: 300_000, usul: 'karta' })
    await kassaga(page)
    const otk = page.locator('.blok', { hasText: "O'tkazmalar — hisobingizga keldimi?" })
    await expect(otk).toContainText("O'tkazma · 700 000 so'm")
    await rasm(page, '4a-otkazma-keldimi')
    await otk.getByRole('button', { name: 'Keldi' }).click()
    await expect(page.getByText('Tasdiqlandi: pul keldi.')).toBeVisible()
    await kassaga(sotuvchi)
  })

  await test.step('sotuvchi yopadi va pulni rahbarga beradi', async () => {
    await sotuvchi.locator('.smena-panel').getByRole('button', { name: 'Smenani yopish' }).click()
    const oyna = sotuvchi.getByRole('dialog', { name: 'Smenani yopish' })
    await oyna.getByLabel('Pul qayerda qoladi').selectOption({ label: 'Rahbarga topshiraman: Rahbar' })
    await summaTer(oyna, ['1', '9', '9', '0', '000'])
    await expect(oyna).toContainText("Farq yo'q")
    await expect(oyna.getByRole('button', { name: 'Smenani yopish' })).toBeDisabled()  // terminal sverkasi kiritilmagan
    await oyna.getByLabel('Terminal sverkasi').fill('300000')
    await expect(oyna).toContainText("Terminal bo'yicha farq yo'q")
    await rasm(sotuvchi, '4-yopish-rahbarga')
    await oyna.getByRole('button', { name: 'Smenani yopish' }).click()
    await sotuvchi.getByRole('alertdialog', { name: 'Smenani yopasizmi?' }).getByRole('button', { name: 'Smenani yopish' }).click()
    await expect(sotuvchi.getByText("Smena yopildi. Farq: 0 so'm")).toBeVisible()
    // rahbarda tasdiq kutayotgan inkassatsiya
    await kassaga(page)
    const kut = page.locator('.blok', { hasText: 'Sizga topshirilgan pul' })
    await expect(kut).toContainText('inkassatsiya')
    await kut.getByRole('button', { name: "1 990 000 so'm qabul qildim" }).click()
    await expect(page.getByText("Qabul qilindi: 1 990 000 so'm.")).toBeVisible()
  })

  await test.step('«Alohida kassir» rejimi: sozlama va sotuvchi ekrani', async () => {
    await nav(page).getByRole('button', { name: 'Asosiy', exact: true }).click()  // Kassa menyusidan asosiy bo'limlarga
    await nav(page).getByRole('button', { name: 'Sozlama', exact: true }).click()
    const guruh = nav(page).getByRole('button', { name: 'Salon' })
    if (await guruh.getAttribute('aria-expanded') !== 'true') await guruh.click()
    await nav(page).getByRole('button', { name: 'Kassa', exact: true }).click()
    await page.getByLabel('Alohida kassir').check()
    await rasm(page, '5-sozlama-kassa')
    await page.getByRole('region', { name: "Saqlanmagan o'zgarishlar" }).getByRole('button', { name: 'Saqlash' }).click()
    try {
      await expect(page.getByText('Sozlamalar saqlandi.')).toBeVisible()
      await kassaga(sotuvchi)  // yangilanganda /auth/me/ dan yangi rejim keladi
      await expect(nav(sotuvchi).getByRole('button', { name: 'Yangi zakaz', exact: true })).toBeVisible()
      await expect(nav(sotuvchi).getByRole('button', { name: "To'lov qabul" })).toHaveCount(0)  // faqat zakaz oladi
      await rasm(sotuvchi, '6-kassir-rejimida-sotuvchi')
    } finally {  // keyingi testlar uchun rejim qaytariladi
      await apiSorov(page, 'PATCH', '/sozlamalar/', { kassa_rejimi: 'sotuvchi' })
    }
  })

  await test.step('dashbord: «Nazorat» — kamomad kimda', async () => {
    await page.reload()  // yangilanganda Dashboard ochiladi
    const n = page.getByRole('region', { name: 'Nazorat, oxirgi 7 kun' })
    await expect(n).toContainText("Rahbar -10 000 so'm")
    await expect(n).toContainText('Sanalmagan')
    await rasm(page, '7-dashbord-nazorat')
  })

  await ctx.close()
  expect([...xatolar, ...xatolar2]).toEqual([])
})
