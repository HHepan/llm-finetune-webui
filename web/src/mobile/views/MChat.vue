<template>
  <div class="m-chat-page">
    <!-- 顶部选择栏 -->
    <div class="m-chat-selectbar">
      <el-select v-model="selectedModel" placeholder="选择对话" size="small" popper-class="m-select-popper" @change="onModelSelect">
        <el-option
          v-for="item in modelList"
          :key="item.model + '|' + item.session"
          :label="item.model + '-' + item.session"
          :value="item.model + '|' + item.session"
        >
          <div style="display:flex;justify-content:space-between;align-items:center;">
            <span style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap;min-width:0;">{{ item.model }}-{{ item.session }}</span>
            <el-button type="danger" size="small" link @click.stop="deleteSelectedChat(item)">删除</el-button>
          </div>
        </el-option>
      </el-select>
      <el-select v-model="selectedRole" placeholder="选择角色" size="small" popper-class="m-select-popper" @change="onRoleChange" :disabled="isModelLoading">
        <el-option v-for="role in roleList" :key="role.id" :value="role.id" :label="role.name">
          <span style="display:flex;justify-content:space-between;align-items:center;width:100%;">
            <span style="font-size:13px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;min-width:0;">{{ role.name }}</span>
            <span v-if="role.id !== 'none'" style="display:flex;gap:4px;flex-shrink:0;">
              <el-button type="primary" size="small" link @mousedown.prevent="handleEditRole(role)" style="font-size:12px;padding:0 4px;">编辑</el-button>
              <el-button type="danger" size="small" link @mousedown.prevent="confirmDeleteRole(role)" style="font-size:12px;padding:0 4px;">删除</el-button>
            </span>
          </span>
        </el-option>
      </el-select>
    </div>

    <!-- 对话消息区 -->
    <div class="m-chat-messages" ref="messagesRef">
      <div v-if="messages.length === 0" class="m-empty">
        <div class="m-empty-icon">💬</div>
        <span>选择模型后开始对话</span>
      </div>
      <template v-for="(msg, index) in messages" :key="index">
        <!-- 滑动窗口分割线 -->
        <div v-if="showDividerBefore(index)" class="m-memory-divider">
          <span class="m-divider-line"></span>
          <span class="m-divider-text">窗口外 · 模型不再记住</span>
          <span class="m-divider-line"></span>
        </div>
        <div
          :id="'msg-' + index"
          class="m-chat-msg"
          :class="msg.role"
        >
          <div class="m-chat-avatar">
            <span v-if="msg.role === 'user'">😊</span>
            <span v-else>🤖</span>
          </div>
          <div class="m-chat-bubble">
            <!-- 可折叠的思考过程 -->
            <div v-if="msg.role === 'assistant' && msg.thinkingContent" class="m-thinking-collapse">
              <div class="m-thinking-header" @click.stop="msg.showThinking = !msg.showThinking">
                <span class="m-thinking-toggle">{{ msg.showThinking ? '▼' : '▶' }}</span>
                <span class="m-thinking-label">💭 思考过程</span>
              </div>
              <div v-show="msg.showThinking" class="m-thinking-body" @click.stop>
                <div class="m-thinking-text" v-html="formatMessage(msg.thinkingContent)"></div>
              </div>
            </div>
            <div class="m-chat-text" v-html="formatMessage(msg.content)"></div>
            <span v-if="msg.role === 'assistant' && msg.isStreaming" class="m-cursor">|</span>
            <div v-if="msg.role === 'assistant' && isThinking && !msg.content" class="m-thinking">思考中...</div>
          </div>
        </div>
      </template>
    </div>

    <!-- 操作按钮组 -->
    <div class="m-chat-toolbar">
      <div class="toolbar-row">
        <el-button size="small" plain @click="showMoreActions = true">更多操作</el-button>
        <el-button size="small" plain @click="regenerateLastMessage" :disabled="!canRegenerate">重生成</el-button>
        <el-button size="small" plain @click="reEditLastMessage" :disabled="!canReEdit">改提问</el-button>
        <el-button
          size="small"
          :plain="!thinkingMode"
          :type="thinkingMode ? 'primary' : 'default'"
          @click="thinkingMode = !thinkingMode"
          class="m-thinking-btn"
          :class="{ 'is-lit': thinkingMode }"
        >
          <span class="m-thinking-btn-icon">💭</span>
          <span>思考</span>
        </el-button>
        <span v-if="isModelLoading" class="m-model-status loading"><span class="m-spinner m-spinner--inline"></span>加载中...</span>
        <span v-else-if="modelLoadError" class="m-model-status error">❌ 加载失败</span>
        <span v-else-if="isModelLoaded && selectedModel" class="m-model-status ready">● 就绪</span>
      </div>
    </div>

    <!-- 输入区 -->
    <div class="m-chat-input">
      <div class="m-chat-input-inner">
        <el-input
          v-model="userInput"
          type="textarea"
          :rows="1"
          placeholder="输入消息..."
          @keydown.enter="handleEnter"
          :disabled="isModelLoading"
          resize="none"
          class="m-chat-textarea"
          autosize
        />
        <button
          class="m-chat-send-btn"
          :class="{ active: userInput.trim() && selectedModel && !isModelLoading }"
          :disabled="!userInput.trim() || !selectedModel || isModelLoading"
          @click="sendMessage"
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
            <line x1="22" y1="2" x2="11" y2="13"/>
            <polygon points="22 2 15 22 11 13 2 9 22 2"/>
          </svg>
        </button>
      </div>
    </div>

    <!-- ====== 更多操作弹窗 ====== -->
    <div v-if="showMoreActions" class="m-modal-overlay" @click.self="showMoreActions = false">
      <div class="m-modal-content">
        <div class="m-modal-header">
          <span>更多操作</span>
          <span class="m-modal-close" @click="showMoreActions = false">&times;</span>
        </div>
        <div class="m-more-actions-list">
          <div class="m-more-action-item" @click="showNewChat = true; showMoreActions = false">
            <span class="m-more-action-icon">+</span>
            <span class="m-more-action-label">新建</span>
          </div>
          <div class="m-more-action-divider"></div>
          <div class="m-more-action-item" @click="clearHistory(); showMoreActions = false">
            <span class="m-more-action-icon">🗑</span>
            <span class="m-more-action-label">清空</span>
          </div>
          <div class="m-more-action-divider"></div>
          <div class="m-more-action-item" @click="showParams = true; showMoreActions = false">
            <span class="m-more-action-icon">⚙</span>
            <span class="m-more-action-label">参数</span>
          </div>
          <div class="m-more-action-divider"></div>
          <div class="m-more-action-item" @click="openRoleDialog(); showMoreActions = false">
            <span class="m-more-action-icon">🎭</span>
            <span class="m-more-action-label">角色</span>
          </div>
        </div>
      </div>
    </div>

    <!-- ====== 新建对话弹窗 ====== -->
    <div v-if="showNewChat" class="m-modal-overlay" @click.self="showNewChat = false">
      <div class="m-modal-content" style="max-height:70vh;">
        <div class="m-modal-header">
          <span>新建对话</span>
          <span class="m-modal-close" @click="showNewChat = false">&times;</span>
        </div>
        <div style="margin-bottom:12px;">
          <el-input v-model="newChatSession" placeholder="对话名称" size="small" />
        </div>
        <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:12px;">
          <el-select v-model="newChatFolder" placeholder="文件夹" size="small" style="flex:1;min-width:80px;" @change="onNewChatFolderChange">
            <el-option v-for="f in folderList" :key="f" :label="f" :value="f" />
          </el-select>
          <el-select v-model="newChatModel" placeholder="模型文件" size="small" style="flex:1;min-width:80px;">
            <el-option v-for="m in modelFileList" :key="m" :label="m" :value="m" />
          </el-select>
        </div>
        <el-button size="small" type="primary" style="width:100%;" @click="confirmNewChat" :disabled="!newChatFolder || !newChatModel || !newChatSession">创建</el-button>
      </div>
    </div>

    <!-- ====== 角色编辑弹窗 ====== -->
    <div v-if="showRoleDialog" class="m-modal-overlay" @click.self="closeRoleDialog">
      <div class="m-modal-content" style="max-height:90vh;">
        <div class="m-modal-header">
          <span>{{ isEditingRole ? '编辑角色' : '新建角色' }}</span>
          <span class="m-modal-close" @click="closeRoleDialog">&times;</span>
        </div>
        <div style="margin-bottom:10px;">
          <div class="m-field-label">角色名称</div>
          <el-input v-model="roleForm.name" placeholder="名称" size="small" />
        </div>
        <div style="margin-bottom:16px;">
          <div class="m-field-label">角色设定</div>
          <el-input v-model="roleForm.content" type="textarea" :rows="18" placeholder="角色设定描述..." size="small" />
        </div>
        <el-button size="small" type="primary" style="width:100%;" @click="confirmRole" :disabled="!roleForm.name || !roleForm.content">
          {{ isEditingRole ? '确认修改' : '确认添加' }}
        </el-button>
      </div>
    </div>

    <!-- ====== 推理参数面板 ====== -->
    <div v-if="showParams" class="m-modal-overlay" @click.self="showParams = false">
      <div class="m-modal-content" style="max-height:85vh;" @focusin="onParamsFocusIn" @focusout="onParamsFocusOut">
        <div class="m-modal-header">
          <span>推理参数</span>
          <div style="display:flex;gap:8px;align-items:center;">
            <el-button size="small" link @click="resetParams">重置</el-button>
            <span class="m-modal-close" @click="showParams = false">&times;</span>
          </div>
        </div>
        <el-form :model="inferParams" label-width="0">
          <div class="m-param-item">
            <div class="m-param-label">max-rounds</div>
            <el-input-number v-model="inferParams.max_rounds" :min="1" :max="100" size="small" style="width:100%;" />
            <div class="m-param-hint">保留最近 N 轮对话，超出部分自动裁剪</div>
          </div>
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:4px;">
            <div>
              <div class="m-param-label">temperature</div>
              <el-input-number v-model="inferParams.temperature" :min="0" :max="2" :step="0.01" :precision="2" size="small" style="width:100%;" />
            </div>
            <div>
              <div class="m-param-label">alpha_frequency</div>
              <el-input-number v-model="inferParams.alpha_frequency" :min="0" :max="1" :step="0.01" :precision="2" size="small" style="width:100%;" />
            </div>
            <div>
              <div class="m-param-label">alpha_presence</div>
              <el-input-number v-model="inferParams.alpha_presence" :min="0" :max="1" :step="0.01" :precision="2" size="small" style="width:100%;" />
            </div>
            <div>
              <div class="m-param-label">alpha_decay</div>
              <el-input-number v-model="inferParams.alpha_decay" :min="0" :max="1" :step="0.001" :precision="3" size="small" style="width:100%;" />
            </div>
          </div>
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:14px;">
            <div>
              <div class="m-param-label">max_tokens</div>
              <el-input-number v-model="inferParams.max_tokens" :min="1" :max="4096" size="small" style="width:100%;" />
            </div>
            <div>
              <div class="m-param-label">clean_rounds</div>
              <el-input-number v-model="inferParams.clean_rounds" :min="1" :max="100" size="small" style="width:100%;" />
            </div>
            <div>
              <div class="m-param-label">top_p</div>
              <el-input-number v-model="inferParams.top_p" :min="0" :max="1" :step="0.01" :precision="2" size="small" style="width:100%;" />
            </div>
            <div>
              <div class="m-param-label">top_k</div>
              <el-input-number v-model="inferParams.top_k" :min="0" :max="200" size="small" style="width:100%;" />
            </div>
          </div>
          <div class="m-param-status">
            <span v-if="isParamsSynced" class="m-param-status-ready">✓ 参数设置完成</span>
            <span v-else class="m-param-status-loading">⏳ 参数设置中...</span>
          </div>
        </el-form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import axios from 'axios'

// ==== 状态 ====
const selectedModel = ref('')
const modelList = ref([])
const messages = ref([])
const userInput = ref('')
const isModelLoading = ref(false)
const isModelLoaded = ref(false)
const modelLoadError = ref('')
const isParamsSynced = ref(true)
const isStreaming = ref(false)
const isThinking = ref(false)
const thinkingMode = ref(false)
const messagesRef = ref(null)
let displayInterval = null

// 面板控制
const showNewChat = ref(false)
const showParams = ref(false)
const showRoleDialog = ref(false)
const showMoreActions = ref(false)

// 新建对话
const newChatFolder = ref('')
const newChatModel = ref('')
const newChatSession = ref('')
const folderList = ref([])
const modelFileList = ref([])

// 角色
const selectedRole = ref('none')
const editingRole = ref(null)
const isEditingRole = ref(false)
const roleForm = reactive({ name: '', content: '' })
const roleList = ref([{ id: 'none', name: '无（普通对话）', content: '' }])

// 推理参数
const inferParams = reactive({
  model: '', max_tokens: 2048, clean_rounds: 10,
  temperature: 1, top_p: 0.85, top_k: 0,
  alpha_frequency: 0.2, alpha_presence: 0.2, alpha_decay: 0.996,
  max_rounds: 15
})

const defaultParams = {
  max_tokens: 2048, clean_rounds: 10,
  temperature: 1, top_p: 0.85, top_k: 0,
  alpha_frequency: 0.2, alpha_presence: 0.2, alpha_decay: 0.996,
  max_rounds: 15
}

const roleplayParams = {
  temperature: 0.6, top_p: 0.7, top_k: 0,
  alpha_frequency: 0.2, alpha_presence: 2.0, alpha_decay: 0.99
}

// ==== 辅助方法 ====
const scrollToBottom = () => {
  nextTick(() => {
    if (messagesRef.value) messagesRef.value.scrollTop = messagesRef.value.scrollHeight
  })
}

const formatMessage = (content) => {
  if (!content) return ''
  return content.replace(/\n/g, '<br>')
}

// 滑动窗口边界：模型记住的对话起始位置（镜像后端 build_prompt 逻辑）
const windowBoundaryIndex = computed(() => {
  const maxRounds = inferParams.max_rounds || 15
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

// ==== API 方法 ====
const loadModels = async () => {
  try {
    const res = await axios.get('/api/data/chat-models')
    modelList.value = res.data
    if (modelList.value.length > 0) {
      const first = modelList.value[0]
      selectedModel.value = first.model + '|' + (first.session || '')
      inferParams.model = first.model
      if (first.params) Object.assign(inferParams, first.params)
      await onModelChange(selectedModel.value)
    } else {
      selectedModel.value = ''
      inferParams.model = ''
      isModelLoaded.value = false
    }
  } catch {
    modelList.value = []
    selectedModel.value = ''
    isModelLoaded.value = false
  }
}

const onModelChange = async (value) => {
  // 切换模型时默认关闭思考模式
  thinkingMode.value = false

  const parts = value.split('|')
  const modelPath = parts[0]
  const session = parts[1] || ''
  const item = modelList.value.find(i => i.model === modelPath && i.session === session)
  if (item) {
    inferParams.model = modelPath
    if (item.params) Object.assign(inferParams, item.params)
  }
  isModelLoading.value = true
  isModelLoaded.value = false
  isParamsSynced.value = false
  modelLoadError.value = ''
  try {
    await axios.post('/api/chat/preload-model', null, { params: { model: modelPath } })
    isModelLoaded.value = true
    isParamsSynced.value = true
  } catch (e) {
    modelLoadError.value = e.response?.data?.detail || '模型加载失败'
  } finally {
    isModelLoading.value = false
  }
  const pathParts = modelPath.split('/')
  if (pathParts.length >= 2) {
    const folder = pathParts[0]
    const modelName = pathParts[1].replace('.pth', '')
    try {
      const res = await axios.get('/api/data/chat-data', { params: { folder, model: modelName, session } })
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
            const thinkKeyword = '</think>'
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
    } catch { messages.value = [] }
  }
}

const onModelSelect = async (value) => {
  await onModelChange(value)
}

const loadCheckpointFolders = async () => {
  try {
    const res = await axios.get('/api/data/checkpoint-folders')
    folderList.value = res.data
    if (!folderList.value.includes('base_models')) folderList.value.unshift('base_models')
  } catch { console.error('获取文件夹列表失败') }
}

const loadCheckpointFiles = async (folder) => {
  try {
    const res = await axios.get('/api/data/checkpoint-files', { params: { folder } })
    modelFileList.value = res.data
  } catch { console.error('获取模型文件失败') }
}

const loadBaseModelFiles = async () => {
  try {
    const res = await axios.get('/api/data/base-model-files')
    modelFileList.value = res.data
  } catch { console.error('获取基底模型文件失败') }
}

const onNewChatFolderChange = async (val) => {
  newChatModel.value = ''
  if (val === 'base_models') await loadBaseModelFiles()
  else await loadCheckpointFiles(val)
}

const saveChatData = async (folder, model, session, params) => {
  try {
    await axios.post('/api/data/chat-data', { folder, model, session, params })
  } catch { console.error('保存对话数据失败') }
}

const handleNewChat = () => {
  showNewChat.value = true
  newChatFolder.value = ''
  newChatModel.value = ''
  newChatSession.value = ''
  modelFileList.value = []
  if (folderList.value.length === 0) loadCheckpointFolders()
}

const confirmNewChat = async () => {
  if (!newChatFolder.value || !newChatModel.value || !newChatSession.value) {
    ElMessage.warning('请填写完整')
    return
  }
  await saveChatData(newChatFolder.value, newChatModel.value, newChatSession.value, defaultParams)
  await loadModels()
  const fullPath = newChatFolder.value + '/' + newChatModel.value
  selectedModel.value = fullPath + '|' + newChatSession.value
  inferParams.model = fullPath
  messages.value = []
  Object.assign(inferParams, defaultParams)
  await onModelChange(selectedModel.value)
  ElMessage.success('新对话已创建')
}

const deleteSelectedChat = async (item) => {
  try {
    await ElMessageBox.confirm(`确定删除 "${item.model}-${item.session}" 吗？`, '确认', { confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning' })
    const parts = item.model.split('/')
    const folder = parts[0]
    const modelName = parts[1].replace('.pth', '')
    await axios.delete('/api/data/chat-data', { params: { folder, model: modelName, session: item.session } })
    ElMessage.success('对话已删除')
    await loadModels()
  } catch (e) { if (e !== 'cancel') ElMessage.error('删除失败') }
}

const clearHistory = async () => {
  if (!selectedModel.value) { ElMessage.warning('请先选择对话'); return }
  try {
    await ElMessageBox.confirm('确定要清空当前对话的全部记录吗？', '确认清空', { confirmButtonText: '确定清空', cancelButtonText: '取消', type: 'warning' })
  } catch { return }
  try {
    const parts = selectedModel.value.split('|')
    const modelPath = parts[0]
    const session = parts[1] || ''
    const pathParts = modelPath.split('/')
    const folder = pathParts[0]
    const modelName = pathParts[1].replace('.pth', '')
    await axios.put('/api/data/chat-data/dialogue', { folder, model: modelName, session, dialogue_content: [] })
    await axios.post('/api/chat/reset-state')
    messages.value = []
    ElMessage.success('已清空')
  } catch { ElMessage.error('清空失败') }
}

// ==== 角色 ====
const loadRoleList = async () => {
  try {
    const res = await axios.get('/api/data/roles')
    roleList.value = [{ id: 'none', name: '无（普通对话）', content: '' }, ...(res.data || [])]
  } catch { console.error('加载角色失败') }
}

const onRoleChange = (val) => {
  isParamsSynced.value = false
  if (val === 'none') {
    Object.assign(inferParams, defaultParams)
    ElMessage.info('已切换为普通对话模式，推理参数已恢复默认')
  } else {
    const role = roleList.value.find(r => r.id === val)
    if (role) {
      Object.assign(inferParams, roleplayParams)
      ElMessage.success(`已切换角色：${role.name}，推理参数已调整为角色扮演模式`)
    }
  }
  // 参数应用完毕后标记为就绪
  nextTick(() => { isParamsSynced.value = true })
}

const openRoleDialog = () => {
  editingRole.value = null
  isEditingRole.value = false
  roleForm.name = ''
  roleForm.content = ''
  showRoleDialog.value = true
}

const closeRoleDialog = () => {
  showRoleDialog.value = false
  editingRole.value = null
  isEditingRole.value = false
  roleForm.name = ''
  roleForm.content = ''
}

const confirmRole = async () => {
  const name = roleForm.name.trim()
  const content = roleForm.content.trim()
  if (!name || !content) { ElMessage.warning('请填写完整'); return }
  const id = editingRole.value ? editingRole.value.id : 'custom_' + Date.now()
  try {
    await axios.post('/api/data/roles', { id, name, content })
    await loadRoleList()
    if (!editingRole.value) {
      selectedRole.value = id
      onRoleChange(id)
    }
    closeRoleDialog()
    ElMessage.success(editingRole.value ? '角色已更新' : '角色已创建')
  } catch { ElMessage.error('操作失败') }
}

const handleEditRole = (role) => {
  editingRole.value = role
  isEditingRole.value = true
  roleForm.name = role.name
  roleForm.content = role.content
  showRoleDialog.value = true
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
    if (error !== 'cancel') ElMessage.error('删除失败')
  }
}

// ==== 对话 ====
const handleEnter = (e) => {
  if (e.shiftKey) return
  e.preventDefault()
  sendMessage()
}

const displayCharByChar = (fullContent) => {
  if (displayInterval) clearInterval(displayInterval)
  isThinking.value = false

  // 以" response"为关键字分割：思考内容放入可折叠区域，只逐字展示回答部分
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
  if (!lastMsg || lastMsg.role !== 'assistant') return

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

const lastUserMessageIndex = computed(() => {
  for (let i = messages.value.length - 1; i >= 0; i--) {
    if (messages.value[i].role === 'user') return i
  }
  return -1
})

const isGenerating = computed(() => {
  if (isThinking.value) return true
  if (messages.value.length === 0) return false
  const lastMsg = messages.value[messages.value.length - 1]
  return lastMsg.role === 'assistant' && lastMsg.isStreaming
})

const canRegenerate = computed(() => {
  if (!selectedModel.value || isModelLoading.value || isGenerating.value) return false
  if (messages.value.length < 2) return false
  const lastMsg = messages.value[messages.value.length - 1]
  return lastMsg.role === 'assistant'
})

const canReEdit = computed(() => {
  if (!selectedModel.value || isModelLoading.value || isGenerating.value) return false
  return lastUserMessageIndex.value !== -1
})

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
    // 重生成时：messages = [..., userMsg, assistant占位符]，slice(0,-2) 排除 userMsg 避免重复
    // 正常发送时：messages = [..., userMsg, assistant占位符]，slice(0,-2) 一样排除 userMsg
    let historyMessages = messages.value.slice(0, -2)
    if (selectedRole.value && selectedRole.value !== 'none') {
      const roleCard = roleList.value.find(r => r.id === selectedRole.value)
      if (roleCard && roleCard.content) {
        historyMessages = [{ role: 'system', content: roleCard.content }, ...historyMessages]
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
          max_rounds: inferParams.max_rounds
        },
        thinking_mode: thinkingMode.value
      })
    })

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      const chunk = decoder.decode(value, { stream: true })
      for (const line of chunk.split('\n')) {
        if (line.startsWith('data: ') && line.slice(6).trim() === '[FINAL]') {
          reader.cancel()
          const res = await axios.get('/api/data/temp-txt', { params: { folder } })
          displayCharByChar(res.data.content)
          return
        }
      }
    }
    const res = await axios.get('/api/data/temp-txt', { params: { folder } })
    displayCharByChar(res.data.content)
  } catch (error) {
    isThinking.value = false
    console.error('发送失败', error)
    ElMessage.error('发送失败')
  }
}

const sendMessage = async () => {
  if (!userInput.value.trim() || !selectedModel.value) return
  const text = userInput.value.trim()
  userInput.value = ''
  await generateResponse(text, true)
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

const reEditLastMessage = () => {
  if (!selectedModel.value || isModelLoading.value) return
  const idx = lastUserMessageIndex.value
  if (idx === -1) {
    ElMessage.warning('没有可重新编辑的消息')
    return
  }
  const userMsg = messages.value[idx]
  messages.value = messages.value.slice(0, idx)
  userInput.value = userMsg.content
  nextTick(() => scrollToBottom())
}

const resetParams = () => {
  Object.assign(inferParams, defaultParams)
  ElMessage.success('已重置')
}

// 参数弹窗：输入框获焦时滚动到可视区域，避免键盘遮挡
const onParamsFocusIn = (e) => {
  const target = e.target
  setTimeout(() => {
    target?.scrollIntoView?.({ block: 'start', behavior: 'smooth' })
  }, 350)
}

onMounted(() => {
  loadModels()
  loadRoleList()
  loadCheckpointFolders()
})

onUnmounted(() => {
  if (displayInterval) clearInterval(displayInterval)
})
</script>

<style scoped>
.m-chat-page {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 48px - 56px - 24px);
  height: calc(100dvh - 48px - 56px - 24px);
  padding-bottom: 0;
}

/* 顶部选择栏 */
.m-chat-selectbar {
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 6px 0 10px;
}

.m-chat-selectbar .el-select {
  width: 100%;
}

/* 角色选项行 */
.m-role-option {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}
.m-role-label {
  font-size: 13px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.m-role-btns {
  display: flex;
  gap: 4px;
  flex-shrink: 0;
}
.m-role-btns .el-button {
  font-size: 12px;
  padding: 0 4px;
}

/* 消息区 */
.m-chat-messages {
  flex: 1;
  overflow-y: auto;
  -webkit-overflow-scrolling: touch;
  padding: 4px 2px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

/* 单条消息 */
.m-chat-msg {
  display: flex;
  gap: 10px;
  max-width: 92%;
  animation: msgIn 0.25s ease;
}

@keyframes msgIn {
  from { opacity: 0; transform: translateY(6px); }
  to { opacity: 1; transform: translateY(0); }
}

.m-chat-msg.assistant {
  align-self: flex-start;
}

.m-chat-msg.user {
  align-self: flex-end;
  flex-direction: row-reverse;
}

.m-chat-avatar {
  flex-shrink: 0;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: var(--c-border-light);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 15px;
}

.m-chat-msg.user .m-chat-avatar {
  background: var(--c-primary-soft);
}

.m-chat-msg.assistant .m-chat-avatar {
  background: linear-gradient(135deg, var(--c-primary-soft), var(--c-avatar-assistant-bg));
}

/* 气泡 */
.m-chat-bubble {
  padding: 11px 15px;
  font-size: 14px;
  line-height: 1.65;
  word-break: break-word;
  min-width: 40px;
}

.m-chat-msg.assistant .m-chat-bubble {
  background: var(--c-surface);
  border-radius: 6px var(--radius-md) var(--radius-md) var(--radius-md);
  box-shadow: var(--shadow-sm);
  border: 1px solid var(--c-border-light);
  color: var(--c-text-primary);
}

.m-chat-msg.user .m-chat-bubble {
  background: linear-gradient(135deg, var(--c-primary), var(--c-primary-light));
  border-radius: var(--radius-md) 6px var(--radius-md) var(--radius-md);
  box-shadow: 0 2px 8px rgba(99, 102, 241, 0.25);
  color: #fff;
}

.m-chat-text {
  white-space: pre-wrap;
}

.m-cursor {
  animation: blink 1s step-end infinite;
  color: var(--c-primary);
  font-weight: 300;
}

@keyframes blink {
  50% { opacity: 0; }
}

/* 滑动窗口分割线（移动端） */
.m-memory-divider {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 0 2px 0;
  user-select: none;
  opacity: 0.55;
}

.m-memory-divider .m-divider-line {
  flex: 1;
  height: 1px;
  background: linear-gradient(to right, transparent, var(--c-border), transparent);
}

.m-memory-divider .m-divider-text {
  font-size: 11px;
  color: var(--c-text-muted);
  white-space: nowrap;
  letter-spacing: 0.3px;
  font-weight: 400;
}

/* 参数辅助提示 */
.m-param-hint {
  font-size: 11px;
  color: var(--c-text-muted);
  margin-top: 4px;
  line-height: 1.4;
}

/* 可折叠思考过程（移动端适配） */
.m-thinking-collapse {
  margin-bottom: 8px;
  background: #f4f5f9;
  border-radius: 6px;
  border: 1px solid #e2e4ea;
  overflow: hidden;
  width: 100%;
}
.m-chat-msg.user .m-thinking-collapse {
  background: rgba(255,255,255,0.15);
  border-color: rgba(255,255,255,0.2);
}
.m-chat-msg.user .m-thinking-text {
  color: rgba(255,255,255,0.75);
}
.m-chat-msg.user .m-thinking-label {
  color: rgba(255,255,255,0.85);
}
.m-chat-msg.user .m-thinking-toggle {
  color: rgba(255,255,255,0.6);
}
.m-chat-msg.user .m-thinking-header:hover {
  background: rgba(255,255,255,0.1);
}
.m-chat-msg.user .m-thinking-body {
  border-top-color: rgba(255,255,255,0.15);
}

.m-thinking-header {
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
.m-thinking-header:active {
  background: #e8eaf0;
}
.m-thinking-toggle {
  font-size: 10px;
  color: #909399;
  width: 12px;
  text-align: center;
  flex-shrink: 0;
}
.m-thinking-label {
  font-weight: 500;
}
.m-thinking-body {
  padding: 0 10px 8px 10px;
  border-top: 1px dashed #dcdde2;
}
.m-thinking-text {
  margin-top: 6px;
  font-size: 13px;
  color: #7a7f8a;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
  text-align: left;
}

.m-thinking {
  color: var(--c-text-muted);
  font-size: 13px;
  font-style: italic;
}

/* 思考模式开关按钮 */
.m-thinking-btn {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  transition: all 0.25s;
}
.m-thinking-btn.is-lit {
  background: var(--c-primary-soft) !important;
  border-color: var(--c-primary-light) !important;
  color: var(--c-primary) !important;
  box-shadow: 0 0 0 2px rgba(99,102,241,0.15);
}
.m-thinking-btn:not(.is-lit) .m-thinking-btn-icon {
  opacity: 0.5;
  filter: grayscale(1);
}
.m-thinking-btn.is-lit .m-thinking-btn-icon {
  opacity: 1;
  filter: none;
}

/* 更多操作弹窗列表 */
.m-more-actions-list {
  display: flex;
  flex-direction: column;
  gap: 0;
}

.m-more-action-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 16px;
  margin: 0 -20px;
  cursor: pointer;
  user-select: none;
  transition: background 0.15s;
}

.m-more-action-item:active {
  background: var(--c-bg);
}

.m-more-action-icon {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  background: var(--c-primary-bg);
  border-radius: var(--radius-sm);
  flex-shrink: 0;
}

.m-more-action-label {
  font-size: 14px;
  font-weight: 500;
  color: var(--c-text-primary);
}

.m-more-action-divider {
  height: 1px;
  background: var(--c-border-light);
  margin: 0 -20px;
}

/* 工具栏 */
.m-chat-toolbar {
  flex-shrink: 0;
  padding: 8px 0 4px;
}

.toolbar-row {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  align-items: center;
}

.toolbar-row .el-button {
  flex-shrink: 0;
  font-size: 12px;
  padding: 5px 12px;
  border-radius: 20px;
  border-color: var(--c-border);
  color: var(--c-text-secondary);
  --el-button-hover-bg-color: var(--c-primary-soft);
  --el-button-hover-border-color: var(--c-primary-light);
  --el-button-hover-text-color: var(--c-primary);
}

.toolbar-row .el-button.is-plain {
  background: var(--c-surface);
}

.toolbar-row .el-button.el-button--primary {
  border-color: var(--c-primary-light);
  color: var(--c-primary);
  background: var(--c-primary-soft);
}

.btn-icon {
  font-weight: 700;
  font-size: 14px;
  line-height: 1;
}

.m-model-status {
  font-size: 12px;
  margin-left: 4px;
  white-space: nowrap;
  font-weight: 500;
}
.m-model-status.loading { color: var(--c-warning); }
.m-model-status.error { color: var(--c-danger); }
.m-model-status.ready { color: var(--c-success); }

/* 输入区 */
.m-chat-input {
  flex-shrink: 0;
  padding-top: 8px;
}

.m-chat-input-inner {
  display: flex;
  gap: 8px;
  align-items: flex-end;
  background: var(--c-surface);
  border: 1.5px solid var(--c-border);
  border-radius: var(--radius-lg);
  padding: 6px 6px 6px 14px;
  transition: border-color 0.2s, box-shadow 0.2s;
}

.m-chat-input-inner:focus-within {
  border-color: var(--c-primary-light);
  box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.12);
}

.m-chat-textarea {
  flex: 1;
}

.m-chat-textarea :deep(.el-textarea__inner) {
  border: none !important;
  box-shadow: none !important;
  padding: 4px 0;
  font-size: 14px;
  line-height: 1.5;
  min-height: 24px;
  max-height: 120px;
  background: transparent;
  resize: none;
}

.m-chat-textarea :deep(.el-textarea__inner:focus) {
  box-shadow: none !important;
}

.m-chat-send-btn {
  flex-shrink: 0;
  width: 38px;
  height: 38px;
  border-radius: 50%;
  border: none;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  background: var(--c-border-light);
  color: var(--c-text-muted);
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}

.m-chat-send-btn.active {
  background: linear-gradient(135deg, var(--c-primary), var(--c-primary-light));
  color: #fff;
  box-shadow: 0 2px 8px rgba(99, 102, 241, 0.3);
}

.m-chat-send-btn:active.active {
  transform: scale(0.92);
}

.m-chat-send-btn:disabled {
  cursor: not-allowed;
}

/* 字段标签 */
.m-field-label {
  font-size: 12px;
  font-weight: 500;
  color: var(--c-text-secondary);
  margin-bottom: 6px;
}

/* 参数项 */
.m-param-item {
  margin-bottom: 14px;
}

.m-param-label {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12px;
  font-weight: 500;
  color: var(--c-text-secondary);
  margin-bottom: 6px;
}

.m-param-value {
  font-weight: 600;
  color: var(--c-primary);
  font-variant-numeric: tabular-nums;
}

.m-param-item .el-slider,
.m-param-item .el-slider__runway {
  touch-action: pan-y;
}

.m-param-item .el-slider__runway {
  cursor: pointer;
}

/* 参数状态提示 */
.m-param-status {
  margin-top: 14px;
  text-align: center;
  font-size: 12px;
}

.m-param-status-ready {
  color: var(--c-success);
  font-weight: 500;
}

.m-param-status-loading {
  color: var(--c-text-muted);
  font-weight: 500;
}

.m-param-label {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12px;
  font-weight: 500;
  color: var(--c-text-secondary);
  margin-bottom: 6px;
}

.m-param-value {
  font-weight: 600;
  color: var(--c-primary);
  font-variant-numeric: tabular-nums;
}

/* 消息里的 br 保留间距 */
.m-chat-text :deep(br) {
  display: block;
  content: '';
  margin: 4px 0;
}

/* 弹窗内滚动条可见 */
.m-chat-page .m-modal-content {
  overflow-y: auto;
}
.m-chat-page .m-modal-content::-webkit-scrollbar {
  width: 6px;
}
.m-chat-page .m-modal-content::-webkit-scrollbar-thumb {
  background: var(--c-scrollbar-thumb);
  border-radius: 3px;
}
</style>

<!-- 移动端选择器下拉框：限制宽度不超出屏幕 -->
<style>
.m-select-popper {
  max-width: calc(100vw - 24px) !important;
}
.m-select-popper .el-select-dropdown__item {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>