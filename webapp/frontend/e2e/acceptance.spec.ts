// Dashboard acceptance checklist, automated.
import { expect, test, type Page } from '@playwright/test'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'

const snap = (f: string) => JSON.parse(readFileSync(fileURLToPath(new URL(`../public/api-snapshot/${f}`, import.meta.url)), 'utf-8'))
const scenarios: any[] = snap('scenarios.json')
const row = (id: string) => scenarios.find((r) => r.id === id)

const VIEWS = ['campus', 'connection', 'week', 'quantum', 'evidence'] as const

async function open(page: Page, q: string) {
  await page.goto(`/?${q}`)
  await expect(page.getByTestId('banner')).toBeVisible()
}

test('honesty banner is visible on every view', async ({ page }) => {
  for (const v of VIEWS) {
    await open(page, `view=${v}&scenario=R3&hour=10`)
    await expect(page.getByTestId('banner')).toContainText('Synthetic 168-h benchmark')
    await expect(page.getByTestId('banner')).toContainText('no quantum advantage claimed')
  }
})

test('at most five KPI cards on any view, and a citation chip on each', async ({ page }) => {
  for (const v of VIEWS) {
    await open(page, `view=${v}&scenario=R3&hour=10`)
    await page.waitForLoadState('networkidle')
    const n = await page.getByTestId('kpi').count()
    expect(n).toBeLessThanOrEqual(5)
    for (let i = 0; i < n; i++) await expect(page.getByTestId('kpi').nth(i).locator('.cite')).toHaveCount(1)
  }
})

test('every KPI value equals its API field (R3)', async ({ page }) => {
  await open(page, 'view=campus&scenario=R3&hour=10')
  const r = row('R3')
  const kpis = page.getByTestId('kpi')
  await expect(kpis.nth(0)).toContainText(`${r.connection_capacity_MW.toFixed(2)} MW`)
  await expect(kpis.nth(1)).toContainText(`${r.capacity_reduction_pct.toFixed(1)} %`)
  await expect(kpis.nth(2)).toContainText(`${r.violation_energy_MWh.toFixed(2)} MWh`)
  await expect(kpis.nth(3)).toContainText(`${r.operational_CO2_t.toFixed(2)} t`)
  await expect(kpis.nth(4)).toContainText(`${r.jobs_shifted_pct.toFixed(1)} % · ${r.average_workload_delay_h.toFixed(2)} h`)
  await expect(kpis.nth(2)).toHaveClass(/ok/) // zero violation -> green check
})

test('R4 and R5 are labelled as peak import under an imposed envelope', async ({ page }) => {
  for (const s of ['R4', 'R5']) {
    await open(page, `view=campus&scenario=${s}&hour=10`)
    await expect(page.getByTestId('kpi').first()).toContainText('Peak import under the imposed envelope')
    await expect(page.getByTestId('kpi').first()).not.toContainText('Required grid connection')
  }
  await open(page, 'view=campus&scenario=R3&hour=10')
  await expect(page.getByTestId('kpi').first()).toContainText('Required grid connection')
})

test('no map, map tiles or geographic layer anywhere', async ({ page }) => {
  for (const v of VIEWS) {
    await open(page, `view=${v}&scenario=R4&hour=37`)
    await expect(page.locator('[class*="leaflet"], [class*="mapbox"], [class*="maplibre"], img[src*="tile"]')).toHaveCount(0)
  }
})

test('citation chip in the header and under every chart', async ({ page }) => {
  await open(page, 'view=campus&scenario=R4&hour=37')
  await expect(page.locator('.header .cite')).toHaveCount(1)
  for (const v of ['campus', 'connection', 'week'] as const) {
    await open(page, `view=${v}&scenario=R4&hour=37`)
    await page.waitForLoadState('networkidle')
    expect(await page.locator('.caption .cite, h3 .cite').count()).toBeGreaterThan(0)
  }
})

test('clicking a component opens its card with the value of the selected hour', async ({ page }) => {
  const disp = snap('dispatch_R4.json').rows
  await open(page, 'view=campus&scenario=R4&hour=37')
  await page.locator('[data-node="grid"]').click()
  await expect(page.getByTestId('side-value')).toContainText(disp[37].grid_import_MW.toFixed(2))
  await page.getByRole('button', { name: 'When were you limited by the connection envelope or by capacity?' }).click()
  await expect(page.getByTestId('answer')).toContainText('GET /api/components/grid?scenario=R4&hour=37')
})

test('the bus balance residual reads 0.00 MW', async ({ page }) => {
  await open(page, 'view=campus&scenario=R4&hour=37')
  await expect(page.locator('[data-node="bus"]')).toContainText('residual 0.00 MW')
})

test('scenario, view and hour survive a page reload via the URL', async ({ page }) => {
  await open(page, 'view=week&scenario=R5&hour=50')
  await page.reload()
  await expect(page.getByTestId('scenario-R5')).toHaveAttribute('aria-pressed', 'true')
  await expect(page.getByRole('button', { name: 'Week replay' })).toHaveAttribute('aria-current', 'page')
  await expect(page.locator('body')).toContainText('h 50')
  await page.getByTestId('scenario-R2').click()
  await expect(page).toHaveURL(/scenario=R2/)
})

test('capacity bridge values are computed from the API', async ({ page }) => {
  await open(page, 'view=connection&scenario=R3&hour=0')
  const svg = page.locator('svg[aria-label^="Capacity bridge"]')
  await expect(svg).toContainText(`${row('R0').connection_capacity_MW.toFixed(2)} MW`)
  await expect(svg).toContainText(`${row('R3').connection_capacity_MW.toFixed(2)} MW`)
  await expect(svg).toContainText(`−${(row('R0').connection_capacity_MW - row('R1').connection_capacity_MW).toFixed(2)} MW`)
  await expect(page.getByTestId('envelope-R4')).toContainText('6 of 28')
})

test('quantum check shows both depths from the API', async ({ page }) => {
  const q = snap('qaoa.json')
  await open(page, 'view=quantum&scenario=R3&hour=0')
  for (const d of q.depths) await expect(page.locator('body')).toContainText(`${d.feasible_mass_pct.toFixed(2)} %`)
  await expect(page.locator('body')).toContainText('optimum found · gap 0')
})

test('evidence view offers the citation, assumptions and downloads', async ({ page }) => {
  await open(page, 'view=evidence&scenario=R3&hour=0')
  await expect(page.getByTestId('citation')).toContainText('Paper ID 1939')
  await expect(page.getByTestId('assumptions')).toContainText('0.72')
  const href = await page.getByRole('link', { name: /Scenario results/ }).getAttribute('href')
  const res = await page.request.get(href!)
  expect(res.ok()).toBeTruthy()
  expect(await res.text()).toContain('connection_capacity_MW')
})
