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
  // standart tab — «Faol» (ish davom etayotganlar): soni jadval qatorlariga teng (50 dan ko'p bo'lsa — birinchi sahifa)
  const faol = page.getByRole('tab', { name: /^Faol/ })
  await expect(faol).toHaveAttribute('aria-selected', 'true')
  const faolSoni = Number(await faol.locator('.tab-son').innerText())
  await expect(qatorlar).toHaveCount(Math.min(faolSoni, 50))
  // bekor qilinmagan zakazda «qachon?» javobi bor
  await expect(page.locator('.zakaz-jadval .muddat').first()).toHaveText(/kun qoldi|olib ketadi|qaytaradi|kechikdi|mijozda/)
  await expect(page.locator('.ijara-sana').first()).toBeVisible()
  await suratlar(page, '1-royxat')

  // «Hammasi» — oxirgi tab; 50 tadan sahifalanadi, «Yana» bilan barcha zakazlarga yetib boriladi
  const hammasi = page.getByRole('tab', { name: /^Hammasi/ })
  await expect(page.getByRole('tab').last()).toHaveText(/^Hammasi/)
  await hammasi.click()
  const jami = Number(await hammasi.locator('.tab-son').innerText())
  await expect(qatorlar).toHaveCount(Math.min(jami, 50))
  const yana = page.locator('.jadval-yana')
  while (await qatorlar.count() < jami) {
    const oldin = await qatorlar.count()
    await expect(yana).toContainText(`${oldin} / ${jami} ko'rsatildi`)
    await yana.getByRole('button', { name: /^Yana \d+ ta$/ }).click()
    await expect(qatorlar).toHaveCount(Math.min(oldin + 50, jami))
  }
  await expect(yana).toHaveCount(0)

  // raqam bo'yicha qidiruv: aniq zakaz birinchi qatorda (telefon raqamlari bilan aralashmaydi)
  const raqam = (await qatorlar.last().locator('.zakaz-nom b').innerText()).match(/#(\d+)/)[1]
  await page.locator('.jadval-qidiruv').fill(raqam)
  await expect(qatorlar.first().locator('.zakaz-nom b')).toHaveText(new RegExp(`^#${raqam} `))
  await page.locator('.jadval-qidiruv').fill('')

  await page.getByRole('tab', { name: /^Bekor/ }).click()
  await expect(qatorlar.first()).toContainText('Bekor')
  await expect(qatorlar.locator('.muddat')).toHaveCount(0)  // bekor zakazda muddat yo'q
  await page.locator('.jadval-qidiruv').fill('yoqmijoz')
  await expect(page.getByText("«yoqmijoz» bo'yicha zakaz topilmadi.")).toBeVisible()
  expect(xatolar).toEqual([])
})
