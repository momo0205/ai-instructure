import { defineStore } from 'pinia'
import { ref } from 'vue'
import { fetchSkills, fetchSkillDetail, triggerCrawl, type SkillListItem, type SkillDetail } from '../api'

export const useSkillStore = defineStore('skill', () => {
  const skills = ref<SkillListItem[]>([])
  const total = ref(0)
  const currentPage = ref(1)
  const pageSize = ref(20)
  const loading = ref(false)
  const currentSkill = ref<SkillDetail | null>(null)
  const detailLoading = ref(false)

  // 筛选条件
  const filterSource = ref<string | undefined>(undefined)
  const filterSearch = ref<string | undefined>(undefined)
  const filterDate = ref<string | undefined>(undefined)

  async function loadSkills(page = 1) {
    loading.value = true
    try {
      const res = await fetchSkills({
        page,
        page_size: pageSize.value,
        source: filterSource.value,
        search: filterSearch.value,
        date: filterDate.value,
      })
      skills.value = res.items
      total.value = res.total
      currentPage.value = res.page
    } catch (err) {
      console.error('加载技能列表失败:', err)
    } finally {
      loading.value = false
    }
  }

  async function loadSkillDetail(id: number) {
    detailLoading.value = true
    try {
      currentSkill.value = await fetchSkillDetail(id)
    } catch (err) {
      console.error('加载技能详情失败:', err)
    } finally {
      detailLoading.value = false
    }
  }

  async function trigger() {
    return await triggerCrawl()
  }

  return {
    skills,
    total,
    currentPage,
    pageSize,
    loading,
    currentSkill,
    detailLoading,
    filterSource,
    filterSearch,
    filterDate,
    loadSkills,
    loadSkillDetail,
    trigger,
  }
})
