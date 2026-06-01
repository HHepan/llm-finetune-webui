<template>
  <div class="page-container">
    <div class="content-wrapper">
      <!-- 左侧对话区 -->
      <div class="left-panel">
        <el-card class="chat-card">
          <template #header>
            <div class="chat-header">
              <span>{{ currentChatName }}</span>
              <el-select
                v-model="selectedModel"
                placeholder="暂无对话，请新建"
                style="width: 280px;"
                @change="onModelChange"
                :disabled="isModelLoading"
              >
                <el-option
                  v-for="item in modelList"
                  :key="item.model + '|' + item.session"
                  :label="item.model + '-' + item.session"
                  :value="item.model + '|' + item.session"
                >
                  <div class="model-option">
                    <span class="model-option-label">{{ item.model + '-' + item.session }}</span>
                    <el-button
                      type="danger"
                      size="small"
                      class="model-option-delete"
                      @click.stop="confirmDeleteChat(item)"
                    >
                      删除
                    </el-button>
                  </div>
                </el-option>
              </el-select>
              <el-button type="success" @click="handleNewChat" :disabled="isModelLoading">新建对话</el-button>
              <el-button type="warning" @click="clearHistory" :disabled="!selectedModel">清空历史</el-button>
              <div v-if="isModelLoading" class="model-status loading">
                <el-icon class="loading-icon"><Loading /></el-icon>
                <span>加载</span>
              </div>
              <div v-else-if="modelLoadError" class="model-status error">
                <span>{{ modelLoadError }}</span>
                <el-button type="danger" size="small" @click="onModelChange(selectedModel)">重试</el-button>
              </div>
              <div v-else-if="isModelLoaded" class="model-status success">
                <el-icon><CircleCheck /></el-icon>
                <span>就绪</span>
              </div>
              <div style="flex:1;"></div>

              <!-- 角色选择下拉框 -->
              <el-select
                v-model="selectedRole"
                placeholder="选择角色"
                style="width: 220px; margin-right: 8px;"
                size="small"
                @change="onRoleChange"
                :disabled="isModelLoading"
              >
                <el-option
                  v-for="role in roleList"
                  :key="role.id"
                  :label="role.name"
                  :value="role.id"
                >
                  <div class="role-option">
                    <span class="role-option-label">{{ role.name }}</span>
                    <div class="role-option-buttons">
                      <el-button
                        v-if="role.id !== 'none'"
                        type="primary"
                        size="small"
                        circle
                        :icon="Edit"
                        class="role-option-btn"
                        @click.stop="handleEditRole(role)"
                      />
                      <el-button
                        v-if="role.id !== 'none'"
                        type="danger"
                        size="small"
                        circle
                        :icon="Delete"
                        class="role-option-btn"
                        @click.stop="confirmDeleteRole(role)"
                      />
                    </div>
                  </div>
                </el-option>
              </el-select>

              <!-- 添加角色按钮 -->
              <el-tooltip content="新建角色卡" placement="top">
                <el-button
                  size="small"
                  type="primary"
                  :icon="Plus"
                  circle
                  @click="showAddRoleDialog = true"
                  style="margin-right: 8px;"
                  :disabled="isModelLoading"
                >
                </el-button>
              </el-tooltip>

              <!-- 侧边栏切换 -->
              <el-tooltip :content="showRightPanel ? '隐藏侧边栏' : '显示侧边栏'" placement="top">
                <el-button
                  size="small"
                  @click="showRightPanel = !showRightPanel"
                  :icon="showRightPanel ? Hide : View"
                  circle
                >
                </el-button>
              </el-tooltip>
            </div>
          </template>

          <div v-if="showNewChatPanel" class="new-chat-panel">
            <span class="new-chat-panel-label">选择模型</span>
            <el-select v-model="newChatFolder" placeholder="文件夹" style="width: 180px;" @change="onFolderChange">
              <el-option v-for="folder in folderList" :key="folder" :label="folder" :value="folder" />
            </el-select>
            <el-select v-model="newChatModel" placeholder="模型文件" style="width: 200px;">
              <el-option v-for="model in modelFileList" :key="model" :label="model" :value="model" />
            </el-select>
            <el-input v-model="newChatSession" placeholder="请输入对话名称" style="width: 200px;" />
            <el-button @click="cancelNewChat">取消</el-button>
            <el-button type="success" @click="confirmNewChat" :disabled="!newChatFolder || !newChatModel || !newChatSession">确认创建</el-button>
          </div>

          <!-- 对话消息区域 -->
          <div class="chat-messages" ref="messagesRef">
            <div v-if="messages.length === 0" class="empty-chat">
              <el-empty description="暂无对话内容，请选择模型后开始对话" />
            </div>
            <template v-for="(msg, index) in messages" :key="index">
              <!-- 滑动窗口分割线 -->
              <div v-if="showDividerBefore(index)" class="memory-divider">
                <span class="divider-line"></span>
                <span class="divider-text">窗口外 · 模型不再记住</span>
                <span class="divider-line"></span>
              </div>
              <div
                :id="'msg-' + index"
                class="message-item"
                :class="msg.role"
              >
                <div class="message-left">
                <div class="message-avatar">
                  <el-icon v-if="msg.role === 'user'"><User /></el-icon>
                  <el-icon v-else><ChatDotRound /></el-icon>
                </div>
                <el-button
                  v-if="msg.role === 'assistant' && !msg.isStreaming && index === messages.length - 1"
                  type="primary"
                  size="small"
                  class="regenerate-btn"
                  :disabled="isModelLoading"
                  @click="regenerateLastMessage"
                >
                  New
                </el-button>
                <el-button
                  v-if="msg.role === 'user' && index === lastUserMessageIndex"
                  type="warning"
                  size="small"
                  class="re-edit-btn"
                  :disabled="isModelLoading || isGenerating"
                  @click="reEditLastMessage"
                >
                  Edit
                </el-button>
              </div>
              <div class="message-content">
                <!-- 可折叠的思考过程 -->
                <div
                  v-if="msg.role === 'assistant' && msg.thinkingContent"
                  class="thinking-collapse"
                >
                  <div class="thinking-header" @click="msg.showThinking = !msg.showThinking">
                    <span class="thinking-toggle">{{ msg.showThinking ? '▼' : '▶' }}</span>
                    <span class="thinking-label">💭 思考过程</span>
                  </div>
                  <div v-show="msg.showThinking" class="thinking-body">
                    <div class="thinking-text" v-html="formatMessage(msg.thinkingContent)"></div>
                  </div>
                </div>
                <div class="message-text" v-html="formatMessage(msg.content)"></div>
                <span v-if="msg.role === 'assistant' && msg.isStreaming" class="cursor">|</span>
                <div v-if="msg.role === 'assistant' && isThinking && !msg.content" class="thinking-indicator">
                  <span>思考中...</span>
                </div>
              </div>
            </div>
            </template>
          </div>

          <!-- 输入区域 -->
          <div class="chat-input-area">
            <el-input
              v-model="userInput"
              type="textarea"
              :rows="5"
              placeholder="请输入您的问题..."
              @keydown.enter="handleEnterKey"
              :disabled="isModelLoading"
            />
            <el-button
              type="primary"
              :disabled="!userInput.trim() || !selectedModel || isModelLoading"
              @click="sendMessage"
              class="send-btn"
            >
              <div class="btn-text">
                <span>发送</span>
                <span class="btn-sub">(Enter)</span>
              </div>
            </el-button>
          </div>
        </el-card>
      </div>

      <!-- 右侧参数区 -->
      <div v-show="showRightPanel" class="right-panel">
        <!-- 推理参数 -->
        <el-card class="param-card">
          <template #header>
            <div class="card-header">
              <div class="card-header-title">
                <span>推理参数</span>
                <el-icon v-if="isSavingParams" class="syncing-icon"><Loading /></el-icon>
                <el-icon v-else-if="isParamsSynced" class="synced-icon"><CircleCheck /></el-icon>
              </div>
              <el-button size="small" @click="resetParams">重置默认</el-button>
            </div>
          </template>
          <el-form :model="inferParams" label-width="100px" class="infer-form">
            <el-form-item label="选择的模型">
              <el-input v-model="inferParams.model" disabled style="width: 100%" />
            </el-form-item>

            <el-form-item label="max-tokens">
              <el-tooltip content="模型单次回复最大生成的 token 数量" placement="top">
                <el-input-number
                  v-model="inferParams.max_tokens"
                  :min="1"
                  :max="4096"
                  style="width: 100%"
                />
              </el-tooltip>
            </el-form-item>

            <el-form-item label="clean-rounds">
              <el-tooltip content="每隔多少轮对话清理一次显存，防止显存溢出" placement="top">
                <el-input-number
                  v-model="inferParams.clean_rounds"
                  :min="1"
                  :max="100"
                  style="width: 100%"
                />
              </el-tooltip>
            </el-form-item>

            <el-form-item label="temperature">
              <template #label>
                <el-tooltip content="值越高输出越随机多样，值越低越确定保守（取值范围为[0,2]）" placement="top">
                  <span>temperature</span>
                </el-tooltip>
              </template>
              <div class="slider-container">
                <el-slider
                  v-model="inferParams.temperature"
                  :min="0"
                  :max="2"
                  :step="0.01"
                  :show-tooltip="true"
                  :format-tooltip="val => val.toFixed(2)"
                />
                <span class="slider-value">{{ inferParams.temperature.toFixed(2) }}</span>
              </div>
            </el-form-item>

            <el-form-item label="top_p">
              <template #label>
                <el-tooltip content="核采样阈值。只从累计概率≥top_p的最小token集合中采样。值越小生成越集中保守（取值范围为[0,1]）" placement="top">
                  <span>top_p</span>
                </el-tooltip>
              </template>
              <div class="slider-container">
                <el-slider
                  v-model="inferParams.top_p"
                  :min="0"
                  :max="1"
                  :step="0.01"
                  :show-tooltip="true"
                  :format-tooltip="val => val.toFixed(2)"
                />
                <span class="slider-value">{{ inferParams.top_p.toFixed(2) }}</span>
              </div>
            </el-form-item>

            <el-form-item label="top_k">
              <el-tooltip content="Top-K采样。只从概率最高的K个token中选择。值越小越保守，值越大越随机（取值范围为[0,200]）" placement="top">
                <el-input-number
                  v-model="inferParams.top_k"
                  :min="0"
                  :max="200"
                  style="width: 100%"
                />
              </el-tooltip>
            </el-form-item>

            <el-form-item label="alpha_frequency">
              <template #label>
                <el-tooltip content="频率惩罚。根据token已出现的频率降低其被选中的概率，防止重复（取值范围为[0,1]）" placement="top">
                  <span>alpha_frequency</span>
                </el-tooltip>
              </template>
              <div class="slider-container">
                <el-slider
                  v-model="inferParams.alpha_frequency"
                  :min="0"
                  :max="1"
                  :step="0.01"
                  :show-tooltip="true"
                  :format-tooltip="val => val.toFixed(2)"
                />
                <span class="slider-value">{{ inferParams.alpha_frequency.toFixed(2) }}</span>
              </div>
            </el-form-item>

            <el-form-item label="alpha_presence">
              <template #label>
                <el-tooltip content="存在惩罚。如果token在已生成文本中出现过就降低其概率，减少重复词（取值范围为[0,1]）" placement="top">
                  <span>alpha_presence</span>
                </el-tooltip>
              </template>
              <div class="slider-container">
                <el-slider
                  v-model="inferParams.alpha_presence"
                  :min="0"
                  :max="1"
                  :step="0.01"
                  :show-tooltip="true"
                  :format-tooltip="val => val.toFixed(2)"
                />
                <span class="slider-value">{{ inferParams.alpha_presence.toFixed(2) }}</span>
              </div>
            </el-form-item>

            <el-form-item label="alpha_decay">
              <template #label>
                <el-tooltip content="惩罚随生成token数递减的速率（取值范围为[0,1]）" placement="top">
                  <span>alpha_decay</span>
                </el-tooltip>
              </template>
              <div class="slider-container">
                <el-slider
                  v-model="inferParams.alpha_decay"
                  :min="0"
                  :max="1"
                  :step="0.001"
                  :show-tooltip="true"
                  :format-tooltip="val => val.toFixed(3)"
                />
                <span class="slider-value">{{ inferParams.alpha_decay.toFixed(3) }}</span>
              </div>
            </el-form-item>

            <el-form-item label="思考模式">
              <el-switch v-model="thinkingMode" active-text="开启" inactive-text="关闭" />
            </el-form-item>

            <el-form-item label="max-rounds">
              <template #label>
                <el-tooltip content="滑动窗口：保留最近 N 轮对话历史（含角色卡），超出部分自动裁剪" placement="top">
                  <span>max-rounds</span>
                </el-tooltip>
              </template>
              <el-input-number
                v-model="inferParams.max_rounds"
                :min="1"
                :max="100"
                style="width: 100%"
              />
            </el-form-item>
          </el-form>
        </el-card>

        <!-- 模型惊讶度 -->
        <el-card class="param-card">
          <template #header>
            <div class="card-header">
              <span>模型惊讶度</span>
              <el-switch v-model="showPerplexity" active-text="显示" inactive-text="隐藏" />
            </div>
          </template>
          <div v-show="showPerplexity" class="perplexity-chart">
            <div ref="perplexityChartRef" style="width: 100%; height: 150px;"></div>
          </div>
        </el-card>

        <!-- 对话发展线 -->
        <el-card class="param-card">
          <template #header>
            <div class="card-header">
              <span>对话发展线</span>
            </div>
          </template>
          <div class="empty-placeholder">
            待开发
          </div>
        </el-card>
      </div>
    </div>
  </div>

  <!-- 添加/编辑角色对话框 -->
  <el-dialog v-model="showAddRoleDialog" :title="isEditingRole ? '编辑角色卡' : '新建角色卡'" width="1000px">
    <el-form :model="newRoleForm" label-width="80px">
      <el-form-item label="角色名称">
        <el-input v-model="newRoleForm.name" placeholder="请输入角色名称" />
      </el-form-item>
      <el-form-item label="角色设定">
        <el-input
          v-model="newRoleForm.content"
          type="textarea"
          :rows="10"
          placeholder="请输入角色设定描述，例如：&#10;你是一位温柔知性的学姐，说话总是带着微笑，给人一种如沐春风的感觉。喜欢用过来人的身份给后辈建议，偶尔也会展现出不为人知的调皮一面。称呼对方为'后辈君'。"
        />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="closeRoleDialog">取消</el-button>
      <el-button type="primary" @click="confirmAddRole" :disabled="!newRoleForm.name.trim() || !newRoleForm.content.trim()">
        {{ isEditingRole ? '确认修改' : '确认添加' }}
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { User, ChatDotRound, Loading, CircleCheck, Hide, View, Plus, Edit, Delete  } from '@element-plus/icons-vue'
import axios from 'axios'
import * as echarts from 'echarts'

const selectedModel = ref('')
const modelList = ref([])
const messages = ref([])
const userInput = ref('')
const isStreaming = ref(false)
const messagesRef = ref(null)
const isModelLoading = ref(false)
const isModelLoaded = ref(false)
const modelLoadError = ref('')
let displayInterval = null
let isThinking = ref(false)
const thinkingMode = ref(false)

const showRightPanel = ref(true)

const scrollToBottom = () => {
  nextTick(() => {
    if (messagesRef.value) {
      messagesRef.value.scrollTop = messagesRef.value.scrollHeight
    }
  })
}

const displayCharByChar = (fullContent) => {
  if (displayInterval) {
    clearInterval(displayInterval)
  }
  isThinking.value = false

  // 以"</think>"为关键字分割：思考内容放入可折叠区域，只逐字展示回答部分
  let thinkingContent = ''
  let contentToShow = fullContent
  const thinkKeyword = '</think>'
  const thinkIdx = fullContent.indexOf(thinkKeyword)
  if (thinkIdx !== -1) {
    thinkingContent = fullContent.substring(0, thinkIdx).trim()
    contentToShow = fullContent.substring(thinkIdx + thinkKeyword.length)
  }

  const content = contentToShow.replace(/^\n+/, '').replace(/\n+$/, '')
  const lastMsg = messages.value[messages.value.length - 1]
  if (lastMsg.role !== 'assistant') return

  // 保存思考内容和折叠状态
  lastMsg.thinkingContent = thinkingContent || ''
  lastMsg.thinking = thinkingContent || ''
  lastMsg.showThinking = false

  lastMsg.content = ''

  let index = 0
  displayInterval = setInterval(() => {
    if (index < content.length) {
      lastMsg.content += content[index]
      index++
      scrollToBottom()
    } else {
      clearInterval(displayInterval)
      displayInterval = null
      lastMsg.isStreaming = false
    }
  }, 30)
}

const showPerplexity = ref(true)
const perplexityChartRef = ref(null)
let perplexityChartInstance = null
const perplexityData = ref([])

const showNewChatPanel = ref(false)
const newChatFolder = ref('')
const newChatModel = ref('')
const newChatSession = ref('')
const folderList = ref([])
const modelFileList = ref([])

// 角色管理
const selectedRole = ref('none')
const showAddRoleDialog = ref(false)
const editingRole = ref(null)  // 正在编辑的角色，null=新建模式
const isEditingRole = computed(() => editingRole.value !== null)
const currentChatName = computed(() => {
  if (!selectedModel.value) return '当前对话'
  const parts = selectedModel.value.split('|')
  return parts[1] || '当前对话'
})
const newRoleForm = reactive({
  name: '',
  content: ''
})

// 初始只包含"无"，后续从后端加载
const roleList = ref([
  { id: 'none', name: '无（普通对话）', content: '' }
])

// 从后端加载角色列表
async function loadRoleList() {
  try {
    const res = await axios.get('/api/data/roles')
    const roles = res.data || []
    roleList.value = [
      { id: 'none', name: '无（普通对话）', content: '' },
      ...roles
    ]
  } catch (e) {
    console.error('加载角色列表失败', e)
  }
}

const roleplayParams = {
  temperature: 1.15,
  top_p: 0.9,
  top_k: 60,
  alpha_frequency: 0.3,
  alpha_presence: 0.15,
  alpha_decay: 0.40
}

const onRoleChange = async (val) => {
  if (val === 'none') {
    // 恢复默认参数
    Object.assign(inferParams, defaultParams)
    isParamsSynced.value = false
    ElMessage.info('已切换为普通对话模式，推理参数已恢复默认')
  } else {
    const role = roleList.value.find(r => r.id === val)
    if (role) {
      // 切换到角色扮演推荐参数
      Object.assign(inferParams, roleplayParams)
      isParamsSynced.value = false
      ElMessage.success(`已切换角色：${role.name}，推理参数已调整为角色扮演模式`)
    }
  }

  // 持久化 role_id 到当前对话的 .json 文件
  if (selectedModel.value) {
    const parts = selectedModel.value.split('|')
    const modelPath = parts[0]
    const session = parts[1] || ''
    const pathParts = modelPath.split('/')
    if (pathParts.length >= 2) {
      const folder = pathParts[0]
      const model = pathParts[1]
      try {
        await axios.put('/api/data/chat-data', {
          folder,
          model,
          session,
          params: { ...inferParams },
          role_id: val
        })
      } catch (e) {
        console.error('保存角色信息失败', e)
      }
    }
  }
}

const confirmDeleteRole = async (role) => {
  try {
    await ElMessageBox.confirm(`确定要删除角色 "${role.name}" 吗？`, '删除确认', {
      confirmButtonText: '确定删除',
      cancelButtonText: '取消',
      type: 'warning'
    })
    await axios.delete(`/api/data/roles/${role.id}`)
    roleList.value = roleList.value.filter(r => r.id !== role.id)
    if (selectedRole.value === role.id) {
      selectedRole.value = 'none'
    }
    ElMessage.success('角色已删除')
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

const handleEditRole = (role) => {
  editingRole.value = role
  newRoleForm.name = role.name
  newRoleForm.content = role.content
  showAddRoleDialog.value = true
}

const closeRoleDialog = () => {
  showAddRoleDialog.value = false
  editingRole.value = null
  newRoleForm.name = ''
  newRoleForm.content = ''
}

const confirmAddRole = async () => {
  const name = newRoleForm.name.trim()
  const content = newRoleForm.content.trim()
  if (!name || !content) {
    ElMessage.warning('请填写角色名称和设定')
    return
  }
  const id = isEditingRole.value ? editingRole.value.id : 'custom_' + Date.now()
  try {
    await axios.post('/api/data/roles', { id, name, content })
    await loadRoleList()
    if (!isEditingRole.value) {
      selectedRole.value = id
      onRoleChange(id)  // 手动触发，应用角色卡的推理参数
    }
    closeRoleDialog()
    ElMessage.success(isEditingRole.value ? `角色「${name}」已更新` : `角色「${name}」已创建并切换`)
  } catch (e) {
    ElMessage.error(isEditingRole.value ? '编辑角色失败' : '创建角色失败')
  }
}

const loadCheckpointFolders = async () => {
  try {
    const res = await axios.get('/api/data/checkpoint-folders')
    folderList.value = res.data
  } catch (error) {
    console.error('获取文件夹列表失败', error)
  }
}

const loadCheckpointFiles = async (folder) => {
  try {
    const res = await axios.get('/api/data/checkpoint-files', { params: { folder } })
    modelFileList.value = res.data
  } catch (error) {
    console.error('获取模型文件列表失败', error)
  }
}

const loadBaseModelFiles = async () => {
  try {
    const res = await axios.get('/api/data/base-model-files')
    modelFileList.value = res.data
  } catch (error) {
    console.error('获取基底模型文件列表失败', error)
  }
}

const inferParams = reactive({
  model: '',
  max_tokens: 2048,
  clean_rounds: 10,
  temperature: 1,
  top_p: 0.85,
  top_k: 0,
  alpha_frequency: 0.2,
  alpha_presence: 0.2,
  alpha_decay: 0.996,
  max_rounds: 5,
})

const isParamsSynced = ref(true)
const isSavingParams = ref(false)
const isLoadingParams = ref(false)

const defaultParams = {
  max_tokens: 2048,
  clean_rounds: 10,
  temperature: 1,
  top_p: 0.85,
  top_k: 0,
  alpha_frequency: 0.2,
  alpha_presence: 0.2,
  alpha_decay: 0.996,
  max_rounds: 5,
}

const loadModels = async () => {
  try {
    const res = await axios.get('/api/data/chat-models')
    modelList.value = res.data
    if (modelList.value.length > 0) {
      isLoadingParams.value = true
      const first = modelList.value[0]
      selectedModel.value = first.model + '|' + (first.session || '')
      inferParams.model = first.model
      if (first.params) {
        Object.assign(inferParams, first.params)
      }
      isParamsSynced.value = true
      isLoadingParams.value = false
      await onModelChange(selectedModel.value)
    } else {
      selectedModel.value = ''
      inferParams.model = ''
      isModelLoaded.value = false
    }
  } catch (error) {
    console.error('获取模型列表失败', error)
    modelList.value = []
    selectedModel.value = ''
    inferParams.model = ''
    isModelLoaded.value = false
  }
}

const onModelChange = async (value) => {
  const parts = value.split('|')
  const modelPath = parts[0]
  const session = parts[1] || ''

  const item = modelList.value.find(i => i.model === modelPath && i.session === session)
  if (item) {
    isLoadingParams.value = true
    inferParams.model = modelPath
    if (item.params) {
      Object.assign(inferParams, item.params)
    }
    isParamsSynced.value = true
    isLoadingParams.value = false
  }

  // 切换模型时默认关闭思考模式
  thinkingMode.value = false

  isModelLoading.value = true
  isModelLoaded.value = false
  modelLoadError.value = ''

  try {
    await axios.post('/api/chat/preload-model', null, { params: { model: modelPath } })
    isModelLoaded.value = true
  } catch (error) {
    modelLoadError.value = error.response?.data?.detail || '模型加载失败'
    isModelLoaded.value = false
  } finally {
    isModelLoading.value = false
  }

  const pathParts = modelPath.split('/')
  if (pathParts.length >= 2) {
    const folder = pathParts[0]
    const modelName = pathParts[1].replace('.pth', '')
    try {
      const res = await axios.get('/api/data/chat-data', {
        params: { folder, model: modelName, session: session }
      })
      messages.value = res.data['dialogue-content'] || []
      // 加载历史消息，处理思考内容（兼容新旧两种格式）
      messages.value.forEach(msg => {
        if (msg.role === 'assistant') {
          if (msg.thinking) {
            // 新格式：后端已切分，thinking 在独立字段
            msg.thinkingContent = msg.thinking
            msg.showThinking = false
          } else if (msg.content && !msg.thinkingContent) {
            // 旧格式兼容：从 content 中解析 " response" 关键字
            const thinkKeyword = ' response'
            const thinkIdx = msg.content.indexOf(thinkKeyword)
            if (thinkIdx !== -1) {
              msg.thinkingContent = msg.content.substring(0, thinkIdx).trim()
              msg.content = msg.content.substring(thinkIdx + thinkKeyword.length)
              msg.showThinking = false
            }
          }
        }
      })
      scrollToBottom()

      // 恢复角色选择
      const savedRoleId = res.data['role_id']
      selectedRole.value = savedRoleId && savedRoleId !== 'none' ? savedRoleId : 'none'
    } catch (error) {
      messages.value = []
    }
  }
}

const confirmDeleteChat = async (item) => {
  try {
    const displayName = item.model + '-' + (item.session || '')
    await ElMessageBox.confirm(`确定要删除对话 "${displayName}" 吗？此操作不可恢复！`, '删除确认', {
      confirmButtonText: '确定删除',
      cancelButtonText: '取消',
      type: 'warning'
    })
    await deleteChat(item)
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(error.response?.data?.detail || '删除失败')
    }
  }
}

const deleteChat = async (item) => {
  try {
    const modelPath = item.model
    const parts = modelPath.split('/')
    const folder = parts[0]
    const modelFile = parts[1]
    const modelName = modelFile.replace('.pth', '')
    await axios.delete(`/api/data/chat-data`, {
      params: { folder: folder, model: modelName, session: item.session }
    })
    ElMessage.success('对话已删除')
    await loadModels()
  } catch (error) {
    console.error('删除对话失败', error)
    ElMessage.error(error.response?.data?.detail || '删除失败')
  }
}

const loadParams = () => {
  const saved = localStorage.getItem('inferParams')
  if (saved) {
    const parsed = JSON.parse(saved)
    Object.assign(inferParams, parsed)
    selectedModel.value = inferParams.model
  }
}

const saveParams = () => {
  localStorage.setItem('inferParams', JSON.stringify(inferParams))
  ElMessage.success('参数已保存')
}

const resetParams = () => {
  isLoadingParams.value = true
  Object.assign(inferParams, defaultParams)
  isLoadingParams.value = false
  ElMessage.success('已重置为默认参数')
}

const handleNewChat = async () => {
  showNewChatPanel.value = !showNewChatPanel.value
  if (showNewChatPanel.value) {
    newChatFolder.value = ''
    newChatModel.value = ''
    newChatSession.value = ''
    modelFileList.value = []
    if (folderList.value.length === 0) {
      await loadCheckpointFolders()
    }
    // 添加基底模型选项到文件夹列表
    if (!folderList.value.includes('base_models')) {
      folderList.value.unshift('base_models')
    }
  }
}

const saveChatData = async (folder, model, session, params) => {
  try {
    await axios.post('/api/data/chat-data', {
      folder: folder,
      model: model,
      session: session,
      params: params,
    })
  } catch (error) {
    console.error('保存对话数据失败', error)
    ElMessage.error('保存对话数据失败，请查看控制台日志')
  }
}

const confirmNewChat = async () => {
  if (!newChatFolder.value || !newChatModel.value || !newChatSession.value) {
    ElMessage.warning('请选择文件夹、模型文件并输入对话名称')
    return
  }
  const params = defaultParams
  await saveChatData(newChatFolder.value, newChatModel.value, newChatSession.value, params)
  await loadModels()
  const fullModelPath = newChatFolder.value + '/' + newChatModel.value
  selectedModel.value = fullModelPath + '|' + newChatSession.value
  inferParams.model = fullModelPath
  messages.value = []
  await onModelChange(selectedModel.value)
  Object.assign(inferParams, defaultParams)
  showNewChatPanel.value = false
  ElMessage.success('新对话已创建')
}

const cancelNewChat = () => {
  showNewChatPanel.value = false
}

const clearHistory = async () => {
  if (!selectedModel.value) {
    ElMessage.warning('请先选择一个对话')
    return
  }
  try {
    const parts = selectedModel.value.split('|')
    const modelPath = parts[0]
    const session = parts[1] || ''
    const pathParts = modelPath.split('/')
    const folder = pathParts[0]
    const modelName = pathParts[1].replace('.pth', '')
    await axios.put('/api/data/chat-data/dialogue', {
      folder: folder,
      model: modelName,
      session: session,
      dialogue_content: []
    })
    await axios.post('/api/chat/reset-state', { model: selectedModel.value })
    messages.value = []
    ElMessage.success('历史记录已清空')
  } catch (error) {
    console.error('清空历史记录失败', error)
    ElMessage.error('清空失败')
  }
}

const onFolderChange = async (val) => {
  newChatModel.value = ''
  if (val) {
    if (val === 'base_models') {
      await loadBaseModelFiles()
    } else {
      await loadCheckpointFiles(val)
    }
  }
}

const handleEnterKey = (e) => {
  if (e.shiftKey) {
    return
  }
  e.preventDefault()
  sendMessage()
}

const generateResponse = async (userMessageContent, isNewMessage = true, isRegenerate = false) => {
  if (isNewMessage) {
    messages.value.push({ role: 'user', content: userMessageContent })
    scrollToBottom()
  }
  messages.value.push({ role: 'assistant', content: '', isStreaming: true })
  scrollToBottom()
  isThinking.value = true

  const parts = selectedModel.value.split('|')
  const modelPath = parts[0]
  const pathParts = modelPath.split('/')
  const folder = pathParts[0]

  try {
    // 如果有选中角色，在历史消息前插入 system 消息作为角色卡
    let historyMessages = messages.value.slice(0, -2)
    if (selectedRole.value && selectedRole.value !== 'none') {
      const roleCard = roleList.value.find(r => r.id === selectedRole.value)
      if (roleCard && roleCard.content) {
        historyMessages = [
          { role: 'system', content: roleCard.content },
          ...historyMessages
        ]
      }
    }

    const apiUrl = isRegenerate ? '/api/chat/regenerate' : '/api/chat/chat'
    const response = await fetch(apiUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        model: selectedModel.value,
        message: userMessageContent,
        messages: historyMessages,
        params: {
          max_tokens: inferParams.max_tokens,
          temperature: inferParams.temperature,
          top_p: inferParams.top_p,
          top_k: inferParams.top_k,
          alpha_frequency: inferParams.alpha_frequency,
          alpha_presence: inferParams.alpha_presence,
          alpha_decay: inferParams.alpha_decay,
          max_rounds: inferParams.max_rounds,
        },
        thinking_mode: thinkingMode.value,
      })
    })

    const reader = response.body.getReader()
    const decoder = new TextDecoder()

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      const chunk = decoder.decode(value, { stream: true })
      const lines = chunk.split('\n')

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6).trim()
          if (data === '[FINAL]') {
            reader.cancel()
            const res = await axios.get('/api/data/temp-txt', { params: { folder } })
            displayCharByChar(res.data.content)
            return
          }
        }
      }
    }

    const res = await axios.get('/api/data/temp-txt', { params: { folder } })
    displayCharByChar(res.data.content)
  } catch (error) {
    isThinking.value = false
    console.error('发送消息失败', error)
    ElMessage.error('发送失败')
  }
}

const sendMessage = async () => {
  if (!userInput.value.trim() || !selectedModel.value) {
    ElMessage.warning('请选择模型并输入内容')
    return
  }

  const userMessage = userInput.value.trim()
  userInput.value = ''
  await generateResponse(userMessage, true)
}

const regenerateLastMessage = async () => {
  if (!selectedModel.value || isModelLoading.value) return

  if (messages.value.length < 2) {
    ElMessage.warning('没有可重新生成的消息')
    return
  }

  const lastMsg = messages.value[messages.value.length - 1]
  if (lastMsg.role !== 'assistant') {
    ElMessage.warning('最后一条消息不是助手回复')
    return
  }

  messages.value.pop()
  const userMsg = messages.value[messages.value.length - 1]
  if (userMsg.role !== 'user') {
    ElMessage.warning('未找到对应的用户消息')
    return
  }

  await generateResponse(userMsg.content, false, true)
}

const lastUserMessageIndex = computed(() => {
  for (let i = messages.value.length - 1; i >= 0; i--) {
    if (messages.value[i].role === 'user') {
      return i
    }
  }
  return -1
})

const isGenerating = computed(() => {
  if (isThinking.value) return true
  if (messages.value.length === 0) return false
  const lastMsg = messages.value[messages.value.length - 1]
  if (lastMsg.role === 'assistant' && lastMsg.isStreaming) return true
  return false
})

const reEditLastMessage = () => {
  if (!selectedModel.value || isModelLoading.value) return

  const lastUserIndex = lastUserMessageIndex.value
  if (lastUserIndex === -1) {
    ElMessage.warning('没有可重新编辑的消息')
    return
  }

  const userMsg = messages.value[lastUserIndex]
  messages.value = messages.value.slice(0, lastUserIndex)
  userInput.value = userMsg.content

  nextTick(() => {
    const textarea = document.querySelector('.chat-input-area textarea')
    if (textarea) textarea.focus()
  })
}

// 滑动窗口边界：模型记住的对话起始位置（镜像后端 build_prompt 逻辑）
const windowBoundaryIndex = computed(() => {
  const maxRounds = inferParams.max_rounds || 5
  const msgs = messages.value
  if (msgs.length === 0) return -1

  // 跳过首条 system 角色卡
  const convStart = msgs[0] && msgs[0].role === 'system' ? 1 : 0
  const convLen = msgs.length - convStart
  const maxMessages = maxRounds * 2 + 1  // N轮完整对话 + 当前用户消息

  if (convLen > maxMessages) {
    // 第一个被模型记住的消息在原始数组中的索引
    return convStart + convLen - maxMessages
  }
  return -1  // 无需分割
})

// 判断在 index 位置前是否要显示分割线
function showDividerBefore(index) {
  return index === windowBoundaryIndex.value
}

const formatMessage = (content) => {
  if (!content) return ''
  return content.replace(/\n/g, '<br>')
}

const updatePerplexityChart = () => {
  if (!perplexityChartRef.value) return

  if (!perplexityChartInstance) {
    perplexityChartInstance = echarts.init(perplexityChartRef.value)
  }

  const data = perplexityData.value.map((val, idx) => [idx, val])

  const option = {
    tooltip: {
      trigger: 'axis',
      formatter: (params) => {
        const point = params[0]
        return `Token: ${point.value[0]}<br/>惊讶度: ${point.value[1]?.toFixed(2)}`
      }
    },
    grid: {
      left: '5%',
      right: '5%',
      top: '10%',
      bottom: '15%'
    },
    xAxis: {
      type: 'value',
      name: 'Token',
      nameLocation: 'middle',
      nameGap: 20,
      min: 0,
      splitLine: { show: false },
      axisLine: { lineStyle: { color: '#333' } }
    },
    yAxis: {
      type: 'value',
      name: 'PPL',
      min: 0,
      max: 20,
      splitLine: {
        lineStyle: { type: 'dashed', color: '#bbb' }
      },
      axisLine: { lineStyle: { color: '#333' } }
    },
    series: [{
      type: 'line',
      smooth: 0.3,
      symbol: 'none',
      data: data,
      lineStyle: {
        color: '#2ecc71',
        width: 1.5
      },
      areaStyle: null
    }]
  }

  perplexityChartInstance.setOption(option)
  perplexityChartInstance.resize()
}

watch(showPerplexity, (val) => {
  if (val) {
    nextTick(() => {
      updatePerplexityChart()
    })
  }
})

watch(() => inferParams, async () => {
  if (!selectedModel.value || isParamsSynced.value === false || isLoadingParams.value) return

  const parts = selectedModel.value.split('|')
  const modelPath = parts[0]
  const session = parts[1] || ''

  const pathParts = modelPath.split('/')
  if (pathParts.length < 2) return

  const folder = pathParts[0]
  const model = pathParts[1]

  isSavingParams.value = true

  try {
    await axios.put('/api/data/chat-data', {
      folder: folder,
      model: model,
      session: session,
      params: {
        max_tokens: inferParams.max_tokens,
        clean_rounds: inferParams.clean_rounds,
        temperature: inferParams.temperature,
        top_p: inferParams.top_p,
        top_k: inferParams.top_k,
        alpha_frequency: inferParams.alpha_frequency,
        alpha_presence: inferParams.alpha_presence,
        alpha_decay: inferParams.alpha_decay,
        max_rounds: inferParams.max_rounds,
      },
    })

    await axios.put('/api/chat/update-params', {
      params: {
        max_tokens: inferParams.max_tokens,
        clean_rounds: inferParams.clean_rounds,
        temperature: inferParams.temperature,
        top_p: inferParams.top_p,
        top_k: inferParams.top_k,
        alpha_frequency: inferParams.alpha_frequency,
        alpha_presence: inferParams.alpha_presence,
        alpha_decay: inferParams.alpha_decay,
        max_rounds: inferParams.max_rounds,
      }
    })

    isParamsSynced.value = true
  } catch (error) {
    console.error('保存参数失败', error)
  } finally {
    isSavingParams.value = false
  }
}, { deep: true })

onMounted(() => {
  loadModels()
  loadParams()
  loadCheckpointFolders()
  loadRoleList()
})

onUnmounted(() => {
  if (perplexityChartInstance) {
    perplexityChartInstance.dispose()
    perplexityChartInstance = null
  }
})
</script>

<style scoped>
.content-wrapper {
  display: flex;
  gap: 20px;
  height: calc(100vh - 140px);
}

.left-panel {
  flex: 2;
  display: flex;
  flex-direction: column;
}

.right-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 20px;
  overflow-y: auto;
}

.chat-card {
  flex: 1;
  display: flex;
  flex-direction: column;
  position: relative;
}

.chat-card :deep(.el-card__body) {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 0;
}

.chat-header {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
}

.model-status {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 14px;
  padding: 5px 10px;
  border-radius: 4px;
}

.model-status.loading {
  color: #e6a23c;
}

.model-status.error {
  color: #f56c6c;
}

.model-status.success {
  color: #67c23a;
}

.model-status .loading-icon {
  animation: spin 1s linear infinite;
}

.model-option {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  padding-right: 5px;
}

.model-option-label {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 250px;
}

.model-option-delete {
  flex-shrink: 0;
  margin-left: 10px;
}

.role-option {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
}

.role-option-label {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.role-option-buttons {
  display: flex;
  align-items: center;
  gap: 2px;
  flex-shrink: 0;
  margin-left: 12px;
}

.role-option-btn {
  flex-shrink: 0;
}

.new-chat-panel {
  position: absolute;
  top: 56px;
  left: 0;
  right: 0;
  z-index: 10;
  padding: 10px 15px;
  background: #fff;
  border-bottom: 1px solid #eee;
  display: flex;
  align-items: center;
  gap: 10px;
}

.new-chat-panel-label {
  font-size: 14px;
  font-weight: 500;
  color: #606266;
  white-space: nowrap;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  background: #fafafa;
}

.empty-chat {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* 滑动窗口分割线 */
.memory-divider {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 0 16px 0;
  user-select: none;
  opacity: 0.7;
}

.memory-divider .divider-line {
  flex: 1;
  height: 1px;
  background: linear-gradient(to right, transparent, #c0c4cc, transparent);
}

.memory-divider .divider-text {
  font-size: 12px;
  color: #909399;
  white-space: nowrap;
  letter-spacing: 0.5px;
}

.message-item {
  display: flex;
  margin-bottom: 20px;
}

.message-item.user {
  flex-direction: row-reverse;
}

.message-avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: #409eff;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  flex-shrink: 0;
}

.message-item.assistant .message-avatar {
  background: #67c23a;
}

.message-content {
  max-width: 70%;
  margin: 0 10px;
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
}

.message-text {
  display: inline;
  padding: 12px 16px;
  border-radius: 8px;
  background: white;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  line-height: 1.6;
  word-wrap: break-word;
  text-align: left;
}

.message-item.user .message-text {
  background: #409eff;
  color: white;
}

.thinking-indicator {
  margin-top: 5px;
  color: #909399;
  font-size: 14px;
}

/* 可折叠思考过程 */
.thinking-collapse {
  margin-bottom: 8px;
  background: #f8f9fc;
  border-radius: 6px;
  border: 1px solid #e8eaef;
  overflow: hidden;
  width: 100%;
}

.thinking-header {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 10px;
  cursor: pointer;
  user-select: none;
  font-size: 13px;
  color: #606266;
  transition: background 0.2s;
}

.thinking-header:hover {
  background: #eef0f5;
}

.thinking-toggle {
  font-size: 10px;
  color: #909399;
  width: 12px;
  text-align: center;
}

.thinking-label {
  font-weight: 500;
}

.thinking-body {
  padding: 0 10px 8px 10px;
  border-top: 1px dashed #e0e2e8;
}

.thinking-text {
  margin-top: 6px;
  font-size: 13px;
  color: #7a7f8a;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
  text-align: left;
}

.cursor {
  animation: blink 1s infinite;
  color: #409eff;
  font-weight: bold;
}

@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}

.chat-input-area {
  padding: 15px;
  border-top: 1px solid #eee;
  background: white;
  display: flex;
  gap: 10px;
}

.chat-input-area :deep(.el-textarea) {
  flex: 1;
  font-size: 16px;
}

.send-btn {
  height: auto;
}

.send-btn .btn-text {
  display: flex;
  flex-direction: column;
  align-items: center;
  line-height: 1.3;
}

.send-btn .btn-sub {
  font-size: 11px;
  opacity: 0.8;
}

.param-card {
  flex-shrink: 0;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-header-title {
  display: flex;
  align-items: center;
  gap: 8px;
}

.synced-icon {
  color: #67c23a;
  font-size: 18px;
}

.syncing-icon {
  color: #e6a23c;
  font-size: 18px;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.empty-placeholder {
  text-align: center;
  color: #909399;
  padding: 40px 0;
}

.perplexity-chart {
  height: 150px;
}

.infer-form :deep(.el-form-item__label) {
  font-weight: 500;
}

.slider-container {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
}

.slider-container :deep(.el-slider) {
  flex: 1;
}

.slider-value {
  min-width: 45px;
  text-align: right;
  font-size: 13px;
  color: #606266;
}

.message-left {
  display: flex;
  flex-direction: column;
  align-items: center;
  flex-shrink: 0;
  margin-right: 10px;
}

.message-item.user .message-left {
  margin-right: 0;
  margin-left: 10px;
}

.message-left .regenerate-btn,
.message-left .re-edit-btn {
  margin-top: 8px;
  width: 100%;
}
</style>>