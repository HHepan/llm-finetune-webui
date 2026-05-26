<template>
  <div class="m-chat-page">
    <!-- 顶部选择栏：选择对话 + 选择角色 -->
    <div class="m-chat-selectbar">
      <el-select v-model="selectedModel" placeholder="选择对话" size="small" @change="onModelSelect" style="flex:1;min-width:0;">
        <el-option
          v-for="item in modelList"
          :key="item.model + '|' + item.session"
          :label="item.model + '-' + item.session"
          :value="item.model + '|' + item.session"
        >
          <div style="display:flex;justify-content:space-between;align-items:center;">
            <span style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">{{ item.model }}-{{ item.session }}</span>
            <el-button type="danger" size="small" link @click.stop="deleteSelectedChat(item)">删除</el-button>
          </div>
        </el-option>
      </el-select>
      <el-select v-model="selectedRole" placeholder="选择角色" size="small" @change="onRoleChange" :disabled="isModelLoading" style="width:130px;flex-shrink:0;">
        <el-option v-for="role in roleList" :key="role.id" :label="role.name" :value="role.id" />
      </el-select>
    </div>

    <!-- 对话消息区 -->
    <div class="m-chat-messages" ref="messagesRef">
      <div v-if="messages.length === 0" class="m-empty">
        <div class="m-empty-icon">💬</div>
        <span>选择模型后开始对话</span>
      </div>
      <div
        v-for="(msg, index) in messages"
        :key="index"
        class="m-chat-msg"
        :class="msg.role"
      >
        <div class="m-chat-avatar">
          <span v-if="msg.role === 'user'">😊</span>
          <span v-else>🤖</span>
        </div>
        <div class="m-chat-bubble">
          <div class="m-chat-text" v-html="formatMessage(msg.content)"></div>
          <span v-if="msg.role === 'assistant' && msg.isStreaming" class="m-cursor">|</span>
          <div v-if="msg.role === 'assistant' && isThinking && !msg.content" class="m-thinking">思考中...</div>
        </div>
      </div>
    </div>

    <!-- 操作按钮组 -->
    <div class="m-chat-toolbar">
      <div class="toolbar-row">
        <el-button size="small" type="success" plain @click="showNewChat = true" :disabled="isModelLoading">
          新建对话
        </el-button>
        <el-button size="small" type="warning" plain @click="clearHistory" :disabled="!selectedModel">
          清空对话记录
        </el-button>
        <el-button size="small" :type="showParams ? 'primary' : 'default'" plain @click="showParams = !showParams">
          设置参数
        </el-button>
        <el-button size="small" type="info" plain @click="openRoleDialog">
          添加角色
        </el-button>
      </div>
      <div class="toolbar-row">
        <el-button size="small" type="primary" plain @click="regenerateLastMessage" :disabled="!canRegenerate">重新生成</el-button>
        <el-button size="small" type="warning" plain @click="reEditLastMessage" :disabled="!canReEdit">重新编辑</el-button>
        <span v-if="isModelLoading" class="m-model-status loading">⏳ 加载中...</span>
        <span v-else-if="modelLoadError" class="m-model-status error">❌ 加载失败</span>
        <span v-else-if="isModelLoaded && selectedModel" class="m-model-status ready">✅ 就绪</span>
      </div>
    </div>

    <!-- 输入区 -->
    <div class="m-chat-input">
      <el-input
        v-model="userInput"
        type="textarea"
        :rows="2"
        placeholder="输入消息..."
        @keydown.enter="handleEnter"
        :disabled="isModelLoading"
        resize="none"
        class="m-chat-textarea"
      />
      <el-button
        type="primary"
        :disabled="!userInput.trim() || !selectedModel || isModelLoading"
        @click="sendMessage"
        class="m-chat-send-btn"
      >
        发送
      </el-button>
    </div>

    <!-- ====== 新建对话弹窗 ====== -->
    <div v-if="showNewChat" class="m-modal-overlay" @click.self="showNewChat = false">
      <div class="m-modal-content" style="max-height:70vh;">
        <div class="m-modal-header">
          <span>新建对话</span>
          <span class="m-modal-close" @click="showNewChat = false">&times;</span>
        </div>
        <div style="display:flex;flex-wrap:wrap;gap:6px;margin-bottom:10px;">
          <el-select v-model="newChatFolder" placeholder="文件夹" size="small" style="flex:1;min-width:80px;" @change="onNewChatFolderChange">
            <el-option v-for="f in folderList" :key="f" :label="f" :value="f" />
          </el-select>
          <el-select v-model="newChatModel" placeholder="模型文件" size="small" style="flex:1;min-width:80px;">
            <el-option v-for="m in modelFileList" :key="m" :label="m" :value="m" />
          </el-select>
        </div>
        <div style="display:flex;gap:6px;">
          <el-input v-model="newChatSession" placeholder="对话名称" size="small" style="flex:1;" />
          <el-button size="small" type="success" @click="confirmNewChat" :disabled="!newChatFolder || !newChatModel || !newChatSession">创建</el-button>
        </div>
      </div>
    </div>

    <!-- ====== 角色编辑弹窗 ====== -->
    <div v-if="showRoleDialog" class="m-modal-overlay" @click.self="closeRoleDialog">
      <div class="m-modal-content">
        <div class="m-modal-header">
          <span>{{ isEditingRole ? '编辑角色' : '新建角色' }}</span>
          <span class="m-modal-close" @click="closeRoleDialog">&times;</span>
        </div>
        <div style="margin-bottom:8px;">
          <div style="font-size:12px;color:#666;margin-bottom:4px;">角色名称</div>
          <el-input v-model="roleForm.name" placeholder="名称" size="small" />
        </div>
        <div style="margin-bottom:12px;">
          <div style="font-size:12px;color:#666;margin-bottom:4px;">角色设定</div>
          <el-input v-model="roleForm.content" type="textarea" :rows="6" placeholder="角色设定描述..." size="small" />
        </div>
        <div style="display:flex;gap:10px;">
          <el-button size="small" style="flex:1;" @click="closeRoleDialog">取消</el-button>
          <el-button size="small" type="primary" style="flex:1;" @click="confirmRole" :disabled="!roleForm.name || !roleForm.content">
            {{ isEditingRole ? '确认修改' : '确认添加' }}
          </el-button>
        </div>
      </div>
    </div>

    <!-- ====== 推理参数面板（底部弹出） ====== -->
    <div v-if="showParams" class="m-modal-overlay" @click.self="showParams = false">
      <div class="m-modal-content" style="max-height:70vh;">
        <div class="m-modal-header">
          <span>推理参数</span>
          <div style="display:flex;gap:8px;align-items:center;">
            <el-button size="small" link @click="resetParams">重置</el-button>
            <span class="m-modal-close" @click="showParams = false">&times;</span>
          </div>
        </div>
        <el-form :model="inferParams" label-width="0">
          <div style="margin-bottom:12px;">
            <div style="font-size:12px;color:#666;margin-bottom:4px;">
              temperature
              <span style="float:right;">{{ inferParams.temperature.toFixed(2) }}</span>
            </div>
            <el-slider v-model="inferParams.temperature" :min="0" :max="2" :step="0.01" size="small" />
          </div>
          <div style="margin-bottom:12px;">
            <div style="font-size:12px;color:#666;margin-bottom:4px;">
              top_p
              <span style="float:right;">{{ inferParams.top_p.toFixed(2) }}</span>
            </div>
            <el-slider v-model="inferParams.top_p" :min="0" :max="1" :step="0.01" size="small" />
          </div>
          <div style="margin-bottom:12px;">
            <div style="font-size:12px;color:#666;margin-bottom:4px;">
              alpha_frequency
              <span style="float:right;">{{ inferParams.alpha_frequency.toFixed(2) }}</span>
            </div>
            <el-slider v-model="inferParams.alpha_frequency" :min="0" :max="1" :step="0.01" size="small" />
          </div>
          <div style="margin-bottom:12px;">
            <div style="font-size:12px;color:#666;margin-bottom:4px;">
              alpha_presence
              <span style="float:right;">{{ inferParams.alpha_presence.toFixed(2) }}</span>
            </div>
            <el-slider v-model="inferParams.alpha_presence" :min="0" :max="1" :step="0.01" size="small" />
          </div>
          <div style="margin-bottom:12px;">
            <div style="font-size:12px;color:#666;margin-bottom:4px;">
              alpha_decay
              <span style="float:right;">{{ inferParams.alpha_decay.toFixed(3) }}</span>
            </div>
            <el-slider v-model="inferParams.alpha_decay" :min="0" :max="1" :step="0.001" size="small" />
          </div>
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;">
            <div>
              <div style="font-size:12px;color:#666;margin-bottom:4px;">max_tokens</div>
              <el-input-number v-model="inferParams.max_tokens" :min="1" :max="4096" size="small" style="width:100%;" />
            </div>
            <div>
              <div style="font-size:12px;color:#666;margin-bottom:4px;">top_k</div>
              <el-input-number v-model="inferParams.top_k" :min="0" :max="200" size="small" style="width:100%;" />
            </div>
            <div>
              <div style="font-size:12px;color:#666;margin-bottom:4px;">clean_rounds</div>
              <el-input-number v-model="inferParams.clean_rounds" :min="1" :max="100" size="small" style="width:100%;" />
            </div>
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
const isStreaming = ref(false)
const isThinking = ref(false)
const messagesRef = ref(null)
let displayInterval = null

// 面板控制
const showNewChat = ref(false)
const showParams = ref(false)
const showRoleDialog = ref(false)

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
  alpha_frequency: 0.2, alpha_presence: 0.2, alpha_decay: 0.996
})

const defaultParams = {
  max_tokens: 2048, clean_rounds: 10,
  temperature: 1, top_p: 0.85, top_k: 0,
  alpha_frequency: 0.2, alpha_presence: 0.2, alpha_decay: 0.996
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
  modelLoadError.value = ''
  try {
    await axios.post('/api/chat/preload-model', null, { params: { model: modelPath } })
    isModelLoaded.value = true
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
  if (val === 'none') Object.assign(inferParams, defaultParams)
  else {
    const role = roleList.value.find(r => r.id === val)
    if (role) Object.assign(inferParams, roleplayParams)
  }
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

// ==== 对话 ====
const handleEnter = (e) => {
  if (e.shiftKey) return
  e.preventDefault()
  sendMessage()
}

const displayCharByChar = (fullContent) => {
  if (displayInterval) clearInterval(displayInterval)
  isThinking.value = false
  const content = fullContent.replace(/\n+$/, '')
  const lastMsg = messages.value[messages.value.length - 1]
  if (!lastMsg || lastMsg.role !== 'assistant') return
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

const generateResponse = async (userMessageContent, isNewMessage = true) => {
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
    let historyMessages = messages.value.slice(0, isNewMessage ? -2 : -1)
    if (selectedRole.value && selectedRole.value !== 'none') {
      const roleCard = roleList.value.find(r => r.id === selectedRole.value)
      if (roleCard && roleCard.content) {
        historyMessages = [{ role: 'system', content: roleCard.content }, ...historyMessages]
      }
    }

    const response = await fetch('/api/chat/chat', {
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
          alpha_decay: inferParams.alpha_decay
        }
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
  await generateResponse(userMsg.content, false)
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
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 8px 0;
  flex-shrink: 0;
}

.m-chat-selectbar .el-select {
  width: 100%;
}

/* 消息区 - 可滚动 */
.m-chat-messages {
  flex: 1;
  overflow-y: auto;
  -webkit-overflow-scrolling: touch;
  padding: 8px 4px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

/* 单条消息 */
.m-chat-msg {
  display: flex;
  gap: 8px;
  max-width: 92%;
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
  background: #f0f0f0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
}

.m-chat-msg.user .m-chat-avatar {
  background: #e6f7ff;
}

.m-chat-bubble {
  background: #fff;
  border-radius: 12px;
  padding: 10px 14px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.08);
  font-size: 14px;
  line-height: 1.6;
  color: #333;
  word-break: break-word;
  min-width: 40px;
}

.m-chat-msg.user .m-chat-bubble {
  background: #409eff;
  color: #fff;
}

.m-chat-text {
  white-space: pre-wrap;
}

.cursor {
  animation: blink 1s step-end infinite;
}

@keyframes blink {
  50% { opacity: 0; }
}

.m-thinking {
  color: #999;
  font-size: 13px;
  font-style: italic;
}

/* 工具栏 */
.m-chat-toolbar {
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 8px 0;
}

.toolbar-row {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  align-items: center;
}

.toolbar-row .el-button {
  flex-shrink: 0;
}

.m-model-status {
  font-size: 12px;
  margin-right: 4px;
  white-space: nowrap;
}
.m-model-status.loading { color: #e6a23c; }
.m-model-status.error { color: #f56c6c; }
.m-model-status.ready { color: #67c23a; }

/* 输入区 */
.m-chat-input {
  flex-shrink: 0;
  display: flex;
  gap: 8px;
  align-items: flex-end;
  padding-top: 8px;
  border-top: 1px solid #eee;
}

.m-chat-textarea {
  flex: 1;
}

.m-chat-textarea :deep(.el-textarea__inner) {
  border-radius: 10px;
  font-size: 14px;
  line-height: 1.4;
  min-height: 44px;
}

.m-chat-send-btn {
  height: 44px;
  flex-shrink: 0;
  padding: 0 20px;
  border-radius: 10px;
}

/* 消息里的 br 保留间距 */
.m-chat-text :deep(br) {
  display: block;
  content: '';
  margin: 4px 0;
}
</style>