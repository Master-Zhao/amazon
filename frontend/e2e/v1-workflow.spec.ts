import { expect, test } from '@playwright/test'
import { fileURLToPath, URL } from 'node:url'

const campaignFixture = fileURLToPath(
  new URL('../../tests/fixtures/reports/campaign-anomalous.csv', import.meta.url),
)
const password = process.env.E2E_USER_PASSWORD
if (!password) throw new Error('E2E_USER_PASSWORD was not created by global setup')

test('Campaign 报表到人工执行回填的真实 V1 闭环', async ({ page }) => {
  await page.goto('/login')
  await page.getByLabel('邮箱').fill('e2e@example.invalid')
  await page.getByLabel('密码').fill(password)
  await page.getByRole('button', { name: '登录' }).click()

  await expect(page.getByRole('heading', { name: /欢迎回来/ })).toBeVisible()
  await page.reload()
  await expect(page.getByRole('heading', { name: /欢迎回来/ })).toBeVisible()

  await page.getByRole('link', { name: '选择卖家空间' }).click()
  const contextSelects = page.locator('select')
  await expect(contextSelects).toHaveCount(4)
  for (let index = 0; index < 4; index += 1) {
    await expect
      .poll(() => contextSelects.nth(index).locator('option').count())
      .toBeGreaterThan(1)
    await contextSelects.nth(index).selectOption({ index: 1 })
  }

  await expect(page.getByRole('link', { name: '数据中心' })).toBeVisible()
  await page.getByRole('link', { name: '数据中心' }).click()

  await page.getByLabel('CSV / XLSX 文件').setInputFiles(campaignFixture)
  await page.getByRole('button', { name: '上传并异步导入' }).click()
  await expect(page.getByText(/状态：SUCCEEDED/)).toBeVisible()
  await expect(page.getByRole('cell', { name: 'SUCCEEDED' })).toBeVisible()

  await page.getByRole('link', { name: '广告分析' }).click()
  await expect(page.getByText(/High ACOS Campaign/)).toBeVisible()
  await expect(page.getByText('异常')).toBeVisible()

  await page.getByRole('link', { name: '智能优化' }).click()
  await page.getByRole('button', { name: '运行四 Agent 分析' }).click()
  await expect(page.getByText(/分析状态：SUCCEEDED；Agent 数：4/)).toBeVisible()
  await expect(page.getByText(/UPDATE_CAMPAIGN_BUDGET/).first()).toBeVisible()

  await page.locator('input[type="checkbox"]').first().check()
  await page.getByRole('button', { name: '冻结版本并提交审批' }).click()
  await expect(page.getByText(/状态：PENDING_APPROVAL/)).toBeVisible()
  await page.getByRole('button', { name: '审批通过' }).click()
  await expect(page.getByText(/状态：APPROVED/)).toBeVisible()

  await page.getByRole('link', { name: '审批执行' }).click()
  await expect(page.getByText(/APPROVED · 版本 1 · 已冻结/)).toBeVisible()
  await page.getByRole('button', { name: '确认成功' }).first().click()
  await expect(page.getByText(/UPDATE_CAMPAIGN_BUDGET · SUCCEEDED/)).toBeVisible()

  await page.goto('/audit')
  await expect(page.getByText('EXECUTION_RECORDED')).toBeVisible()
  await page.getByRole('button', { name: '退出登录' }).click()
  await expect(page.getByRole('heading', { name: '登录广告优化工作台' })).toBeVisible()
})
