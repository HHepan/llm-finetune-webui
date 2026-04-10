<template>
  <div class="page-container">
    <!-- 顶部操作区 -->
    <div class="action-bar">
      <div class="left-actions">
        <span class="label">选择文件夹：</span>
        <el-select v-model="selectedFolder" placeholder="请选择文件夹" style="width: 180px" @change="onFolderChange">
          <el-option
            v-for="item in folderList"
            :key="item"
            :label="item"
            :value="item"
          />
        </el-select>
        <span class="label" style="margin-left: 20px;">当前数据集：</span>
        <el-popover
          placement="bottom-start"
          :width="280"
          trigger="click"
          popper-class="file-select-popover"
        >
          <template #reference>
            <el-button class="file-select-btn">
              <span class="file-select-text">{{ selectedFile || '请选择数据集文件' }}</span>
              <el-icon class="el-icon--right"><ArrowDown /></el-icon>
            </el-button>
          </template>
          <div class="file-list-container">
            <div
              v-for="item in fileList"
              :key="item"
              class="file-list-item"
              @click="selectFile(item)"
            >
              <span class="file-name">{{ item }}</span>
              <el-button
                type="danger"
                size="small"
                link
                @click.stop="confirmDeleteFile(item)"
              >
                <el-icon><Delete /></el-icon>
              </el-button>
            </div>
            <div v-if="fileList.length === 0" class="file-list-empty">
              暂无文件
            </div>
          </div>
        </el-popover>
        <span class="label" style="margin-left: 20px;">筛选类型：</span>
        <el-select v-model="roundsFilter" placeholder="筛选类型" style="width: 120px" @change="onRoundsFilterChange">
          <el-option label="全部数据" value="all" />
          <el-option label="单轮对话" value="single" />
          <el-option label="多轮对话" value="multi" />
        </el-select>
      </div>
      <div class="right-actions">
        <el-button type="success" @click="openMergeDialog">
          <el-icon><CopyDocument /></el-icon> 合并与打乱
        </el-button>
      </div>
    </div>

    <!-- 数据表格区 -->
    <el-table :data="tableData" border stripe style="width: 100%; margin-top: 20px" v-loading="loading">
      <el-table-column prop="id" label="行号" width="80" align="center" />
      <el-table-column prop="rounds" label="轮次" width="100" align="center">
        <template #default="scope">
          <el-tag :type="scope.row.rounds > 1 ? 'warning' : 'info'" size="small">
            {{ scope.row.rounds }}轮
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="对话内容" min-width="400">
        <template #default="scope">
          <div class="conversation-display">
            <div
              v-for="(msg, idx) in scope.row.conversations"
              :key="idx"
              :class="['conversation-item', msg.role === 'user' ? 'user-msg' : 'assistant-msg']"
            >
              <span class="round-label">第{{ Math.floor(idx / 2) + 1 }}轮 - </span>
              <span class="role-label">{{ msg.role === 'user' ? 'User' : 'Assistant' }}:</span>
              <span class="content">{{ msg.content }}</span>
            </div>
          </div>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="160" align="center">
        <template #default="scope">
          <el-button size="small" type="primary" @click="openEditDialog(scope.row)">编辑</el-button>
          <el-button size="small" type="danger" @click="deleteRow(scope.row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 分页 -->
    <div class="pagination-container">
      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :page-sizes="[10, 20, 50, 100]"
        layout="total, sizes, prev, pager, next, jumper"
        :total="totalRows"
        @size-change="handleSizeChange"
        @current-change="handleCurrentChange"
      />
    </div>

    <!-- 编辑单行数据的弹窗 -->
    <el-dialog v-model="editDialogVisible" title="编辑数据" width="70%">
      <div class="edit-conversation-list">
        <div
          v-for="(msg, idx) in editForm.conversations"
          :key="idx"
          class="edit-conversation-item"
        >
          <div class="edit-item-header">
            <span class="round-label">第{{ Math.floor(idx / 2) + 1 }}轮</span>
            <el-tag :type="msg.role === 'user' ? 'primary' : 'success'" size="small">
              {{ msg.role === 'user' ? 'User' : 'Assistant' }}
            </el-tag>
            <el-button
              v-if="msg.role === 'assistant'"
              type="danger"
              size="small"
              link
              @click="removeRound(idx)"
              style="margin-left: auto;"
            >
              删除本轮
            </el-button>
          </div>
          <el-input
            v-model="msg.content"
            type="textarea"
            :rows="2"
            :placeholder="msg.role === 'user' ? '输入 User 内容...' : '输入 Assistant 内容...'"
          />
        </div>
      </div>
      <div class="edit-actions">
        <el-button type="primary" plain @click="addRound">添加一轮对话</el-button>
      </div>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="editDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="saveEdit">保存修改</el-button>
        </span>
      </template>
    </el-dialog>

    <!-- 合并与打乱数据集的弹窗 -->
    <el-dialog v-model="mergeDialogVisible" title="合并与打乱数据集" width="600px" @closed="onMergeDialogClosed">
      <el-form label-width="120px">
        <el-form-item label="选择源数据集">
          <el-select
            v-model="mergeForm.sourceFiles"
            multiple
            placeholder="请选择要合并的文件(支持跨文件夹)"
            style="width: 100%"
            @change="onSourceFilesChange"
          >
            <el-option
              v-for="item in allFileOptions"
              :key="item.value"
              :label="item.label"
              :value="item.value"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="是否打乱(Shuffle)">
          <el-switch v-model="mergeForm.shuffle" />
        </el-form-item>

        <el-form-item label="抽样数量分配" v-if="mergeForm.sourceFiles.length >= 1">
          <div class="counts-section">
            <div v-for="fileKey in mergeForm.sourceFiles" :key="fileKey" class="count-item">
              <span class="count-filename">{{ fileKey }}</span>
              <el-input-number
                v-model="mergeForm.counts[fileKey]"
                :min="0"
                :max="getFileLineCount(fileKey)"
                size="small"
                style="width: 120px;"
              />
              <span class="count-label">条</span>
              <span class="count-max">(共{{ getFileLineCount(fileKey) }}条)</span>
              <span class="count-ratio">占比: {{ getCountRatio(fileKey) }}%</span>
              <div v-if="mergeForm.counts[fileKey] > getFileLineCount(fileKey)" class="count-warning">
                <el-icon><WarningFilled /></el-icon>
                抽取数量不能超过源数据集总数
              </div>
            </div>
            <div class="count-total">
              新数据集总条数: {{ mergeFormTotalCount }} 条
            </div>
          </div>
        </el-form-item>

        <el-form-item label="新数据集名称">
          <el-input v-model="mergeForm.newName" placeholder="例如: merged_dataset">
            <template #append>.jsonl</template>
          </el-input>
        </el-form-item>

        <el-form-item label="保存位置">
          <el-tag type="info">workspace/data/out</el-tag>
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="mergeDialogVisible = false">取消</el-button>
          <el-button
            type="success"
            @click="submitMerge"
            :disabled="!canSubmitMerge"
          >
            开始处理
          </el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { CopyDocument, WarningFilled, ArrowDown, Delete } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
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

const editDialogVisible = ref(false)
const editForm = reactive({ id: null, conversations: [] })

const mergeDialogVisible = ref(false)
const mergeForm = reactive({
  sourceFiles: [],
  fileStats: [],
  shuffle: true,
  newName: '',
  counts: {}
})

const allFileOptions = computed(() => {
  const options = []
  for (const folder of folderList.value) {
    const files = allFilesByFolder.value[folder] || []
    for (const file of files) {
      const key = `${folder}/${file}`
      options.push({ label: key, value: key })
    }
  }
  return options
})

const allFilesByFolder = ref({})

const getFileLineCount = (fileKey) => {
  const stat = mergeForm.fileStats.find(s => {
    const fullKey = s.folder ? `${s.folder}/${s.filename}` : s.filename
    return fullKey === fileKey
  })
  return stat ? stat.line_count : 0
}

const mergeFormTotalCount = computed(() => {
  return Object.values(mergeForm.counts).reduce((sum, count) => sum + (count || 0), 0)
})

const hasOverLimit = computed(() => {
  return mergeForm.sourceFiles.some(filename => {
    return mergeForm.counts[filename] > getFileLineCount(filename)
  })
})

const canSubmitMerge = computed(() => {
  if (mergeForm.sourceFiles.length < 1) return false
  if (!mergeForm.newName) return false
  if (mergeFormTotalCount.value === 0) return false
  if (hasOverLimit.value) return false
  return true
})

const getCountRatio = (fileKey) => {
  if (mergeFormTotalCount.value === 0) return '0.0'
  const count = mergeForm.counts[fileKey] || 0
  return ((count / mergeFormTotalCount.value) * 100).toFixed(1)
}

const loadFolderList = async () => {
  try {
    const res = await axios.get('/api/data/folders')
    folderList.value = res.data
    if (folderList.value.length > 0) {
      selectedFolder.value = './'
      await loadFileList()
    }
  } catch (error) {
    ElMessage.error('获取文件夹列表失败')
  }
}

const getFolderParam = (folder) => {
  return folder.replace('./', '') || ''
}

const loadFileList = async () => {
  try {
    const res = await axios.get('/api/data/files', {
      params: { folder: getFolderParam(selectedFolder.value) }
    })
    fileList.value = res.data
    if (fileList.value.length > 0 && !selectedFile.value) {
      selectedFile.value = fileList.value[0]
      loadData()
    } else {
      selectedFile.value = ''
      tableData.value = []
      totalRows.value = 0
    }
  } catch (error) {
    ElMessage.error('获取文件列表失败')
  }
}

const onFolderChange = () => {
  selectedFile.value = ''
  currentPage.value = 1
  loadFileList()
}

const selectFile = (file) => {
  if (selectedFile.value !== file) {
    selectedFile.value = file
    currentPage.value = 1
    loadData()
  }
}

const confirmDeleteFile = async (file) => {
  try {
    await ElMessageBox.confirm(`确定要删除文件 "${file}" 吗？此操作不可恢复！`, '删除确认', {
      confirmButtonText: '确定删除',
      cancelButtonText: '取消',
      type: 'warning'
    })
    await deleteFile(file)
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(error.response?.data?.detail || '删除失败')
    }
  }
}

const deleteFile = async (file) => {
  try {
    await axios.delete(`/api/data/files/${file}`, {
      params: { folder: getFolderParam(selectedFolder.value) }
    })
    ElMessage.success('文件已删除')
    const currentIndex = fileList.value.indexOf(file)
    await loadFileList()
    if (fileList.value.length > 0) {
      if (currentIndex < fileList.value.length) {
        selectedFile.value = fileList.value[currentIndex]
      } else {
        selectedFile.value = fileList.value[fileList.value.length - 1]
      }
      loadData()
    } else {
      selectedFile.value = ''
      tableData.value = []
      totalRows.value = 0
    }
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '删除失败')
  }
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
    ElMessage.success(`成功加载 ${selectedFile.value}`)
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '加载数据失败')
  } finally {
    loading.value = false
  }
}

const onRoundsFilterChange = () => {
  currentPage.value = 1
  loadData()
}

const handleSizeChange = (val) => {
  pageSize.value = val
  loadData()
}
const handleCurrentChange = (val) => {
  currentPage.value = val
  loadData()
}

const openEditDialog = (row) => {
  editForm.id = row.id
  editForm.conversations = JSON.parse(JSON.stringify(row.conversations))
  editDialogVisible.value = true
}

const addRound = () => {
  editForm.conversations.push(
    { role: 'user', content: '' },
    { role: 'assistant', content: '' }
  )
}

const removeRound = (assistantIndex) => {
  const roundIndex = Math.floor(assistantIndex / 2)
  editForm.conversations.splice(roundIndex * 2, 2)
}

const buildText = (conversations) => {
  return conversations
    .map(msg => `${msg.role === 'user' ? 'User' : 'Assistant'}: ${msg.content}`)
    .join('\n\n')
}

const saveEdit = async () => {
  const text = buildText(editForm.conversations)
  try {
    await axios.put(`/api/data/files/${selectedFile.value}/${editForm.id}`, text, {
      params: { folder: getFolderParam(selectedFolder.value) },
      headers: { 'Content-Type': 'text/plain' }
    })
    ElMessage.success('修改已保存')
    editDialogVisible.value = false
    loadData()
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '保存失败')
  }
}

const deleteRow = async (row) => {
  try {
    await ElMessageBox.confirm(`确定要删除第 ${row.id} 行数据吗？`, '删除确认', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    await axios.delete(`/api/data/files/${selectedFile.value}/${row.id}`, {
      params: { folder: getFolderParam(selectedFolder.value) }
    })
    ElMessage.success('删除成功')
    loadData()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(error.response?.data?.detail || '删除失败')
    }
  }
}

const openMergeDialog = async () => {
  mergeForm.sourceFiles = []
  mergeForm.fileStats = []
  mergeForm.shuffle = true
  mergeForm.newName = ''
  mergeForm.counts = {}
  
  const filesByFolder = {}
  for (const folder of folderList.value) {
    try {
      const res = await axios.get('/api/data/files', { params: { folder } })
      filesByFolder[folder] = res.data
    } catch (error) {
      filesByFolder[folder] = []
    }
  }
  allFilesByFolder.value = filesByFolder
  
  mergeDialogVisible.value = true
}

const onMergeDialogClosed = () => {
  mergeForm.sourceFiles = []
  mergeForm.fileStats = []
  mergeForm.counts = {}
  allFilesByFolder.value = {}
}

const loadFileStats = async (fileKeys) => {
  if (fileKeys.length === 0) {
    mergeForm.fileStats = []
    mergeForm.counts = {}
    return
  }
  try {
    const filenames = []
    const folders = []
    for (const key of fileKeys) {
      const parts = key.split('/')
      if (parts.length === 2) {
        folders.push(parts[0])
        filenames.push(parts[1])
      } else {
        folders.push('')
        filenames.push(key)
      }
    }
    const filesParam = filenames.join(',')
    const foldersParam = folders.join(',')
    const res = await axios.get(`/api/data/files/stats?files=${filesParam}&folders=${foldersParam}`)
    mergeForm.fileStats = res.data
    fileKeys.forEach(f => {
      const parts = f.split('/')
      const filename = parts.length === 2 ? parts[1] : f
      const folder = parts.length === 2 ? parts[0] : ''
      const stat = res.data.find(s => s.filename === filename && s.folder === folder)
      mergeForm.counts[f] = stat ? stat.line_count : 0
    })
  } catch (error) {
    ElMessage.error('获取文件统计失败')
  }
}

const onSourceFilesChange = () => {
  loadFileStats(mergeForm.sourceFiles)
}

const submitMerge = async () => {
  try {
    const sourceFiles = mergeForm.sourceFiles.map(key => {
      const parts = key.split('/')
      if (parts.length === 2) {
        return { folder: parts[0], filename: parts[1] }
      } else {
        return { folder: '', filename: key }
      }
    })
    const res = await axios.post('/api/data/merge', {
      source_files: sourceFiles,
      shuffle: mergeForm.shuffle,
      new_name: mergeForm.newName,
      counts: { ...mergeForm.counts },
      folder: 'out'
    })
    ElMessage.success(`合并成功，已保存到 ${res.data.path}`)
    mergeDialogVisible.value = false
    if (!folderList.value.includes('./out')) {
      loadFolderList()
    } else if (selectedFolder.value === './out') {
      loadFileList()
    }
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '合并失败')
  }
}

onMounted(() => {
  loadFolderList()
})
</script>

<style scoped>
.action-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background-color: #f8f9fa;
  padding: 15px;
  border-radius: 8px;
  border: 1px solid #ebeef5;
}

.left-actions {
  display: flex;
  align-items: center;
}

.file-select-btn {
  width: 250px;
  justify-content: space-between;
}

.file-select-text {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
  text-align: left;
}

.file-list-container {
  max-height: 300px;
  overflow-y: auto;
}

.file-list-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  cursor: pointer;
  border-radius: 4px;
  transition: background-color 0.2s;
}

.file-list-item:hover {
  background-color: #f5f7fa;
}

.file-name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  margin-right: 8px;
}

.file-list-empty {
  padding: 20px;
  text-align: center;
  color: #909399;
}

.label {
  font-weight: bold;
  margin-right: 10px;
  color: #606266;
}

.pagination-container {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}

.conversation-display {
  font-size: 14px;
  line-height: 1.6;
}

.conversation-item {
  padding: 4px 8px;
  border-radius: 4px;
  margin: 2px 0;
}

.user-msg {
  background-color: #ecf5ff;
  border-left: 3px solid #409eff;
}

.assistant-msg {
  background-color: #f0f9eb;
  border-left: 3px solid #67c23a;
}

.round-label {
  color: #909399;
  font-size: 13px;
  margin-right: 4px;
}

.role-label {
  font-weight: 600;
  margin: 0 4px;
}

.user-msg .role-label {
  color: #409eff;
}

.assistant-msg .role-label {
  color: #67c23a;
}

.content {
  color: #303133;
}

.edit-conversation-list {
  max-height: 400px;
  overflow-y: auto;
  padding: 10px;
}

.edit-conversation-item {
  margin-bottom: 16px;
  padding: 12px;
  background-color: #f5f7fa;
  border-radius: 8px;
}

.edit-item-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.edit-item-header .round-label {
  font-weight: 600;
}

.edit-actions {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid #ebeef5;
  text-align: center;
}

.counts-section {
  width: 100%;
}

.count-item {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
  padding: 8px;
  background-color: #f5f7fa;
  border-radius: 4px;
}

.count-filename {
  width: 140px;
  font-size: 14px;
  color: #606266;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.count-label {
  font-size: 14px;
  color: #606266;
}

.count-max {
  font-size: 13px;
  color: #909399;
}

.count-ratio {
  font-size: 14px;
  color: #67c23a;
  font-weight: 500;
  margin-left: auto;
}

.count-warning {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  color: #f56c6c;
  margin-top: 4px;
}

.count-total {
  margin-top: 8px;
  padding-top: 12px;
  border-top: 1px solid #ebeef5;
  font-size: 15px;
  font-weight: 600;
  color: #303133;
}
</style>
