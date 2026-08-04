<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'

import type { CampaignTrendPoint } from '@/features/advertising/types/campaign'
import { init, type ECharts } from '@/shared/charts/echarts'

const props = defineProps<{ rows: CampaignTrendPoint[] }>()
const element = ref<HTMLElement | null>(null)
let chart: ECharts | null = null

async function render(): Promise<void> {
  await nextTick()
  if (!element.value || props.rows.length === 0) {
    chart?.dispose()
    chart = null
    return
  }
  chart ??= init(element.value)
  chart.setOption({
    animationDuration: 350,
    color: ['#547aa5', '#d98f39', '#43a078', '#8b68a9'],
    tooltip: { trigger: 'axis' },
    legend: { top: 4, data: ['展示量', '点击量', '购买量', 'ACoS'] },
    grid: { left: 54, right: 58, top: 48, bottom: 34 },
    xAxis: {
      type: 'category',
      boundaryGap: true,
      data: props.rows.map((row) => row.date.slice(5)),
      axisLabel: { color: '#70757a', interval: Math.max(Math.floor(props.rows.length / 8) - 1, 0) },
    },
    yAxis: [
      { type: 'value', axisLabel: { color: '#70757a' }, splitLine: { lineStyle: { color: '#eceff1' } } },
      { type: 'value', axisLabel: { formatter: '{value}%' }, splitLine: { show: false } },
    ],
    series: [
      { name: '展示量', type: 'bar', data: props.rows.map((row) => row.metrics.impressions), barMaxWidth: 18 },
      { name: '点击量', type: 'line', smooth: true, symbolSize: 5, data: props.rows.map((row) => row.metrics.clicks) },
      { name: '购买量', type: 'line', smooth: true, symbolSize: 5, data: props.rows.map((row) => row.metrics.orders) },
      {
        name: 'ACoS',
        type: 'line',
        smooth: true,
        yAxisIndex: 1,
        symbolSize: 5,
        data: props.rows.map((row) => row.metrics.acos === null ? null : Number(row.metrics.acos) * 100),
      },
    ],
  }, true)
}

function resize(): void { chart?.resize() }
watch(() => props.rows, () => void render(), { deep: true })
onMounted(() => { window.addEventListener('resize', resize); void render() })
onBeforeUnmount(() => { window.removeEventListener('resize', resize); chart?.dispose() })
</script>

<template>
  <div v-if="rows.length" ref="element" class="remote-performance-chart" aria-label="广告活动绩效趋势图" />
  <div v-else class="remote-performance-empty">当前筛选范围暂无趋势数据</div>
</template>

<style scoped>
.remote-performance-chart { width: 100%; height: 300px; }
.remote-performance-empty { height: 300px; display: grid; place-items: center; color: #70757a; }
</style>
