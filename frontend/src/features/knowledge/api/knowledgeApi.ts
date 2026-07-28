import { httpClient } from '@/shared/api/httpClient'
import type { ApiEnvelope } from '@/shared/api/types'

export interface KnowledgeCategory {
  code: string
  name: string
  articles: Array<{ id: string; slug: string; title: string; body: string }>
}

export async function fetchKnowledge(): Promise<KnowledgeCategory[]> {
  const response = await httpClient.get<
    ApiEnvelope<{ categories: KnowledgeCategory[] }>
  >('/api/v1/knowledge/')
  return response.data.data.categories
}
