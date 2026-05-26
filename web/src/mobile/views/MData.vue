<template>
  <div class="m-data-page">
    <!-- 文件夹选择 + 文件选择 + 筛选 三合一操作栏 -->
    <div class="m-actions">
      <el-select v-model="selectedFolder" placeholder="选择文件夹" size="small" @change="onFolderChange">
        <el-option v-for="item in folderList" :key="item" :label="item" :value="item" />
      </el-select>
      <el-select v-model="selectedFile" placeholder="选择数据集" size="small" @change="selectFile">
        <el-option v-for="item in fileList" :key="item" :label="item" :value="item" />
      </el-select>
      <el-select v-model="roundsFilter" placeholder="筛选" size="small" style="max-width: 100px;" @change="onFilterChange">
        <el-option label="全部" value="all" />
        <el-option label="单轮" value="single" />
        <el-option label="多轮" value="multi" />
      </el-select>
    </div>

    <!-- 数据加载中 -->
    <div v-if="loading" class="m-empty">
      <div class="m-empty-icon">⏳</div>
      <span>加载中...</span>
    </div>

    <!-- 空状态 -->
    <div v-else-if="!selectedFile" class="m-empty">
      <div class="m-empty-icon">📂</div>
      <span>请选择数据集文件</span>
    </div>

    <div v-else-if="tableData.length === 0" class="m-empty">
      <div class="m-empty-icon">📭</div>
      <span>暂无数据</span>
    </div>

    <!-- 数据卡片列表 -->
    <template v-else>
      <div
        v-for="row in tableData"
        :key="row.id"
        class="m-list-item"
      >
        <div class="m-list-item-header">
          <span>#{{ row.id }}</span>
          <span :class="['m-tag', row.rounds > 1 ? 'm-tag-warning' : 'm-tag-info']">
            {{ row.rounds }}轮
          </span>
        </div>
        <div class="m-list-item-body">
          <div
            v-for="(msg, idx) in row.conversations.slice(0, 4)"
            :key="idx"
            class="conv-line"
            :style="{ color: msg.role === 'user' ? '#409eff' : '#52c41a', fontSize: '13px', marginBottom: '4px' }"
          >
            <strong>{{ msg.role === 'user' ? 'U' : 'A' }}:</strong>
            <span style="color:#555">{{ truncate(msg.content, 60) }}</span>
          </div>
          <div v-if="row.conversations.length > 4" style="color:#999;font-size:12px;margin-top:4px;">
            ... 还有 {{ row.conversations.length - 4 }} 条消息
          </div>
        </div>
        <div class="m-list-item-footer">
          <el-button size="small" type="primary" plain @click="viewDetail(row)">查看</el-button>
        </div>
      </div>

      <!-- 简化分页 -->
      <div class="m-pager">
        <button :disabled="currentPage <= 1" @click="prevPage">上一页</button>
        <span>{{ currentPage }} / {{ totalPages }}</span>
        <button :disabled="currentPage >= totalPages" @click="nextPage">下一页</button>
      </div>
    </template>

    <!-- ====== 数据详情弹窗（查看模式） ====== -->
    <div v-if="showDetail" class="m-modal-overlay" @click.self="showDetail = false">
      <div class="m-modal-content">
        <div class="m-modal-header">
          <span>数据详情 #{{ detailForm.id }}</span>
          <span class="m-modal-close" @click="showDetail = false">&times;</span>
        </div>
        <div
          v-for="(msg, idx) in detailForm.conversations"
          :key="idx"
          style="margin-bottom: 10px;"
        >
          <div style="display:flex;align-items:center;gap:8px;margin-bottom:4px;">
            <span :class="['m-tag', msg.role === 'user' ? 'm-tag-info' : 'm-tag-success']">
              {{ msg.role === 'user' ? 'User' : 'Assistant' }}
            </span>
            <span style="font-size:12px;color:#999;">第{{ Math.floor(idx / 2) + 1 }}轮</span>
          </div>
          <el-input
            :model-value="msg.content"
            type="textarea"
            :rows="2"
            size="small"
            disabled
          />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import axios from 'axios'

const folderList = ref([])
const selectedFolder = ref('')
const fileList = ref([])
const selectedFile = ref('')
const roundsFilter = ref('all')
const loading = ref(false)

const tableData = ref([])
const currentPage = ref(1)
const pageSize = ref(10)
const totalRows = ref(0)

const totalPages = computed(() => Math.max(1, Math.ceil(totalRows.value / pageSize.value)))

// 详情查看
const showDetail = ref(false)
const detailForm = ref({ id: null, conversations: [] })

const truncate = (text, max) => {
  if (!text) return ''
  return text.length > max ? text.slice(0, max) + '...' : text
}

// ==== API 方法 ====

const loadFolderList = async () => {
  try {
    const res = await axios.get('/api/data/folders')
    folderList.value = res.data
    if (folderList.value.length > 0) {
      selectedFolder.value = './'
      await loadFileList()
    }
  } catch { ElMessage.error('获取文件夹列表失败') }
}

const getFolderParam = (folder) => folder.replace('./', '') || ''

const loadFileList = async () => {
  try {
    const res = await axios.get('/api/data/files', { params: { folder: getFolderParam(selectedFolder.value) } })
    fileList.value = res.data
    if (fileList.value.length > 0 && !selectedFile.value) {
      selectedFile.value = fileList.value[0]
      loadData()
    } else if (fileList.value.length === 0) {
      selectedFile.value = ''
      tableData.value = []
      totalRows.value = 0
    }
  } catch { ElMessage.error('获取文件列表失败') }
}

const onFolderChange = () => {
  selectedFile.value = ''
  currentPage.value = 1
  loadFileList()
}

const selectFile = (file) => {
  selectedFile.value = file
  currentPage.value = 1
  loadData()
}

const onFilterChange = () => {
  currentPage.value = 1
  loadData()
}

const loadData = async () => {
  if (!selectedFile.value) return
  loading.value = true
  try {
    const res = await axios.get(`/api/data/files/${selectedFile.value}`, {
      params: { folder: getFolderParam(selectedFolder.value), page: currentPage.value, size: pageSize.value, rounds_filter: roundsFilter.value }
    })
    tableData.value = res.data.data
    totalRows.value = res.data.total
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '加载数据失败')
  } finally {
    loading.value = false
  }
}

const prevPage = () => { if (currentPage.value > 1) { currentPage.value--; loadData() } }
const nextPage = () => { if (currentPage.value < totalPages.value) { currentPage.value++; loadData() } }

// ==== 查看详情 ====
const viewDetail = (row) => {
  detailForm.value = { id: row.id, conversations: JSON.parse(JSON.stringify(row.conversations)) }
  showDetail.value = true
}

onMounted(loadFolderList)
</script>

<style scoped>
.m-data-page {
  padding-bottom: 8px;
}
.conv-line {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>