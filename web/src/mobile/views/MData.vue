<template>
  <div class="m-data-page">
    <!-- 操作栏 -->
    <div class="m-actions">
      <el-select v-model="selectedFolder" placeholder="选择文件夹" size="small" @change="onFolderChange">
        <el-option v-for="item in folderList" :key="item" :label="item" :value="item" />
      </el-select>
      <el-select v-model="selectedFile" placeholder="选择数据集" size="small" @change="selectFile">
        <el-option v-for="item in fileList" :key="item" :label="item" :value="item" />
      </el-select>
      <el-select v-model="roundsFilter" placeholder="筛选" size="small" style="max-width: 90px;" @change="onFilterChange">
        <el-option label="全部" value="all" />
        <el-option label="单轮" value="single" />
        <el-option label="多轮" value="multi" />
      </el-select>
    </div>

    <!-- 数据加载中 -->
    <div v-if="loading" class="m-empty">
      <div class="m-spinner m-spinner--lg"></div>
      <span style="margin-top:6px;">加载中...</span>
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
          <span class="m-id-badge">#{{ row.id }}</span>
          <span :class="['m-tag', row.rounds > 1 ? 'm-tag-warning' : 'm-tag-info']">
            {{ row.rounds }}轮
          </span>
        </div>
        <div class="m-list-item-body">
          <div
            v-for="(msg, idx) in row.conversations.slice(0, 4)"
            :key="idx"
            class="conv-line"
            :class="msg.role"
          >
            <span class="conv-role">{{ msg.role === 'user' ? 'U' : 'A' }}</span>
            <span class="conv-text">{{ truncate(msg.content, 60) }}</span>
          </div>
          <div v-if="row.conversations.length > 4" class="conv-more">
            还有 {{ row.conversations.length - 4 }} 条消息
          </div>
        </div>
        <div class="m-list-item-footer">
          <el-button size="small" plain @click="viewDetail(row)">查看详情</el-button>
        </div>
      </div>

      <!-- 分页 -->
      <div class="m-pager">
        <button :disabled="currentPage <= 1" @click="prevPage">上一页</button>
        <span>{{ currentPage }} / {{ totalPages }}</span>
        <button :disabled="currentPage >= totalPages" @click="nextPage">下一页</button>
      </div>
    </template>

    <!-- ====== 数据详情弹窗 ====== -->
    <div v-if="showDetail" class="m-modal-overlay" @click.self="showDetail = false">
      <div class="m-modal-content">
        <div class="m-modal-header">
          <span>数据详情 #{{ detailForm.id }}</span>
          <span class="m-modal-close" @click="showDetail = false">&times;</span>
        </div>
        <div
          v-for="(msg, idx) in detailForm.conversations"
          :key="idx"
          class="detail-msg-block"
        >
          <div class="detail-msg-meta">
            <span :class="['m-tag', msg.role === 'user' ? 'm-tag-info' : 'm-tag-success']">
              {{ msg.role === 'user' ? 'User' : 'Assistant' }}
            </span>
            <span class="detail-round">第{{ Math.floor(idx / 2) + 1 }}轮</span>
          </div>
          <el-input
            :model-value="msg.content"
            type="textarea"
            :rows="2"
            size="small"
            disabled
            class="detail-msg-input"
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

/* ID 徽标 */
.m-id-badge {
  font-size: 12px;
  font-weight: 600;
  color: var(--c-text-muted);
  background: var(--c-border-light);
  padding: 2px 8px;
  border-radius: 6px;
}

/* 对话行 */
.conv-line {
  display: flex;
  gap: 6px;
  font-size: 13px;
  margin-bottom: 5px;
  padding: 4px 8px;
  border-radius: 6px;
  background: var(--c-bg);
}

.conv-line.user {
  border-left: 2px solid var(--c-primary-light);
}

.conv-line.assistant {
  border-left: 2px solid var(--c-success);
}

.conv-role {
  flex-shrink: 0;
  font-weight: 700;
  font-size: 11px;
  width: 18px;
  height: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  margin-top: 1px;
}

.conv-line.user .conv-role {
  background: var(--c-primary-soft);
  color: var(--c-primary);
}

.conv-line.assistant .conv-role {
  background: var(--c-success-soft);
  color: var(--c-success);
}

.conv-text {
  color: var(--c-text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
}

.conv-more {
  color: var(--c-text-muted);
  font-size: 12px;
  margin-top: 6px;
  padding-left: 8px;
  font-style: italic;
}

/* 详情弹窗内的对话块 */
.detail-msg-block {
  margin-bottom: 14px;
  padding-bottom: 14px;
  border-bottom: 1px solid var(--c-border-light);
}

.detail-msg-block:last-child {
  border-bottom: none;
  margin-bottom: 0;
  padding-bottom: 0;
}

.detail-msg-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}

.detail-round {
  font-size: 12px;
  color: var(--c-text-muted);
  font-weight: 500;
}

.detail-msg-input :deep(.el-textarea__inner) {
  background: var(--c-bg);
  border-color: transparent;
  color: var(--c-text-primary);
  font-size: 13px;
  line-height: 1.6;
}
</style>