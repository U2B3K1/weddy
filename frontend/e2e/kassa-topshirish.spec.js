// Kassa: har kim o'z qo'lidagi naqdga javob beradi. Rahbar smenani ochib pul oladi, sotuvchi qo'shiladi;
// rahbar pulini sotuvchiga topshirib chiqadi → sotuvchi «Sizga topshirilgan pul» dan qabul qiladi →
// sotuvchi yopib pulni rahbarga beradi (seyfda 0 qoladi). Keyin «Alohida kassir» rejimida sotuvchi ekrani.
// Skrinshotlar: test-results/kassa/*.png (ko'z bilan tekshirish uchun).
import { expect, test } from '@playwright/test'
import { bolimga, QURILMA_HOLATI, kirish, xatolarniKuzat } from './yordam.js'

const rasm = (page, nom) => page.screenshot({ path: `test-results/kassa/${nom}.png`, fullPage: true })
// Sahifa yangilansa Dashboard ochiladi — kassa holatini qayta yuklash uchun yangilab, Kassaga o'tamiz
const kassaga = async (p) => { await p.reload(); await bolimga(p, 'Kassa') }
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
  await bolimga(page, 'Kassa')

  await test.step('rahbar smenani ochadi va 2 000 000 avans oladi', async () => {
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
    const libos = (await apiSorov(page, 'GET', '/liboslar/')).find((l) => l.artikul === 'E2E-2')
    const z = await apiSorov(page, 'POST', '/zakazlar/', { telefon: `+99890${String(Date.now()).slice(-7)}`, fio: 'Kassa Sinov',
      dan: iso(40), gacha: iso(42), liboslar: [libos.id] })
    await apiSorov(page, 'POST', '/kassa/tolovlar/', { zakaz: z.id, tur: 'avans', summa: 2_000_000 })
  })

  const ctx = await browser.newContext({ storageState: QURILMA_HOLATI })
  const sotuvchi = await ctx.newPage()
  const xatolar2 = xatolarniKuzat(sotuvchi)
  await kirish(sotuvchi, 'Sotuvchi', '2222')
  await bolimga(sotuvchi, 'Kassa')

  await test.step('sotuvchi qo\'shiladi; rahbar pulini unga topshirib chiqadi', async () => {
    await sotuvchi.locator('.smena-panel').getByRole('button', { name: "Smenaga qo'shilish" }).click()
    await expect(sotuvchi.locator('.smena-naqd')).toContainText("Naqd0 so'm")
    await kassaga(page)
    await expect(page.locator('.smena-naqd')).toContainText("2 000 000 so'm")
    // smenada ikki xodim — yopish tugmasi yo'q (oxirgi qolgan xodim yopadi), faqat topshirib chiqish
    await expect(page.locator('.smena-panel').getByRole('button', { name: 'Smenani yopish' })).toHaveCount(0)
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
    // «Kelmadi» qaytarib bo'lmaydi — avval oqibati aytiladi (C-03); bu yerda bekor qilinadi
    await otk.getByRole('button', { name: 'Kelmadi' }).click()
    const kelmadi = page.getByRole('alertdialog', { name: "O'tkazma kelmadimi?" })
    await expect(kelmadi).toContainText("700 000 so'm hisobdan chiqadi")
    await rasm(page, '4b-kelmadi-tasdiq')
    await kelmadi.getByRole('button', { name: "Yo'q, qaytish" }).click()
    await expect(kelmadi).toHaveCount(0)
    await otk.getByRole('button', { name: 'Keldi' }).click()
    await expect(page.getByText('Tasdiqlandi: pul keldi.')).toBeVisible()
    await kassaga(sotuvchi)
  })

  await test.step("smena hisoboti: tepada 4 ko'rsatkich (maket uslubi), terminal — tizimdagi summa", async () => {
    await sotuvchi.getByRole('tab', { name: 'Smena hisoboti', exact: true }).click()
    const kpi = sotuvchi.getByRole('region', { name: "Smena ko'rsatkichlari" })
    await expect(kpi.locator('.dash-kpi-karta')).toHaveCount(4)
    await expect(kpi.locator('.dash-kpi-karta', { hasText: 'Terminal' })).toContainText("300 000 so'm")
    await expect(sotuvchi.getByRole('region', { name: 'Kun yakuni' })).toBeVisible()
    await rasm(sotuvchi, '4c-smena-hisoboti')
    await kassaga(sotuvchi)  // keyingi qadam smena panelidagi «Smenani yopish» bilan (hisobotda amallar «Kun yakuni»da)
  })

  await test.step('sotuvchi yopadi va pulni rahbarga beradi', async () => {
    await sotuvchi.locator('.smena-panel').getByRole('button', { name: 'Smenani yopish' }).click()
    const oyna = sotuvchi.getByRole('dialog', { name: 'Smenani yopish' })
    await oyna.getByRole('radio', { name: 'Rahbarga: Rahbar' }).check()  // kanvas: «Pul qayerda qoladi?» — tanlov tugmalari
    await summaTer(oyna, ['1', '9', '9', '0', '000'])
    await expect(oyna).toContainText("Farq yo'q")
    await expect(oyna.getByRole('button', { name: 'Smenani yopish' })).toBeDisabled()  // terminal hisoboti kiritilmagan
    await oyna.getByLabel('Terminal hisoboti').fill('300000')
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
    await bolimga(page, 'Sozlama')
    await page.getByRole('navigation', { name: 'Sozlama menyusi' }).getByRole('button', { name: 'Kassa', exact: true }).click()  // B-36: «Salon va xodimlar» guruhida
    await page.getByLabel('Alohida kassir').check()
    await rasm(page, '5-sozlama-kassa')
    await page.getByRole('region', { name: "Saqlanmagan o'zgarishlar" }).getByRole('button', { name: 'Saqlash' }).click()
    try {
      await expect(page.getByText('Sozlamalar saqlandi.')).toBeVisible()
      await kassaga(sotuvchi)  // yangilanganda /auth/me/ dan yangi rejim keladi
      // yagona bo'lim — tablar chiqmaydi; bo'lim nomi sarlavha ostida (shisha uslubi, Ndiz)
      await expect(sotuvchi.locator('.ustki-nom p:not(.nom-tor)')).toHaveText('Yangi zakaz')
      await expect(sotuvchi.getByRole('tab', { name: "To'lov qabul", exact: true })).toHaveCount(0)  // faqat zakaz oladi
      await rasm(sotuvchi, '6-kassir-rejimida-sotuvchi')
    } finally {  // keyingi testlar uchun rejim qaytariladi
      await apiSorov(page, 'PATCH', '/sozlamalar/', { kassa_rejimi: 'sotuvchi' })
    }
  })

  await test.step('dashbord: «Kassada kamomad» — kamomad kimda', async () => {
    await page.reload()  // yangilanganda Dashboard ochiladi
    await expect(page.getByRole('region', { name: 'Egasining savollari' })).toContainText("Rahbar -10 000 so'm")
    await expect(page.getByRole('region', { name: 'Liboslar holati' })).toContainText('hali sanalmagan')
    await rasm(page, '7-dashbord-nazorat')
  })

  await ctx.close()
  expect([...xatolar, ...xatolar2]).toEqual([])
})
