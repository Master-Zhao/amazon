import { expect, test, type Page } from '@playwright/test'
import { fileURLToPath, URL } from 'node:url'

const campaignFixture = fileURLToPath(
  new URL('../../tests/fixtures/reports/campaign-anomalous.csv', import.meta.url),
)
const partialFixture = fileURLToPath(
  new URL(
    '../../tests/fixtures/reports/campaign-partial-errors.csv',
    import.meta.url,
  ),
)
const password = process.env.E2E_USER_PASSWORD
if (!password) throw new Error('E2E_USER_PASSWORD was not created by global setup')

async function login(page: Page): Promise<void> {
  await page.goto('/login')
  await page.getByLabel('邮箱').fill('e2e@example.invalid')
  await page.getByLabel('密码', { exact: true }).fill(password!)
  await page.getByRole('button', { name: '登录工作台' }).click()
  await page.waitForURL(/\/advertising\/overview|\/$/)
  await expect(page.getByRole('heading', { name: /欢迎回来/ })).toBeVisible()
}

async function selectContext(page: Page): Promise<void> {
  await page
    .getByRole('navigation', { name: '业务导航' })
    .getByRole('link', { name: '卖家空间', exact: true })
    .click()
  const contextSelects = page.locator('select')
  await expect(contextSelects).toHaveCount(4)
  for (let index = 0; index < 4; index += 1) {
    await expect
      .poll(() => contextSelects.nth(index).locator('option').count())
      .toBeGreaterThan(1)
    await contextSelects.nth(index).selectOption({ index: 1 })
  }
  await expect(page.getByText('上下文已就绪')).toBeVisible()
}

test('Campaign 导入、异常、Mock 分析到人工执行与审计的真实闭环', async ({
  page,
}) => {
  await login(page)
  await page.reload()
  await expect(page.getByRole('heading', { name: /欢迎回来/ })).toBeVisible()
  await selectContext(page)

  await page.getByRole('link', { name: '数据中心' }).click()
  await page.getByLabel('Campaign report file').setInputFiles(campaignFixture)
  await page.getByRole('button', { name: '上传并异步导入' }).click()
  await expect(page.getByRole('cell', { name: 'SUCCEEDED' }).first()).toBeVisible()

  await page.getByRole('link', { name: '广告分析' }).click()
  await page.getByRole('link', { name: 'Campaign 指标' }).click()
  await expect(page.getByText('High ACOS Campaign')).toBeVisible()
  await expect(page.getByText(/ANOMALY/).first()).toBeVisible()

  await page.getByRole('link', { name: '智能优化' }).click()
  await page.getByRole('button', { name: '运行 Mock 智能分析' }).click()
  await expect(page.getByText('SUCCEEDED').first()).toBeVisible()
  await expect(page.getByText(/UPDATE_CAMPAIGN_BUDGET/).first()).toBeVisible()
  await page.getByRole('button', { name: '生成 Action Preview' }).first().click()
  await expect(page.getByRole('button', { name: /已创建 Preview/ })).toBeDisabled()

  await page.getByRole('link', { name: '审批执行' }).click()
  await page.getByRole('button', { name: '提交审批' }).first().click()
  await page.getByRole('button', { name: '批准' }).first().click()
  await page.getByRole('button', { name: '回填人工执行成功' }).first().click()
  await expect(page.getByText(/SUCCEEDED ·/).first()).toBeVisible()

  await page.getByRole('link', { name: '系统管理' }).click()
  await page.getByRole('link', { name: '审计日志' }).click()
  await expect(page.getByText('action_preview.execution_recorded')).toBeVisible()
})

test('Campaign 部分错误导入可查询任务与行级错误并正常退出', async ({
  page,
}) => {
  await login(page)
  await selectContext(page)
  await page.getByRole('link', { name: '数据中心' }).click()

  await page.getByLabel('Campaign report file').setInputFiles(partialFixture)
  await page.getByRole('button', { name: '上传并异步导入' }).click()
  const partialRow = page.getByRole('row').filter({
    has: page.getByText('campaign-partial-errors.csv'),
  })
  await expect(partialRow.getByText('PARTIAL_SUCCEEDED')).toBeVisible()
  await partialRow.getByRole('button', { name: '错误明细' }).click()
  await expect(page.getByRole('heading', { name: /错误明细/ })).toBeVisible()
  await expect(page.getByRole('cell', { name: 'ROW_VALIDATION_ERROR' }).first()).toBeVisible()

  await page.getByLabel('用户菜单').click()
  await page.getByRole('button', { name: '退出登录' }).click()
  await expect(page.getByRole('heading', { name: '欢迎回来' })).toBeVisible()
})
