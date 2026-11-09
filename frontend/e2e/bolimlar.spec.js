// Tutun testi: rahbar va sotuvchi har bir bo'lim va ichki bo'limni ochadi — JS xatosi va 5xx bo'lmasligi kerak.
import { expect, test } from '@playwright/test'
import { GURUHLAR, SOZLAMA_BOLIMLAR } from '../src/pages/sozlamaBolimlari.js'
import { bolim, kirish, xatolarniKuzat } from './yordam.js'

// Ichki bo'limlari sahifa tepasidagi tablarda bo'lgan bo'limlar (App.jsx: kassaRoyxat, HISOBOT_ROYXAT; Ndiz — shisha uslubi)
const ICHKI = {
  Kassa: ['Yangi zakaz', "To'lov qabul", 'Xarajat', 'Inkassatsiya', 'Zaloglar', 'Smena hisoboti', 'Smenalar tarixi'],
  // «Grafik» bo'limi yo'q (B-14): 12 oylik sof foyda grafigi — «Oylik foyda» ostida (QA-07: nav nomi sahifa sarlavhasi bilan bir xil)
  Hisobotlar: ['Umumiy hisobot', 'Oylik foyda', 'Xarajatlar', 'Sotuvchi bonusi', 'Bank solishtirish'],
}

const nav = (page) => page.getByRole('navigation', { name: "Bo'limlar" })

async function och(page, nomi) {
  await nav(page).getByRole('button', { name: nomi, exact: true }).click()
  await page.waitForLoadState('networkidle')
}
async function tabOch(page, nomi) {
  await page.getByRole('tab', { name: nomi, exact: true }).click()
  await page.waitForLoadState('networkidle')
}

test('rahbar: barcha bo\'limlar va ichki bo\'limlar ochiladi', async ({ page }) => {
  const xatolar = xatolarniKuzat(page)
  await kirish(page, 'Rahbar', '1111')
  // rahbar dashboardida kundalik operatsion kartalar (olib ketish, qaytarish, qo'ng'iroq, qoldiq) yo'q — ular xodimlarda;
  // rahbarga faqat qarorlar va qarzdorlar (bo'lsa)
  for (const nom of ['Bugun olib ketadi', 'Bugun qaytaradi', "Qo'ng'iroq qilish", "Qoldiq to'lanmagan"]) {
    await expect(page.getByRole('region', { name: new RegExp(`^${nom}:`) })).toHaveCount(0)
  }
  for (const karta of ['Egasining savollari', 'Tushum dinamikasi', 'Diqqat talab', 'Liboslar holati', 'Zakaz va mijoz', 'Xodimlar']) {  // kanvas bloklari
    await expect(page.getByRole('region', { name: karta })).toBeVisible()
  }
  const [kpiY, torY] = await page.evaluate(() => ['.dash-kpi', '.dash-tor']
    .map((s) => document.querySelector(s).getBoundingClientRect().top))
  expect(kpiY).toBeLessThan(torY)
  // davr — «Tushum dinamikasi» kartasidagi ixcham tanlov; ko'rsatkichlar shu davr bo'yicha qayta yuklanadi
  await page.getByRole('region', { name: 'Tushum dinamikasi' }).getByLabel('Davr').selectOption('7')
  await expect(page.getByRole('region', { name: 'Tushum dinamikasi' })).toContainText('oldingi 7 kun')
  // «+ Libos qo'shish» — Liboslar bo'limi boshida (kanvas; Dashboard'da «Tezkor amallar» yo'q): qo'shish oynasi ochiladi
  await och(page, 'Liboslar')
  await page.getByRole('button', { name: "Libos qo'shish" }).click()
  await expect(page.getByRole('dialog', { name: "Libos qo'shish" })).toBeVisible()
  await page.keyboard.press('Escape')
  await expect(page.getByRole('dialog', { name: "Libos qo'shish" })).toHaveCount(0)
  await och(page, 'Dashboard')
  for (const nom of ['Dashboard', 'Liboslar', 'Zakazlar', 'Mijozlar', 'Kassa', 'Hisobotlar']) {
    await test.step(nom, async () => {
      await och(page, nom)
      for (const ichki of ICHKI[nom] || []) await test.step(ichki, () => tabOch(page, ichki))
      if (nom === 'Hisobotlar') await expect(page.getByRole('tab', { name: 'Grafik', exact: true })).toHaveCount(0)
    })
  }
  await test.step('Sozlama', async () => {
    await och(page, 'Sozlama')
    // «Barcha sozlamalar» umumiy ko'rinishi (maket uslubi): har guruh — karta, har bo'lim — belgi, nom, izoh; bosilsa bo'lim formasi
    const markaz = page.getByRole('group', { name: "Sozlama bo'limlari" })
    for (const g of GURUHLAR) await expect(markaz.getByRole('region', { name: g.nomi })).toBeVisible()
    await expect(markaz.getByRole('button')).toHaveCount(SOZLAMA_BOLIMLAR.length)
    await page.screenshot({ path: 'test-results/sozlama/1-barcha-sozlamalar.png', animations: 'disabled' })
    await page.setViewportSize({ width: 390, height: 844 })  // telefon: bitta ustun, gorizontal surilish yo'q
    await page.screenshot({ path: 'test-results/sozlama/2-telefon.png', fullPage: true, animations: 'disabled' })
    const [kenglik, ekran] = await page.evaluate(() => [document.documentElement.scrollWidth, window.innerWidth])
    expect(kenglik, "Sozlama umumiy ko'rinishi telefonda gorizontal surilmasin").toBeLessThanOrEqual(ekran)
    await page.setViewportSize({ width: 1280, height: 860 })
    await markaz.getByRole('button', { name: /^Bron va zalog/ }).click()
    await expect(page.getByRole('heading', { name: 'Bron va zalog' })).toBeVisible()  // guruh sahifasi: har bo'lim — panel (kanvas)
    const sozMenyu = page.getByRole('navigation', { name: 'Sozlama menyusi' })
    await sozMenyu.getByRole('button', { name: 'Barcha sozlamalar', exact: true }).click()  // sahifadagi chap ro'yxatdan umumiy ko'rinishga qaytish
    await expect(markaz).toBeVisible()
    for (const g of GURUHLAR) {
      for (const b of SOZLAMA_BOLIMLAR.filter((x) => x.guruh === g.nomi)) {
        await test.step(b.nomi, async () => {
          await sozMenyu.getByRole('button', { name: b.nomi, exact: true }).click()
          await page.waitForLoadState('networkidle')
        })
      }
    }
  })
  expect(xatolar).toEqual([])
})

test('sotuvchi: rahbar bo\'limlari ko\'rinmaydi, o\'zinikilari ochiladi', async ({ page }) => {
  const xatolar = xatolarniKuzat(page)
  await kirish(page, 'Sotuvchi', '2222')
  await expect(bolim(page, 'Hisobotlar')).toHaveCount(0)
  await expect(bolim(page, 'Sozlama')).toHaveCount(0)
  // xodim bosh sahifasi — «Bugungi ishlar» kartalari (faqat ish bor turlar) yoki «shoshilinch ish yo'q»
  const ishlar = page.getByRole('region', { name: 'Bugungi ishlar' })
  await expect(ishlar).toBeVisible()
  await expect(ishlar).not.toContainText('Yuklanmoqda')  // kartalar soni ma'lumot kelgach sanaladi
  const kartalar = ishlar.locator('.ish-karta')
  for (let i = 0; i < await kartalar.count(); i++) {
    await expect(kartalar.nth(i)).toHaveAttribute('aria-label', /: [1-9]\d*$/)  // bo'sh tur karta bo'lib chiqmaydi
  }
  if (await kartalar.count() === 0) await expect(ishlar).toContainText("Bugun shoshilinch ish yo'q")
  for (const nom of ['Dashboard', 'Liboslar', 'Zakazlar', 'Mijozlar']) await och(page, nom)
  await och(page, 'Kassa')
  for (const ichki of ICHKI.Kassa.filter((x) => x !== 'Smenalar tarixi')) await tabOch(page, ichki)
  await expect(page.getByRole('tab', { name: 'Smenalar tarixi', exact: true })).toHaveCount(0)
  // shapka menyusi: «Chiqish» ustida profil rasmi — yuklangach shapkada va kirish ekranidagi kartochkada ko'rinadi
  await page.locator('.ustki-xodim').click()
  const menyu = page.getByRole('menu')
  await expect(menyu.getByRole('menuitem', { name: 'Profil rasmini yuklash' })).toBeVisible()
  await menyu.locator('input[type=file]').setInputFiles('public/kelinlar/1.jpg')
  await expect(page.locator('.ustki-xodim .xodim-chip img')).toBeVisible()
  // ismga bosish — menyu ochiladi, undagi «Chiqish» PIN ekraniga qaytaradi
  await page.locator('.ustki-xodim').click()
  await expect(menyu.getByRole('menuitem', { name: 'Profil rasmini almashtirish' })).toBeVisible()
  await menyu.getByRole('menuitem', { name: 'Ilovadan chiqish' }).click()
  // smenada qo'lida naqd bo'lsa avval ogohlantirish chiqadi (oldingi testlar holatiga bog'liq) — bu yerda faqat chiqish tekshiriladi
  const kirishEkrani = page.locator('.pin-klaviatura, .kirish').first()
  const ogoh = page.getByRole('alertdialog', { name: 'Siz hali smenadasiz' })
  await expect(kirishEkrani.or(ogoh)).toBeVisible()
  if (await ogoh.count()) await ogoh.getByRole('button', { name: 'Baribir chiqish' }).click()
  await expect(kirishEkrani).toBeVisible()
  await expect(nav(page)).toHaveCount(0)
  const karta = page.locator('.xodim-karta.rasmli', { hasText: 'Sotuvchi' })
  await expect(karta.locator('img.xodim-foto')).toBeVisible()
  await page.screenshot({ path: 'test-results/profil/kirish-ekrani.png', animations: 'disabled' })
  await karta.click()
  await expect(page.locator('img.pin-foto')).toBeVisible()
  expect(xatolar).toEqual([])
})
