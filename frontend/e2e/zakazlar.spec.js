// «Zakazlar» ro'yxati: holat tablari sonlari bilan (standart «Faol», «Hammasi» oxirida), 50 talik sahifalar,
// ijara sanasi va «qachon?» belgisi (N kun qoldi / kechikdi), raqam bo'yicha qidiruvda aniq zakaz birinchi.
// Keng ekranda va telefonda suratga olinadi (test-results/zakazlar/*.png).
import { expect, test } from '@playwright/test'
import { kirish, xatolarniKuzat } from './yordam.js'

const nav = (page) => page.getByRole('navigation', { name: "Bo'limlar" })
const TELEFON = { width: 390, height: 844 }
const KENG = { width: 1280, height: 860 }

async function suratlar(page, nom) {
  await page.waitForLoadState('networkidle')
  await page.screenshot({ path: `test-results/zakazlar/${nom}-keng.png`, fullPage: true, animations: 'disabled' })
  await page.setViewportSize(TELEFON)
  await page.waitForTimeout(400)
  await page.screenshot({ path: `test-results/zakazlar/${nom}-telefon.png`, fullPage: true, animations: 'disabled' })
  const [kenglik, ekran] = await page.evaluate(() => [document.documentElement.scrollWidth, window.innerWidth])
  expect(kenglik, `${nom}: telefonda sahifa gorizontal surilmasin`).toBeLessThanOrEqual(ekran)
  await page.setViewportSize(KENG)
}

test("zakazlar: ro'yxat — sonli tablar, ijara sanasi va muddat", async ({ page }) => {
  const xatolar = xatolarniKuzat(page)
  await kirish(page, 'Rahbar', '1111')
  await nav(page).getByRole('button', { name: 'Zakazlar', exact: true }).click()
  const qatorlar = page.locator('.zakaz-jadval tbody tr')
  await expect(qatorlar.first()).toBeVisible()
  // standart tab — «Faol» (ish davom etayotganlar): soni jadval qatorlariga teng (20 dan ko'p bo'lsa — birinchi sahifa)
  const faol = page.getByRole('tab', { name: /^Faol/ })
  await expect(faol).toHaveAttribute('aria-selected', 'true')
  const faolSoni = Number(await faol.locator('.tab-son').innerText())
  await expect(qatorlar).toHaveCount(Math.min(faolSoni, 20))
  // bekor qilinmagan zakazda «qachon?» javobi bor
  await expect(page.locator('.zakaz-jadval .muddat').first()).toHaveText(/kun qoldi|olib ketadi|qaytaradi|kechikdi|mijozda/)
  await expect(page.locator('.ijara-sana').first()).toBeVisible()
  await suratlar(page, '1-royxat')

  // «Hammasi» — oxirgi tab; 20 tadan raqamli sahifalar, oxirgi sahifada qolgan zakazlar (Ndiz)
  const hammasi = page.getByRole('tab', { name: /^Hammasi/ })
  await expect(page.getByRole('tab').last()).toHaveText(/^Hammasi/)
  await hammasi.click()
  const jami = Number(await hammasi.locator('.tab-son').innerText())
  await expect(qatorlar).toHaveCount(Math.min(jami, 20))
  const sahifalar = Math.ceil(jami / 20)
  const sahifaNav = page.getByRole('navigation', { name: 'Sahifalar' })
  if (sahifalar > 1) {
    await expect(sahifaNav).toContainText(`${jami} tadan 1–20`)
    await sahifaNav.getByRole('button', { name: `${sahifalar}-sahifa` }).click()
    await expect(qatorlar).toHaveCount(jami - (sahifalar - 1) * 20)
    await expect(sahifaNav.getByRole('button', { name: `${sahifalar}-sahifa` })).toHaveAttribute('aria-current', 'page')
  } else {
    await expect(sahifaNav).toHaveCount(0)
  }

  // raqam bo'yicha qidiruv: aniq zakaz birinchi qatorda (telefon raqamlari bilan aralashmaydi)
  const raqam = (await qatorlar.last().locator('.zakaz-nom b').innerText()).match(/#(\d+)/)[1]
  await page.locator('.jadval-qidiruv').fill(raqam)
  // kanvas ustuni: «#raqam» alohida, libos nomi ostida — raqam aniq mos kelishi kerak (#1 va #10 aralashmasin)
  await expect(qatorlar.first().locator('.zakaz-nom b')).toHaveText(new RegExp(`^#${raqam}$`))
  await page.locator('.jadval-qidiruv').fill('')

  await page.getByRole('tab', { name: /^Bekor/ }).click()
  await expect(qatorlar.first()).toContainText('Bekor')
  await expect(qatorlar.locator('.muddat')).toHaveCount(0)  // bekor zakazda muddat yo'q
  await page.locator('.jadval-qidiruv').fill('yoqmijoz')
  await expect(page.getByText("«yoqmijoz» bo'yicha zakaz topilmadi.")).toBeVisible()
  expect(xatolar).toEqual([])
})
