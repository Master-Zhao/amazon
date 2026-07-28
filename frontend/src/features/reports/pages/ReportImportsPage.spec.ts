import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, vi } from 'vitest'

import {
  fetchImportErrors,
  fetchImportTasks,
} from '@/features/reports/api/reportApi'
import ReportImportsPage from '@/features/reports/pages/ReportImportsPage.vue'
import { useTenantContextStore } from '@/features/tenant-context/stores/tenantContext'

vi.mock('@/features/reports/api/reportApi', () => ({
  fetchImportTasks: vi.fn(),
  fetchImportErrors: vi.fn(),
  downloadImportSource: vi.fn(),
  uploadReport: vi.fn(),
  reprocessImport: vi.fn(),
}))

const taskMock = vi.mocked(fetchImportTasks)
const errorMock = vi.mocked(fetchImportErrors)

describe('Campaign report imports page', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    const pinia = createPinia()
    setActivePinia(pinia)
    const context = useTenantContextStore()
    context.$patch({
      tenantId: 'tenant-1',
      storeId: 'store-1',
      storeMarketplaceId: 'store-market-1',
      profileId: 'profile-1',
      status: 'ready',
      membershipRole: 'OWNER',
      permissionCodes: ['reports.view', 'reports.upload'],
      tenants: [
        {
          id: 'tenant-1',
          name: 'Demo Tenant',
          tenantType: 'TEAM',
          membershipRole: 'OWNER',
        },
      ],
      stores: [
        { id: 'store-1', name: 'Demo Store', externalStoreId: 'demo-store' },
      ],
      marketplaces: [
        {
          storeMarketplaceId: 'store-market-1',
          marketplace: {
            id: 'market-1',
            code: 'US',
            name: 'United States',
            currencyCode: 'USD',
            timezone: 'America/Los_Angeles',
          },
        },
      ],
      profiles: [
        {
          id: 'profile-1',
          name: 'Demo Profile',
          externalProfileId: 'demo-profile-001',
          currencyCode: 'USD',
          timezone: 'America/Los_Angeles',
          accessLevel: 'MANAGE',
        },
      ],
    })
  })

  it('renders server task state and row error details', async () => {
    taskMock.mockResolvedValue([
      {
        id: 'task-1',
        status: 'PARTIAL_SUCCEEDED',
        celeryTaskId: 'celery-1',
        totalRows: 2,
        successRows: 1,
        errorRows: 1,
        errorCode: '',
        errorMessage: '',
        reprocessedFromId: null,
        createdAt: '2026-07-28T12:00:00Z',
        startedAt: '2026-07-28T12:00:01Z',
        finishedAt: '2026-07-28T12:00:02Z',
        upload: {
          id: 'upload-1',
          reportType: 'CAMPAIGN',
          originalFilename: 'campaign-partial-errors.csv',
          contentType: 'text/csv',
          sizeBytes: 100,
          sha256: 'abc',
          duplicateOfId: null,
          createdAt: '2026-07-28T12:00:00Z',
        },
      },
    ])
    errorMock.mockResolvedValue([
      {
        id: 'error-1',
        rowNumber: 3,
        errorCode: 'ROW_VALIDATION_ERROR',
        message: 'spend must be a decimal',
        fieldName: 'spend',
        rejectedValue: '',
        createdAt: '2026-07-28T12:00:02Z',
      },
    ])

    const wrapper = mount(ReportImportsPage, {
      global: {
        stubs: { RouterLink: { template: '<a><slot /></a>' } },
      },
    })
    await flushPromises()

    expect(wrapper.text()).toContain('campaign-partial-errors.csv')
    expect(wrapper.text()).toContain('PARTIAL_SUCCEEDED')
    await wrapper.get('button').trigger('click')
    await flushPromises()
    const detailButton = wrapper
      .findAll('button')
      .find((button) => button.text().includes('错误明细'))
    await detailButton?.trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('ROW_VALIDATION_ERROR')
    expect(wrapper.text()).toContain('spend must be a decimal')
  })
})
