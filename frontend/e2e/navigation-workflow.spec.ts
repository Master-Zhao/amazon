import { expect, test, type Page } from '@playwright/test'

const password = process.env.E2E_USER_PASSWORD
if (!password) throw new Error('E2E_USER_PASSWORD was not created by global setup')

async function login(page: Page): Promise<void> {
  await page.goto('/login')
  await page.getByLabel('账号或邮箱').fill('e2e@example.invalid')
  await page.getByLabel('密码', { exact: true }).fill(password!)
  await page.getByRole('button', { name: '登录工作台' }).click()
  await page.waitForURL(/\/advertising\/overview|\/$/)
}

async function selectCompleteContext(page: Page): Promise<void> {
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

test('登录→广告总览→创建广告→通知→帮助→头像菜单→退出登录', async ({
  page,
}) => {
  await login(page)

  await expect(page.getByRole('heading', { name: /欢迎回来/ })).toBeVisible()
  const businessNavigation = page.getByRole('navigation', { name: '业务导航' })
  await businessNavigation
    .getByRole('link', { name: '广告总览', exact: true })
    .click()
  await expect(page.getByRole('heading', { name: '广告总览' })).toBeVisible()

  await page.getByRole('link', { name: '创建广告' }).click()
  await expect(page.getByRole('heading', { name: '创建广告' })).toBeVisible()

  await businessNavigation
    .getByRole('link', { name: '广告总览', exact: true })
    .click()
  await expect(page.getByRole('heading', { name: '广告总览' })).toBeVisible()

  const bellButton = page.getByLabel('通知')
  await bellButton.hover()
  await expect(page.getByText('通知', { exact: true })).toBeVisible()

  await page.getByRole('button', { name: '查看全部通知' }).click()
  await expect(page.getByRole('heading', { name: '通知中心' })).toBeVisible()

  await page.getByLabel('帮助中心').click()
  await expect(page.getByRole('heading', { name: '帮助中心' })).toBeVisible()

  const avatarButton = page.getByLabel('用户菜单')
  await avatarButton.click()
  await expect(page.getByText('退出登录')).toBeVisible()

  await page.getByRole('button', { name: '退出登录' }).click()
  await expect(page.getByRole('heading', { name: '欢迎回来' })).toBeVisible()
})

test('登录页在常用视口保持完整布局且不出现横向溢出', async ({ page }) => {
  const viewports = [
    { width: 1440, height: 900 },
    { width: 1280, height: 720 },
    { width: 768, height: 1024 },
    { width: 390, height: 844 },
  ]

  for (const viewport of viewports) {
    await page.setViewportSize(viewport)
    await page.goto('/login')
    await expect(page.getByRole('heading', { name: '欢迎回来' })).toBeVisible()
    await expect(page.getByLabel('账号或邮箱')).toBeVisible()
    await expect(
      page.getByLabel('密码', { exact: true }),
    ).toBeVisible()
    await expect(
      page.getByRole('button', { name: '登录工作台' }),
    ).toBeVisible()
    await expect(
      page.getByRole('navigation', { name: '业务导航' }),
    ).toHaveCount(0)
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth,
      ),
    ).toBe(true)
  }
})

test('登录表单支持键盘顺序操作', async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 720 })
  await page.goto('/login')

  await page.keyboard.press('Tab')
  await expect(page.getByLabel('账号或邮箱')).toBeFocused()
  await page.keyboard.type('e2e@example.invalid')

  await page.keyboard.press('Tab')
  await expect(page.getByLabel('密码', { exact: true })).toBeFocused()
  await page.keyboard.type('keyboard-check')

  await page.keyboard.press('Tab')
  await expect(
    page.getByRole('button', { name: '显示密码' }),
  ).toBeFocused()
  await page.keyboard.press('Tab')
  await expect(
    page.getByRole('button', { name: '登录工作台' }),
  ).toBeFocused()
})

test('错误凭据可见反馈后允许使用正确凭据重试', async ({ page }) => {
  const pageErrors: string[] = []
  const consoleErrors: string[] = []
  const expectedAuthConsoleDiagnostics: string[] = []
  const failedRequests: string[] = []
  const unexpectedResponses: string[] = []
  page.on('pageerror', (error) => pageErrors.push(error.message))
  page.on('console', (message) => {
    if (message.type() !== 'error') return
    if (
      message
        .text()
        .includes('server responded with a status of 401 (Unauthorized)')
    ) {
      expectedAuthConsoleDiagnostics.push(message.text())
      return
    }
    consoleErrors.push(message.text())
  })
  page.on('requestfailed', (request) => {
    failedRequests.push(
      `${request.url()} ${request.failure()?.errorText ?? 'request failed'}`,
    )
  })
  page.on('response', (response) => {
    if (response.status() < 400) return
    const isExpectedAnonymousRefresh =
      response.status() === 401 && response.url().includes('/auth/refresh')
    const isExpectedInvalidLogin =
      response.status() === 401 && response.url().includes('/auth/login')
    if (!isExpectedAnonymousRefresh && !isExpectedInvalidLogin) {
      unexpectedResponses.push(`${response.status()} ${response.url()}`)
    }
  })

  await page.goto('/login')
  await page.getByLabel('账号或邮箱').fill('e2e@example.invalid')
  await page
    .getByLabel('密码', { exact: true })
    .fill('incorrect-password')
  await page.getByRole('button', { name: '登录工作台' }).click()

  await expect(page.getByRole('alert')).toContainText('账号或密码错误')
  await expect(page).toHaveURL(/\/login$/)

  await page.getByLabel('密码', { exact: true }).fill(password!)
  await page.getByRole('button', { name: '登录工作台' }).click()
  await page.waitForURL(/\/advertising\/overview|\/$/)
  await expect(page.getByRole('heading', { name: /欢迎回来/ })).toBeVisible()
  expect(pageErrors).toEqual([])
  expect(consoleErrors).toEqual([])
  expect(expectedAuthConsoleDiagnostics).toHaveLength(2)
  expect(failedRequests).toEqual([])
  expect(unexpectedResponses).toEqual([])
})

test('刷新后恢复登录状态', async ({ page }) => {
  await login(page)
  await expect(page.getByRole('heading', { name: /欢迎回来/ })).toBeVisible()

  await page.reload()
  await expect(page.getByRole('heading', { name: /欢迎回来/ })).toBeVisible()
})

test('完整上下文进入数据中心并在刷新后保留路由和上下文', async ({
  page,
}) => {
  const routerWarnings: string[] = []
  page.on('console', (message) => {
    if (
      message.type() === 'warning' &&
      message.text().includes('[Vue Router warn]')
    ) {
      routerWarnings.push(message.text())
    }
  })

  await login(page)
  await selectCompleteContext(page)
  await page.getByRole('button', { name: '进入数据中心' }).click()

  await expect(page).toHaveURL(/\/reports\/imports$/)
  await expect(page.getByRole('heading', { name: '数据中心' })).toBeVisible()
  const businessNavigation = page.getByRole('navigation', { name: '业务导航' })
  const dataCenterLink = businessNavigation.getByRole('link', {
    name: '数据中心',
    exact: true,
  })
  const analyticsLink = businessNavigation.getByRole('link', {
    name: '广告分析',
    exact: true,
  })
  await expect(dataCenterLink).toHaveClass(/router-link-active/)
  await expect(analyticsLink).not.toHaveClass(/router-link-active/)

  await page.reload()
  await expect(page).toHaveURL(/\/reports\/imports$/)
  await expect(page.getByRole('heading', { name: '数据中心' })).toBeVisible()
  await expect(page.getByLabel('Campaign report file')).toBeVisible()
  await expect(dataCenterLink).toHaveClass(/router-link-active/)

  await page.goto('/reports')
  await expect(page).toHaveURL(/\/reports\/imports$/)
  await expect(page.getByRole('heading', { name: '数据中心' })).toBeVisible()

  await analyticsLink.click()
  await expect(page).toHaveURL(/\/dashboard$/)
  await expect(page.getByRole('heading', { name: '广告工作台' })).toBeVisible()
  await expect(analyticsLink).toHaveClass(/router-link-active/)
  await expect(dataCenterLink).not.toHaveClass(/router-link-active/)
  expect(routerWarnings).toEqual([])
})

test('完整上下文进入常见问题详情并支持刷新、前进后退和返回', async ({
  page,
}) => {
  const browserErrors: string[] = []
  const failedApiResponses: string[] = []
  const failedRequests: string[] = []

  await login(page)
  await selectCompleteContext(page)
  page.on('console', (message) => {
    if (
      message.type() === 'error' ||
      (message.type() === 'warning' &&
        message.text().includes('[Vue Router warn]'))
    ) {
      browserErrors.push(message.text())
    }
  })
  page.on('response', (response) => {
    if (
      response.url().includes('/api/') &&
      response.status() >= 400
    ) {
      failedApiResponses.push(`${response.status()} ${response.url()}`)
    }
  })
  page.on('requestfailed', (request) => {
    failedRequests.push(
      `${request.url()} ${request.failure()?.errorText ?? 'request failed'}`,
    )
  })
  const selectedContext = await page.evaluate(() =>
    localStorage.getItem('amazon-ads-context-v1'),
  )
  expect(selectedContext).not.toBeNull()

  await page.getByLabel('帮助中心').click()
  await expect(page).toHaveURL(/\/help$/)
  await expect(page.getByRole('heading', { name: '帮助中心' })).toBeVisible()

  const faqNavigation = page.getByRole('navigation', { name: '常见问题' })
  const firstFaq = faqNavigation.getByRole('link').first()
  const firstTitle = (await firstFaq.locator('strong').textContent())?.trim()
  const firstHref = await firstFaq.getAttribute('href')
  expect(firstTitle).toBeTruthy()
  expect(firstHref).toMatch(/^\/help\/faq\/[a-z0-9-]+$/)

  await firstFaq.click()
  await expect(page).toHaveURL(new RegExp(`${firstHref}$`))
  await expect(
    page.getByRole('heading', { name: firstTitle!, exact: true }),
  ).toBeVisible()
  await expect(page.locator('.help-answer-body')).not.toBeEmpty()
  await expect(page).toHaveTitle(
    new RegExp(`${firstTitle} · 帮助中心 · Amazon Ads Optimizer`),
  )

  await page.reload()
  await expect(page).toHaveURL(new RegExp(`${firstHref}$`))
  await expect(
    page.getByRole('heading', { name: firstTitle!, exact: true }),
  ).toBeVisible()

  await page.goBack()
  await expect(page).toHaveURL(/\/help$/)
  await page.goForward()
  await expect(page).toHaveURL(new RegExp(`${firstHref}$`))
  await expect(
    page.getByRole('heading', { name: firstTitle!, exact: true }),
  ).toBeVisible()

  await page.getByRole('link', { name: '返回帮助中心' }).click()
  await expect(page).toHaveURL(/\/help$/)
  await expect(faqNavigation.getByRole('link')).not.toHaveCount(0)
  expect(
    await page.evaluate(() =>
      localStorage.getItem('amazon-ads-context-v1'),
    ),
  ).toBe(selectedContext)

  await page.goto('/context')
  await expect(page.getByText('上下文已就绪')).toBeVisible()
  expect(browserErrors).toEqual([])
  expect(failedApiResponses).toEqual([])
  expect(failedRequests).toEqual([])
})

test('目录路径逐级跳转', async ({ page }) => {
  await login(page)

  await page.goto('/advertising/overview')
  await expect(page.getByRole('heading', { name: '广告总览' })).toBeVisible()

  const breadcrumb = page.locator('.directory-breadcrumb')
  await expect(breadcrumb).toBeVisible()
  await expect(breadcrumb.getByText('advertising')).toBeVisible()
  await expect(breadcrumb.getByText('overview')).toBeVisible()

  await breadcrumb.getByText('advertising').click()
  await expect(page).toHaveURL(/\/advertising$/)

  await breadcrumb.locator('.breadcrumb-home').click()
  await expect(page).toHaveURL(/\/$/)
})
