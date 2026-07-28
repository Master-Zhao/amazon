<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'

import {
  createAnomalyRuleVersion,
  fetchAnalyticsConfiguration,
  updateTargetAcos,
  type AnalyticsConfiguration,
} from '@/features/analytics/api/analyticsApi'
import { useTenantContextStore } from '@/features/tenant-context/stores/tenantContext'
import { normalizeApiError } from '@/shared/api/httpClient'

const context = useTenantContextStore()
const configuration = ref<AnalyticsConfiguration | null>(null)
const loading = ref(false)
const saving = ref(false)
const errorMessage = ref<string | null>(null)
const successMessage = ref<string | null>(null)

const targetScope = ref<'TENANT' | 'PROFILE' | 'CAMPAIGN'>('PROFILE')
const targetCampaignId = ref('')
const targetAcos = ref('')
const ruleCode = ref('HIGH_ACOS')
const ruleScope = ref<'TENANT' | 'PROFILE' | 'CAMPAIGN'>('PROFILE')
const ruleCampaignId = ref('')
const ruleConfiguration = ref('{"minimum_clicks": 10, "minimum_sales": "0.01"}')

const campaigns = computed(() => configuration.value?.campaigns ?? [])

async function refresh(): Promise<void> {
  if (!context.tenantId || !context.profileId) {
    configuration.value = null
    return
  }
  loading.value = true
  errorMessage.value = null
  try {
    configuration.value = await fetchAnalyticsConfiguration(
      context.tenantId,
      context.profileId,
    )
  } catch (error) {
    errorMessage.value = normalizeApiError(error).message
  } finally {
    loading.value = false
  }
}

async function saveTarget(): Promise<void> {
  if (!context.tenantId || !context.profileId) return
  saving.value = true
  errorMessage.value = null
  successMessage.value = null
  try {
    configuration.value = await updateTargetAcos(
      context.tenantId,
      context.profileId,
      {
        scopeType: targetScope.value,
        ...(targetScope.value === 'CAMPAIGN'
          ? { campaignId: targetCampaignId.value }
          : {}),
        targetAcos: targetAcos.value || null,
      },
    )
    successMessage.value = '目标 ACOS 已保存并写入审计。'
  } catch (error) {
    errorMessage.value = normalizeApiError(error).message
  } finally {
    saving.value = false
  }
}

async function saveRule(): Promise<void> {
  if (!context.tenantId || !context.profileId) return
  saving.value = true
  errorMessage.value = null
  successMessage.value = null
  try {
    const parsed = JSON.parse(ruleConfiguration.value) as Record<
      string,
      string | number
    >
    await createAnomalyRuleVersion(context.tenantId, context.profileId, {
      code: ruleCode.value,
      scopeType: ruleScope.value,
      ...(ruleScope.value === 'CAMPAIGN'
        ? { campaignId: ruleCampaignId.value }
        : {}),
      configuration: parsed,
    })
    await refresh()
    successMessage.value = '新规则版本已追加，旧版本仍保留。'
  } catch (error) {
    errorMessage.value =
      error instanceof SyntaxError
        ? '规则配置必须是有效 JSON。'
        : normalizeApiError(error).message
  } finally {
    saving.value = false
  }
}

watch(
  () => [context.tenantId, context.profileId],
  () => void refresh(),
)
onMounted(async () => {
  if (context.status === 'idle') await context.initialize()
  await refresh()
})
</script>

<template>
  <section class="report-page">
    <header class="report-heading">
      <div>
        <p class="eyebrow">DETERMINISTIC RULE CONFIGURATION</p>
        <h2>目标 ACOS 与异常规则</h2>
        <p>配置按 Tenant → Profile → Campaign 逐层覆盖；规则每次保存都追加新版本并进入审计。</p>
      </div>
      <button type="button" :disabled="loading" @click="refresh">
        {{ loading ? '加载中…' : '刷新' }}
      </button>
    </header>

    <div v-if="!context.isComplete" class="empty-panel">请先完成上下文选择。</div>
    <template v-else>
      <div v-if="errorMessage" class="error-panel" role="alert">{{ errorMessage }}</div>
      <p v-if="successMessage" class="success-panel" role="status">{{ successMessage }}</p>

      <div class="context-grid">
        <form class="context-card" @submit.prevent="saveTarget">
          <h3>目标 ACOS</h3>
          <label>
            范围
            <select v-model="targetScope">
              <option value="TENANT">Tenant</option>
              <option value="PROFILE">Profile</option>
              <option value="CAMPAIGN">Campaign</option>
            </select>
          </label>
          <label v-if="targetScope === 'CAMPAIGN'">
            Campaign
            <select v-model="targetCampaignId" required>
              <option value="" disabled>请选择</option>
              <option v-for="item in campaigns" :key="item.campaignId" :value="item.campaignId">
                {{ item.campaignName }}
              </option>
            </select>
          </label>
          <label>
            目标值（如 0.28；留空清除本层）
            <input v-model="targetAcos" inputmode="decimal">
          </label>
          <button type="submit" :disabled="saving">保存目标</button>
        </form>

        <form class="context-card" @submit.prevent="saveRule">
          <h3>追加规则版本</h3>
          <label>
            规则
            <select v-model="ruleCode">
              <option value="HIGH_ACOS">HIGH_ACOS</option>
              <option value="HIGH_SPEND_NO_ORDERS">HIGH_SPEND_NO_ORDERS</option>
              <option value="HIGH_CLICKS_LOW_CONVERSION">HIGH_CLICKS_LOW_CONVERSION</option>
              <option value="BUDGET_EARLY_EXHAUSTION">BUDGET_EARLY_EXHAUSTION</option>
              <option value="LOW_IMPRESSIONS">LOW_IMPRESSIONS</option>
              <option value="LOW_CLICKS">LOW_CLICKS</option>
            </select>
          </label>
          <label>
            范围
            <select v-model="ruleScope">
              <option value="TENANT">Tenant</option>
              <option value="PROFILE">Profile</option>
              <option value="CAMPAIGN">Campaign</option>
            </select>
          </label>
          <label v-if="ruleScope === 'CAMPAIGN'">
            Campaign
            <select v-model="ruleCampaignId" required>
              <option value="" disabled>请选择</option>
              <option v-for="item in campaigns" :key="item.campaignId" :value="item.campaignId">
                {{ item.campaignName }}
              </option>
            </select>
          </label>
          <label>
            JSON 配置
            <textarea v-model="ruleConfiguration" rows="4" />
          </label>
          <button type="submit" :disabled="saving">追加版本</button>
        </form>
      </div>

      <div v-if="configuration" class="metric-cards">
        <article class="metric-card">
          <h3>当前目标</h3>
          <p>Tenant：{{ configuration.tenantTargetAcos ?? '未配置' }}</p>
          <p>Profile：{{ configuration.profileTargetAcos ?? '继承 Tenant' }}</p>
          <ul>
            <li v-for="item in campaigns" :key="item.campaignId">
              {{ item.campaignName }}：{{ item.targetAcos ?? '继承' }}（有效 {{ item.effectiveTargetAcos ?? '无' }}）
            </li>
          </ul>
        </article>
        <article class="metric-card">
          <h3>当前最新规则版本</h3>
          <p v-if="configuration.rules.length === 0">尚无已发布规则。</p>
          <ul v-else>
            <li v-for="rule in configuration.rules" :key="rule.id">
              {{ rule.scopeKey }} · {{ rule.code }} · v{{ rule.version }}
            </li>
          </ul>
        </article>
      </div>
    </template>
  </section>
</template>
