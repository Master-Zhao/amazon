import { httpClient } from '@/shared/api/httpClient'
import type { ApiEnvelope } from '@/shared/api/types'

export interface KnowledgeCategory {
  code: string
  name: string
  description: string
  sortOrder: number
}

export interface KnowledgeArticle {
  slug: string
  title: string
  summary: string
  categoryCode: string
  categoryName: string
  sortOrder: number
  updatedAt: string
  body?: string
  contentHash?: string
}

async function data<T>(request: Promise<{ data: ApiEnvelope<T> }>): Promise<T> {
  return (await request).data.data
}

export function fetchKnowledgeCategories(
  tenantId: string,
): Promise<KnowledgeCategory[]> {
  return data(
    httpClient.get(`/api/v1/knowledge/tenants/${tenantId}/categories`),
  )
}

export function fetchKnowledgeArticles(
  tenantId: string,
  category?: string,
): Promise<KnowledgeArticle[]> {
  return data(
    httpClient.get(`/api/v1/knowledge/tenants/${tenantId}/articles`, {
      params: category ? { category } : undefined,
    }),
  )
}

export function fetchKnowledgeArticle(
  tenantId: string,
  slug: string,
): Promise<KnowledgeArticle> {
  return data(
    httpClient.get(
      `/api/v1/knowledge/tenants/${tenantId}/articles/${slug}`,
    ),
  )
}
