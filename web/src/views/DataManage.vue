<template>
  <div class="page-container">
    <!-- 顶部操作区 -->
    <div class="action-bar">
      <div class="left-actions">
        <span class="label">当前数据集：</span>
        <el-select v-model="selectedFile" placeholder="请选择数据集文件" style="width: 250px">
          <el-option
            v-for="item in fileList"
            :key="item"
            :label="item"
            :value="item"
          />
        </el-select>
        <el-button type="primary" style="margin-left: 10px" @click="loadData" :disabled="!selectedFile">
          加载数据
        </el-button>
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
            placeholder="请选择要合并的文件"
            style="width: 100%"
            @change="onSourceFilesChange"
          >
            <el-option v-for="item in fileList" :key="item" :label="item" :value="item" />
          </el-select>
        </el-form-item>

        <el-form-item label="是否打乱(Shuffle)">
          <el-switch v-model="mergeForm.shuffle" />
        </el-form-item>

        <el-form-item label="抽样数量分配" v-if="mergeForm.sourceFiles.length >= 1">
          <div class="counts-section">
            <div v-for="filename in mergeForm.sourceFiles" :key="filename" class="count-item">
              <span class="count-filename">{{ filename }}</span>
              <el-input-number
                v-model="mergeForm.counts[filename]"
                :min="0"
                :max="getFileLineCount(filename)"
                size="small"
                style="width: 120px;"
              />
              <span class="count-label">条</span>
              <span class="count-max">(共{{ getFileLineCount(filename) }}条)</span>
              <span class="count-ratio">占比: {{ getCountRatio(filename) }}%</span>
              <div v-if="mergeForm.counts[filename] > getFileLineCount(filename)" class="count-warning">
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
import { CopyDocument, WarningFilled } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import axios from 'axios'

const fileList = ref([])
const selectedFile = ref('')
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

const getFileLineCount = (filename) => {
  const stat = mergeForm.fileStats.find(s => s.filename === filename)
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

const getCountRatio = (filename) => {
  if (mergeFormTotalCount.value === 0) return '0.0'
  const count = mergeForm.counts[filename] || 0
  return ((count / mergeFormTotalCount.value) * 100).toFixed(1)
}

const loadFileList = async () => {
  try {
    const res = await axios.get('/api/data/files')
    fileList.value = res.data
  } catch (error) {
    ElMessage.error('获取文件列表失败')
  }
}

const loadData = async () => {
  if (!selectedFile.value) return
  loading.value = true
  try {
    const res = await axios.get(`/api/data/files/${selectedFile.value}`, {
      params: { page: currentPage.value, size: pageSize.value }
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
    await axios.delete(`/api/data/files/${selectedFile.value}/${row.id}`)
    ElMessage.success('删除成功')
    loadData()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(error.response?.data?.detail || '删除失败')
    }
  }
}

const openMergeDialog = () => {
  mergeForm.sourceFiles = []
  mergeForm.fileStats = []
  mergeForm.shuffle = true
  mergeForm.newName = ''
  mergeForm.counts = {}
  mergeDialogVisible.value = true
}

const onMergeDialogClosed = () => {
  mergeForm.sourceFiles = []
  mergeForm.fileStats = []
  mergeForm.counts = {}
}

const loadFileStats = async (filenames) => {
  if (filenames.length === 0) {
    mergeForm.fileStats = []
    mergeForm.counts = {}
    return
  }
  try {
    const filesParam = filenames.join(',')
    const res = await axios.get(`/api/data/files/stats?files=${filesParam}`)
    mergeForm.fileStats = res.data
    filenames.forEach(f => {
      const stat = res.data.find(s => s.filename === f)
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
    await axios.post('/api/data/merge', {
      source_files: mergeForm.sourceFiles,
      shuffle: mergeForm.shuffle,
      new_name: mergeForm.newName,
      counts: { ...mergeForm.counts }
    })
    ElMessage.success('合并成功')
    mergeDialogVisible.value = false
    loadFileList()
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '合并失败')
  }
}

onMounted(() => {
  loadFileList()
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
  font-size: 13px;
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
  font-size: 12px;
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
  font-size: 13px;
  color: #606266;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.count-label {
  font-size: 13px;
  color: #606266;
}

.count-max {
  font-size: 12px;
  color: #909399;
}

.count-ratio {
  font-size: 13px;
  color: #67c23a;
  font-weight: 500;
  margin-left: auto;
}

.count-warning {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: #f56c6c;
  margin-top: 4px;
}

.count-total {
  margin-top: 8px;
  padding-top: 12px;
  border-top: 1px solid #ebeef5;
  font-size: 14px;
  font-weight: 600;
  color: #303133;
}
</style>
