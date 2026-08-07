import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, vi } from 'vitest'

import ReportCenterPage from '@/features/reports/pages/ReportCenterPage.vue'
import { useTenantContextStore } from '@/features/tenant-context/stores/context'

const { tasksMock, taskMock, uploadMock } = vi.hoisted(() => ({
  tasksMock: vi.fn(),
  taskMock: vi.fn(),
  uploadMock: vi.fn(),
}))

vi.mock('@/features/reports/api/reportApi', () => ({
  fetchImportTasks: tasksMock,
  fetchImportTask: taskMock,
  fetchImportErrors: vi.fn(),
  uploadReport: uploadMock,
  reprocessImport: vi.fn(),
  downloadImportSource: vi.fn(),
}))

describe('Report center page', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    setActivePinia(createPinia())
    useTenantContextStore().$patch({
      selectedTenantId: 'tenant-1',
      selectedStoreId: 'store-1',
      selectedStoreMarketplaceId: 'store-market-1',
      selectedProfileId: 'profile-1',
    })
  })

  it('renders historical import tasks sourced from report_import_task + report_upload', async () => {
    tasksMock.mockResolvedValue([
      {
        taskId: 'task-1',
        originalName: 'campaign-report-2026-08-07.csv',
        reportType: 'CAMPAIGN',
        status: 'SUCCEEDED',
        failedRows: 0,
      },
      {
        taskId: 'task-2',
        originalName: 'targeting-report-2026-08-07.csv',
        reportType: 'TARGETING',
        status: 'PARTIAL_SUCCEEDED',
        failedRows: 3,
      },
    ])

    const wrapper = mount(ReportCenterPage)
    await flushPromises()

    const tableText = wrapper.find('table').text()
    expect(tableText).toContain('campaign-report-2026-08-07.csv')
    expect(tableText).toContain('CAMPAIGN')
    expect(tableText).toContain('SUCCEEDED')
    expect(tableText).toContain('targeting-report-2026-08-07.csv')
    expect(tableText).toContain('TARGETING')
    expect(tableText).toContain('PARTIAL_SUCCEEDED')
    expect(tableText).toContain('3')
  })

  it('uploads a report and renders the created import task detail', async () => {
    tasksMock.mockResolvedValue([
      {
        taskId: 'task-1',
        originalName: 'campaign-report-2026-08-07.csv',
        reportType: 'CAMPAIGN',
        status: 'SUCCEEDED',
        failedRows: 0,
      },
    ])
    uploadMock.mockResolvedValue({ taskId: 'task-new' })
    taskMock.mockResolvedValue({
      taskId: 'task-new',
      status: 'RUNNING',
      isDuplicate: false,
      batch: {
        totalRows: 10,
        succeededRows: 8,
        failedRows: 2,
        errors: [
          { rowNumber: 3, field: 'spend', code: 'ROW_VALIDATION_ERROR' },
        ],
      },
    })

    const wrapper = mount(ReportCenterPage)
    await flushPromises()

    const file = new File(['csv,content'], 'campaign-upload.csv', {
      type: 'text/csv',
    })
    const fileInput = wrapper.find('input[type="file"]')
    Object.defineProperty(fileInput.element, 'files', {
      value: [file],
      configurable: true,
    })
    await fileInput.trigger('change')
    await wrapper.find('form.context-grid').trigger('submit')
    await flushPromises()

    expect(uploadMock).toHaveBeenCalledWith({
      tenantId: 'tenant-1',
      profileId: 'profile-1',
      reportType: 'CAMPAIGN',
      file,
    })
    expect(taskMock).toHaveBeenCalledWith('task-new')
    expect(wrapper.text()).toContain('任务 task-new')
    expect(wrapper.text()).toContain('状态：RUNNING')
    expect(wrapper.text()).toContain('总行 10，成功 8，失败 2')
    expect(wrapper.text()).toContain('第 3 行 · spend · ROW_VALIDATION_ERROR')
  })

  it('renders a failure banner when the task list cannot be loaded', async () => {
    tasksMock.mockRejectedValue(new Error('forbidden'))
    const wrapper = mount(ReportCenterPage)
    await flushPromises()
    expect(wrapper.text()).toContain('导入任务列表加载失败或当前账号无权限')
  })

  it('does not attempt to load history without a selected profile', async () => {
    useTenantContextStore().$patch({ selectedProfileId: null })
    const wrapper = mount(ReportCenterPage)
    await flushPromises()
    expect(tasksMock).not.toHaveBeenCalled()
    expect(wrapper.text()).toContain('请先在卖家空间页选择 Advertising Profile。')
  })
})
