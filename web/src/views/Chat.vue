<template>
  <div class="page-container">
    <div class="content-wrapper">
      <!-- 左侧对话区 -->
      <div class="left-panel">
        <el-card class="chat-card">
          <template #header>
            <div class="chat-header">
              <span>当前对话</span>
              <el-select
                v-model="selectedModel"
                placeholder="选择模型"
                style="width: 320px;"
                @focus="loadModels"
                @change="onModelChange"
              >
                <el-option
                  v-for="item in modelList"
                  :key="item.model"
                  :label="item.model"
                  :value="item.model"
                >
                  <div class="model-option">
                    <span class="model-option-label">{{ item.model }}</span>
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
              <el-button type="success" @click="handleNewChat">新建对话</el-button>
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
            <el-button @click="cancelNewChat">取消</el-button>
            <el-button type="success" @click="confirmNewChat">确认创建</el-button>
          </div>

          <!-- 对话消息区域 -->
          <div class="chat-messages" ref="messagesRef">
            <div v-if="messages.length === 0" class="empty-chat">
              <el-empty description="暂无对话内容，请选择模型后开始对话" />
            </div>
            <div
              v-for="(msg, index) in messages"
              :key="index"
              class="message-item"
              :class="msg.role"
            >
              <div class="message-avatar">
                <el-icon v-if="msg.role === 'user'"><User /></el-icon>
                <el-icon v-else><ChatDotRound /></el-icon>
              </div>
              <div class="message-content">
                <div class="message-text" v-html="formatMessage(msg.content)"></div>
                <div v-if="msg.role === 'assistant' && msg.isStreaming" class="streaming-indicator">
                  <span class="cursor">|</span>
                </div>
              </div>
            </div>
          </div>

          <!-- 输入区域 -->
          <div class="chat-input-area">
            <el-input
              v-model="userInput"
              type="textarea"
              :rows="3"
              placeholder="请输入您的问题..."
              :disabled="isStreaming"
              @keydown.enter.ctrl="sendMessage"
            />
            <el-button
              type="primary"
              :loading="isStreaming"
              :disabled="!userInput.trim() || !selectedModel"
              @click="sendMessage"
              class="send-btn"
            >
              {{ isStreaming ? '生成中...' : '发送' }}
            </el-button>
          </div>
        </el-card>
      </div>

      <!-- 右侧参数区 -->
      <div class="right-panel">
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
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { User, ChatDotRound, Loading, CircleCheck } from '@element-plus/icons-vue'
import axios from 'axios'
import * as echarts from 'echarts'

const selectedModel = ref('')
const modelList = ref([])
const messages = ref([])
const userInput = ref('')
const isStreaming = ref(false)
const messagesRef = ref(null)
const showPerplexity = ref(true)
const perplexityChartRef = ref(null)
let perplexityChartInstance = null
const perplexityData = ref([])

const showNewChatPanel = ref(false)
const newChatFolder = ref('')
const newChatModel = ref('')
const folderList = ref([])
const modelFileList = ref([])

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

const inferParams = reactive({
  model: '',
  max_tokens: 2048,
  clean_rounds: 10,
  temperature: 1,
  top_p: 0.85,
  top_k: 0,
  alpha_frequency: 0.2,
  alpha_presence: 0.2,
  alpha_decay: 0.996
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
  alpha_decay: 0.996
}

const loadModels = async () => {
  try {
    const res = await axios.get('/api/data/chat-models')
    modelList.value = res.data
    if (modelList.value.length > 0) {
      isLoadingParams.value = true
      selectedModel.value = modelList.value[0].model
      inferParams.model = modelList.value[0].model
      if (modelList.value[0].params) {
        Object.assign(inferParams, modelList.value[0].params)
      }
      isParamsSynced.value = true
      isLoadingParams.value = false
    }
  } catch (error) {
    console.error('获取模型列表失败', error)
    modelList.value = mockModelList
    if (modelList.value.length > 0) {
      selectedModel.value = modelList.value[0].model
      inferParams.model = modelList.value[0].model
    }
  }
}

const onModelChange = (value) => {
  const item = modelList.value.find(i => i.model === value)
  if (item) {
    isLoadingParams.value = true
    inferParams.model = value
    if (item.params) {
      Object.assign(inferParams, item.params)
    }
    isParamsSynced.value = true
    isLoadingParams.value = false
  }
}

const confirmDeleteChat = async (item) => {
  try {
    await ElMessageBox.confirm(`确定要删除对话 "${item.model}" 吗？此操作不可恢复！`, '删除确认', {
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
      params: { folder: folder, model: modelName }
    })
    ElMessage.success('对话已删除')
    await loadModels()
  } catch (error) {
    console.error('删除对话失败', error)
    ElMessage.error(error.response?.data?.detail || '删除失败')
  }
}

const mockModelList = [
  'checkpoint-1000.pth',
  'checkpoint-2000.pth',
  'checkpoint-3000.pth',
  'lora_model.pth'
]

const mockResponses = [
  '您好！我是基于大语言模型的智能助手。我可以帮您回答各种问题、提供信息、进行对话交流等。有什么我可以帮助您的吗？',
  '根据您的问题，我来详细解释一下。这个概念涉及到多个方面：首先，我们需要理解基本原理；其次，要掌握关键的技术要点；最后，还需要大量的实践操作。',
  '好的，让我来回答您的问题。这个问题的答案取决于多个因素，包括具体的应用场景、实际需求以及约束条件等。',
  '感谢您的提问！关于您提到的内容，我可以从以下几个角度来分析：第一，从技术层面；第二，从应用层面；第三，从发展趋势来看。'
]

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
  isParamsSynced.value = false
  isLoadingParams.value = false
  ElMessage.success('已重置为默认参数')
}

const formatMessage = (content) => {
  return content.replace(/\n/g, '<br>')
}

const clearConversation = () => {
  messages.value = []
  perplexityData.value = []
  updatePerplexityChart()
}

const handleNewChat = async () => {
  showNewChatPanel.value = !showNewChatPanel.value
  if (showNewChatPanel.value) {
    newChatFolder.value = ''
    newChatModel.value = ''
    modelFileList.value = []
    if (folderList.value.length === 0) {
      await loadCheckpointFolders()
    }
  }
}

const saveChatData = async (folder, model, params) => {
  try {
    await axios.post('/api/data/chat-data', {
      folder: folder,
      model: model,
      params: params
    })
  } catch (error) {
    console.error('保存对话数据失败', error)
  }
}

const confirmNewChat = async () => {
  if (!newChatFolder.value || !newChatModel.value) {
    ElMessage.warning('请选择文件夹和模型文件')
    return
  }
  const params = {
    max_tokens: inferParams.max_tokens,
    clean_rounds: inferParams.clean_rounds,
    temperature: inferParams.temperature,
    top_p: inferParams.top_p,
    top_k: inferParams.top_k,
    alpha_frequency: inferParams.alpha_frequency,
    alpha_presence: inferParams.alpha_presence,
    alpha_decay: inferParams.alpha_decay
  }
  await saveChatData(newChatFolder.value, newChatModel.value, params)
  selectedModel.value = newChatModel.value
  inferParams.model = newChatModel.value
  messages.value = []
  perplexityData.value = []
  updatePerplexityChart()
  showNewChatPanel.value = false
  ElMessage.success('新对话已创建')
}

const cancelNewChat = () => {
  showNewChatPanel.value = false
}

const onFolderChange = async (val) => {
  newChatModel.value = ''
  if (val) {
    await loadCheckpointFiles(val)
  }
}

const scrollToBottom = () => {
  nextTick(() => {
    if (messagesRef.value) {
      messagesRef.value.scrollTop = messagesRef.value.scrollHeight
    }
  })
}

const sendMessage = async () => {
  if (!userInput.value.trim() || !selectedModel.value) {
    ElMessage.warning('请选择模型并输入内容')
    return
  }

  const userMessage = userInput.value.trim()
  messages.value.push({ role: 'user', content: userMessage })

  const assistantMessage = { role: 'assistant', content: '', isStreaming: true }
  messages.value.push(assistantMessage)

  userInput.value = ''
  isStreaming.value = true
  scrollToBottom()

  try {
    const response = await axios.post('/api/chat/chat', {
      model: selectedModel.value,
      message: userMessage,
      messages: messages.value.slice(0, -1).map(m => ({ role: m.role, content: m.content })),
      params: {
        max_tokens: inferParams.max_tokens,
        temperature: inferParams.temperature,
        top_p: inferParams.top_p,
        top_k: inferParams.top_k,
        alpha_frequency: inferParams.alpha_frequency,
        alpha_presence: inferParams.alpha_presence,
        alpha_decay: inferParams.alpha_decay
      }
    }, {
      responseType: 'text',
      onDownloadProgress: (progressEvent) => {
        const text = new TextDecoder().decode(progressEvent.target.response)
        const lines = text.split('\n').filter(line => line.startsWith('data: '))
        const lastLine = lines[lines.length - 1]
        if (lastLine) {
          const data = lastLine.replace('data: ', '')
          if (data !== '[DONE]') {
            try {
              const parsed = JSON.parse(data)
              assistantMessage.content += parsed.content || ''

              if (parsed.perplexity) {
                perplexityData.value.push(parsed.perplexity)
                updatePerplexityChart()
              }
            } catch (e) {
              assistantMessage.content += data
            }
          } else {
            assistantMessage.isStreaming = false
            isStreaming.value = false
          }
        }
        scrollToBottom()
      }
    })
  } catch (error) {
    console.error('请求失败，使用模拟响应', error)
    assistantMessage.content = ''
    assistantMessage.isStreaming = true

    const randomResponse = mockResponses[Math.floor(Math.random() * mockResponses.length)]
    let currentIndex = 0
    const chunkSize = 3
    let perplexityIndex = 0

    const simulateResponse = () => {
      return new Promise((resolve) => {
        setTimeout(() => {
          if (currentIndex < randomResponse.length) {
            const end = Math.min(currentIndex + chunkSize, randomResponse.length)
            const chunk = randomResponse.slice(currentIndex, end)
            assistantMessage.content += chunk
            currentIndex = end

            const ecgWave = (i) => {
              const t = (i % 20) / 20
              if (t < 0.1) return 1 + Math.sin(t * Math.PI * 10) * 0.3
              if (t < 0.15) return 0.3 + (t - 0.1) * 10
              if (t < 0.2) return 1.3 - (t - 0.15) * 20
              if (t < 0.25) return 0.3 + (t - 0.2) * 10
              if (t < 0.35) return 0.8 + Math.sin((t - 0.25) * Math.PI * 10) * 0.2
              if (t < 0.4) return 1 - (t - 0.35) * 10
              return 0.5 + Math.sin(t * Math.PI * 2) * 0.1
            }
            const basePerplexity = ecgWave(perplexityIndex) * 8 + Math.random() * 1.5
            perplexityData.value.push(basePerplexity)
            perplexityIndex++
            updatePerplexityChart()
            scrollToBottom()

            resolve(simulateResponse())
          } else {
            assistantMessage.isStreaming = false
            isStreaming.value = false
            scrollToBottom()
            resolve()
          }
        }, 30)
      })
    }

    await simulateResponse()
  }
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

  const parts = selectedModel.value.split('/')
  if (parts.length < 2) return

  const folder = parts[0]
  const model = parts[1]

  isSavingParams.value = true

  try {
    await axios.put('/api/data/chat-data', {
      folder: folder,
      model: model,
      params: {
        max_tokens: inferParams.max_tokens,
        clean_rounds: inferParams.clean_rounds,
        temperature: inferParams.temperature,
        top_p: inferParams.top_p,
        top_k: inferParams.top_k,
        alpha_frequency: inferParams.alpha_frequency,
        alpha_presence: inferParams.alpha_presence,
        alpha_decay: inferParams.alpha_decay
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
  height: calc(100vh - 180px);
}

.left-panel {
  flex: 1;
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
}

.model-option-delete {
  flex-shrink: 0;
  margin-left: 10px;
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
}

.message-text {
  padding: 12px 16px;
  border-radius: 8px;
  background: white;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  line-height: 1.6;
  word-wrap: break-word;
}

.message-item.user .message-text {
  background: #409eff;
  color: white;
}

.streaming-indicator {
  margin-top: 5px;
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
}

.send-btn {
  height: auto;
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
</style>