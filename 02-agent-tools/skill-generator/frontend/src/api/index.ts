import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
})

// --- 类型定义 ---
export interface SkillListItem {
  id: number
  title: string
  source: string
  source_url: string
  description: string
  tags: string | null
  stars: number | null
  language: string | null
  crawled_at: string
  is_doc_ready: boolean
}

export interface SkillDetail extends SkillListItem {
  raw_content: string
  doc_markdown: string | null
  doc_generated_at: string | null
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

export interface CrawlJob {
  id: number
  triggered_by: string
  status: string
  total: number
  success: number
  failed: number
  started_at: string
  finished_at: string | null
  error_msg: string | null
}

// --- API 方法 ---

export async function fetchSkills(params: {
  page?: number
  page_size?: number
  source?: string
  search?: string
  date?: string
}): Promise<PaginatedResponse<SkillListItem>> {
  const { data } = await api.get('/skills', { params })
  return data
}

export async function fetchSkillDetail(id: number): Promise<SkillDetail> {
  const { data } = await api.get(`/skills/${id}`)
  return data
}

export async function generateSkillDoc(id: number): Promise<{
  id: number
  is_doc_ready: boolean
  doc_markdown: string | null
  doc_generated_at: string | null
}> {
  const { data } = await api.post(`/skills/${id}/generate-doc`)
  return data
}

/**
 * 下载 Skill zip 包（标准 CodeFlicker Skill 格式）
 * 后端会实时调用 LLM 生成 Agent 操作指南，需要等待约 15-20 秒
 */
export async function downloadSkill(id: number): Promise<void> {
  const resp = await api.get(`/skills/${id}/download`, {
    responseType: 'blob',
    timeout: 120000, // 下载需等待 LLM 生成，最多 2 分钟
  })
  // 从 Content-Disposition 读取文件名
  const disposition = resp.headers['content-disposition'] || ''
  const match = disposition.match(/filename="?([^"]+)"?/)
  const filename = match ? match[1] : `skill-${id}.zip`

  // 触发浏览器下载
  const url = URL.createObjectURL(new Blob([resp.data], { type: 'application/zip' }))
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

export async function fetchJobs(limit = 20): Promise<CrawlJob[]> {
  const { data } = await api.get('/jobs', { params: { limit } })
  return data
}

export async function triggerCrawl(): Promise<{ message: string; status: string }> {
  const { data } = await api.post('/jobs/trigger')
  return data
}

export async function fetchHealth(): Promise<Record<string, any>> {
  const { data } = await api.get('/health')
  return data
}

export default api
