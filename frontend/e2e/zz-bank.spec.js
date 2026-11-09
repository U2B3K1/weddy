// Bank solishtirish: sotuvchi «karta» deb yozgan to'lov rahbarga tarixda ko'rinadi — kim, qachon, qaysi zakazga, qancha.
// «zz-» — smena ochadi/qo'shiladi, boshqa testlardan keyin ishlasin.
import { expect, test } from '@playwright/test'
import { QURILMA_HOLATI, kirish, xatolarniKuzat } from './yordam.js'

const nav = (page) => page.getByRole('navigation', { name: "Bo'limlar" })
const iso = (kun) => { const t = new Date(); t.setDate(t.getDate() + kun); return t.toLocaleDateString('sv-SE') }
const apiSorov = (page, usul, yol, tana) => page.evaluate(async ([usul, yol, tana]) => {
  const r = await fetch(`http://127.0.0.1:8001/api${yol}`, {
    method: usul, body: tana ? JSON.stringify(tana) : undefined,
    headers: { 'Content-Type': 'application/json', 'X-Device-Token': localStorage.getItem('weddy.qurilma_token'),
               Authorization: `Bearer ${sessionStorage.getItem('weddy.token')}` },
  })
  return r.json()
}, [usul, yol, tana])

test("bank solishtirish: karta to'lovlari tarixi — kim, qachon, qaysi zakazga", async ({ page, browser }) => {
  await kirish(page, 'Sotuvchi', '2222')
  const smena = await apiSorov(page, 'GET', '/kassa/smena/')
  if (!smena.ochiq) await apiSorov(page, 'POST', '/kassa/smena/ochish/', { boshlangich_qoldiq: 0 })
  else if (!smena.men_ishtirokchi) await apiSorov(page, 'POST', '/kassa/smena/qoshilish/')
  const bosh = await apiSorov(page, 'GET', `/bronlar/bosh/?dan=${iso(300)}&gacha=${iso(301)}`)
  const libos = bosh.find((l) => !l.band && !l.qulflangan && l.ijara_narxi >= 100_000)
  expect(libos, JSON.stringify(bosh)).toBeTruthy()
  const z = await apiSorov(page, 'POST', '/zakazlar/', { telefon: '+998907770044', fio: 'Bank Sinov', dan: iso(300), gacha: iso(301), liboslar: [libos.id] })
  const t = await apiSorov(page, 'POST', '/kassa/tolovlar/', { zakaz: z.id, tur: 'avans', usul: 'karta', summa: 100_000 })
  expect(t.detail, JSON.stringify(t)).toBeUndefined()

  const ctx = await browser.newContext({ storageState: QURILMA_HOLATI })
  const rahbar = await ctx.newPage()
  const xatolar = xatolarniKuzat(rahbar)
  await rahbar.setViewportSize({ width: 1280, height: 860 })
  await kirish(rahbar, 'Rahbar', '1111')
  await nav(rahbar).getByRole('button', { name: 'Hisobotlar', exact: true }).click()
  await rahbar.getByRole('tab', { name: 'Bank solishtirish', exact: true }).click()
  await expect(rahbar.getByText('Nima uchun:')).toBeVisible()
  const tarix = rahbar.locator('details.bank-tarix', { hasText: 'Terminal' })  // kanvas: jadval ostida har usulning tarixi
  await tarix.locator('summary').click()
  const qator = tarix.locator('tbody tr', { hasText: `#${z.raqam} Bank Sinov` })
  await expect(qator).toContainText('Sotuvchi')
  await expect(qator).toContainText('100 000')
  await rahbar.screenshot({ path: 'test-results/bank/tarix-keng.png', fullPage: true, animations: 'disabled' })
  // zakazga o'tish
  await qator.getByRole('button', { name: `#${z.raqam} Bank Sinov` }).click()
  await expect(rahbar.locator('.karta-asosiy')).toContainText('Bank Sinov')

  // Dashboard: shapka menyusidagi «Chiqish» panellar ostida qolmaydi (trial — ustini boshqa element yopsa yiqiladi);
  // «Salonni sozlash» → «Yashirish» butun ilovani qora ekranga aylantirmaydi
  // zakaz kartasi ochilganda chap panel asosiy menyuga qaytadi (R2) — «Asosiy» bosish shart emas
  await expect(nav(rahbar).getByRole('button', { name: 'Asosiy', exact: true })).toHaveCount(0)
  await nav(rahbar).getByRole('button', { name: 'Dashboard', exact: true }).click()
  await rahbar.locator('.ustki-xodim').click()
  await rahbar.getByRole('menu').getByRole('menuitem', { name: 'Chiqish' }).click({ trial: true, timeout: 5000 })
  await rahbar.keyboard.press('Escape')
  // «Salonni sozlash» endi qo'ng'iroqcha menyusida (ixcham)
  await rahbar.getByRole('button', { name: /^Bildirishnomalar/ }).click()
  const sozlash = rahbar.locator('.xabar-sozlash')
  if (await sozlash.isVisible()) {
    await sozlash.getByRole('button', { name: 'Yashirish' }).click()
    await expect(sozlash).toHaveCount(0)
    await expect(nav(rahbar)).toBeVisible()
  }
  await rahbar.keyboard.press('Escape')
  expect(xatolar).toEqual([])
  await ctx.close()
})
