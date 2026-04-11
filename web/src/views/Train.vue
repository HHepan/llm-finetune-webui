<template>
  <div class="page-container">
    <div class="content-wrapper">
      <!-- 左侧参数设置区 -->
      <div class="left-panel">
        <!-- 训练参数 -->
        <el-card class="param-card">
          <template #header>
            <div class="card-header">
              <span>训练参数</span>
            </div>
          </template>
          <el-form :model="trainParams" label-width="120px">
            <el-form-item label="保存位置">
              <el-input disabled value="llm-finetune-webui/workspace/checkpoints" />
            </el-form-item>

            <el-form-item label="基底模型">
              <el-select v-model="trainParams.base_model" placeholder="请选择基底模型" style="width: 100%" @change="onBaseModelChange" :disabled="trainingStatus === 'running'">
                <el-option
                  v-for="model in modelList"
                  :key="model"
                  :label="model"
                  :value="model"
                />
              </el-select>
            </el-form-item>

            <el-form-item label="模型参数量">
              <el-select v-model="trainParams.model_size" placeholder="请选择模型参数量" style="width: 100%" :disabled="trainingStatus === 'running'">
                <el-option
                  v-for="size in modelSizeList"
                  :key="size"
                  :label="size"
                  :value="size"
                />
              </el-select>
            </el-form-item>

            <el-form-item label="训练数据">
              <div style="display: flex; gap: 10px; width: 100%;">
                <el-select v-model="trainDataFolder" placeholder="选择文件夹" style="flex: 1" @change="onTrainDataFolderChange" :disabled="trainingStatus === 'running'">
                  <el-option
                    v-for="folder in trainDataFolderList"
                    :key="folder"
                    :label="folder"
                    :value="folder"
                  />
                </el-select>
                <el-select v-model="trainParams.train_data" placeholder="选择数据文件" style="flex: 1" :disabled="!trainDataFolder || trainingStatus === 'running'">
                  <el-option
                    v-for="data in trainDataFileList"
                    :key="data"
                    :label="data"
                    :value="data"
                  />
                </el-select>
              </div>
            </el-form-item>

            <el-form-item label="micro_bsz">
              <el-tooltip content="微批次大小，根据显存大小调整，微调时从 1 开始逐渐增大" placement="top">
                <el-input-number v-model="trainParams.micro_bsz" :min="1" :max="64" style="width: 100%" :disabled="trainingStatus === 'running'" />
              </el-tooltip>
            </el-form-item>

            <el-form-item label="epoch_save">
              <el-tooltip content="每隔多少个训练轮次保存一次 LoRA 文件，注意存储空间是否充足" placement="top">
                <el-input-number v-model="trainParams.epoch_save" :min="1" :max="100" style="width: 100%" :disabled="trainingStatus === 'running'" />
              </el-tooltip>
            </el-form-item>

            <el-form-item label="epoch_steps">
              <el-tooltip content="每个训练轮次的步数，增加会拉长单个 epoch 的训练时间" placement="top">
                <el-input-number v-model="trainParams.epoch_steps" :min="1" :max="10000" style="width: 100%" :disabled="trainingStatus === 'running'" />
              </el-tooltip>
            </el-form-item>

            <el-form-item label="ctx_len">
              <el-tooltip content="微调模型的上下文长度，建议根据语料长度修改" placement="top">
                <el-input-number v-model="trainParams.ctx_len" :min="128" :max="4096" :step="128" style="width: 100%" :disabled="trainingStatus === 'running'" />
              </el-tooltip>
            </el-form-item>

            <el-form-item label="epoch_count">
              <el-tooltip content="总训练轮次" placement="top">
                <el-input-number v-model="trainParams.epoch_count" :min="1" :max="100" style="width: 100%" :disabled="trainingStatus === 'running'" />
              </el-tooltip>
            </el-form-item>

            <el-form-item label="lr_init">
              <el-tooltip content="初始学习率，DiSHA 建议 2e-5 ，最大不超过 1e-4" placement="top">
                <el-input-number v-model="trainParams.lr_init" :min="1e-6" :max="1e-4" :step="1e-6" :precision="5" style="width: 100%" :disabled="trainingStatus === 'running'" />
              </el-tooltip>
            </el-form-item>

            <el-form-item label="lr_final">
              <el-tooltip content="最终学习率，建议和初始学习率保持一致" placement="top">
                <el-input-number v-model="trainParams.lr_final" :min="1e-6" :max="1e-4" :step="1e-6" :precision="5" style="width: 100%" :disabled="trainingStatus === 'running'" />
              </el-tooltip>
            </el-form-item>
            
            <el-form-item>
              <el-button type="info" link @click="clearSavedParams" :disabled="trainingStatus === 'running'">
                清除已保存参数
              </el-button>
            </el-form-item>
          </el-form>
        </el-card>

        <!-- LoRA参数 -->
        <el-card class="param-card">
          <template #header>
            <div class="card-header">
              <span>LoRA参数</span>
            </div>
          </template>
          <el-form :model="loraParams" label-width="120px">
            <el-form-item label="r (rank)">
              <el-tooltip content="LoRA 微调的 rank 参数，值越大效果越好，但训练速度越慢/显存需求越高，一般训练使用 32 或者 64 即可" placement="top">
                <el-input-number v-model="loraParams.r" :min="1" :max="256" style="width: 100%" :disabled="trainingStatus === 'running'" />
              </el-tooltip>
            </el-form-item>

            <el-form-item label="lora_alpha">
              <el-tooltip content="LoRA 微调的 alpha 参数（缩放因子）" placement="top">
                <el-input-number v-model="loraParams.lora_alpha" :min="1" :max="256" style="width: 100%" :disabled="trainingStatus === 'running'" />
              </el-tooltip>
            </el-form-item>

            <el-form-item label="lora_dropout">
              <el-tooltip content="LoRA 微调的丢弃率，建议使用 0.01" placement="top">
                <el-input-number v-model="loraParams.lora_dropout" :min="0" :max="1" :step="0.01" :precision="2" style="width: 100%" :disabled="trainingStatus === 'running'" />
              </el-tooltip>
            </el-form-item>
          </el-form>
        </el-card>
      </div>

      <!-- 右侧训练进度区 -->
      <div class="right-panel">
        <el-card class="progress-card">
          <template #header>
            <div class="card-header">
              <span>训练进度</span>
            </div>
          </template>
          <div class="progress-info">
            <div class="progress-item">
              <span class="progress-label">Epoch 进度</span>
              <el-progress class="progress-bar" :percentage="epochProgress" :stroke-width="12" />
            </div>
            <div class="progress-item">
              <span class="progress-label">Step 进度</span>
              <el-progress class="progress-bar" :percentage="stepProgress" :stroke-width="12" />
            </div>
            <div class="progress-detail">
              <span>Epoch: {{ currentEpoch }} / {{ trainParams.epoch_count }}</span>
              <span>Step: {{ currentStep }} / {{ trainParams.epoch_steps }}</span>
            </div>
            <div class="progress-metrics" v-if="trainingStatus === 'running'">
              <span>loss: {{ sumLoss.toFixed(3) }}</span>
              <span>lr: {{ currentLr.toExponential(2) }}</span>
              <span>{{ itsPerSec.toFixed(2) }} it/s</span>
            </div>
          </div>
        </el-card>

        <el-card class="loss-card">
          <template #header>
            <div class="card-header">
              <span>损失曲线</span>
            </div>
          </template>
          <div class="loss-chart">
            <div v-if="lossData.length === 0" class="loss-empty">
              暂无训练数据
            </div>
            <canvas ref="lossCanvas" width="400" height="200"></canvas>
          </div>
        </el-card>

        <el-card class="log-card">
          <template #header>
            <div class="card-header">
              <span>训练日志</span>
              <el-button type="primary" link @click="logDialogVisible = true">
                <el-icon><FullScreen /></el-icon>
                放大
              </el-button>
            </div>
          </template>
          <el-scrollbar ref="inlineLogScrollbarRef" class="log-scrollbar">
            <div class="log-content">
              <div v-for="(log, index) in logs" :key="index" class="log-line">
                {{ log }}
              </div>
              <div v-if="logs.length === 0" class="log-empty">
                点击"开始训练"启动训练
              </div>
            </div>
          </el-scrollbar>
        </el-card>

        <el-dialog v-model="logDialogVisible" title="训练日志" width="50%" top="5vh">
          <div class="log-dialog-header">
            <el-switch v-model="autoScroll" active-text="自动滚动" />
            <el-button type="danger" @click="clearLogs">清空日志</el-button>
          </div>
          <el-scrollbar ref="logScrollbarRef" class="log-dialog-scrollbar" :wrap-style="'height: calc(70vh - 80px)'">
            <div class="log-content dialog-log-content">
              <div v-for="(log, index) in logs" :key="index" class="log-line">
                {{ log }}
              </div>
              <div v-if="logs.length === 0" class="log-empty">
               暂无日志
              </div>
            </div>
          </el-scrollbar>
        </el-dialog>

        <el-dialog v-model="stopConfirmDialogVisible" title="确认停止训练" width="30%">
          <p>确定要停止训练吗？停止后训练将被中断。</p>
          <template #footer>
            <el-button @click="stopConfirmDialogVisible = false">取消</el-button>
            <el-button type="danger" @click="handleStopTraining">确定停止</el-button>
          </template>
        </el-dialog>

        <div class="action-bar">
          <el-button
            v-if="trainingStatus === 'idle'"
            type="success"
            size="large"
            @click="startTraining"
          >
            开始训练
          </el-button>
          <el-button
            v-else
            type="danger"
            size="large"
            @click="stopConfirmDialogVisible = true"
          >
            停止训练
          </el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { FullScreen } from '@element-plus/icons-vue'
import axios from 'axios'

const trainParams = reactive({
  base_model: '',
  model_size: '2.9B',
  train_data: '',
  micro_bsz: 1,
  epoch_save: 1,
  epoch_steps: 1000,
  ctx_len: 512,
  epoch_count: 1,
  lr_init: 2e-5,
  lr_final: 2e-5
})

const modelSizeMap = {
  '0.1B': { n_layer: 12, n_embd: 768 },
  '0.4B': { n_layer: 24, n_embd: 1024 },
  '1.5B': { n_layer: 24, n_embd: 2048 },
  '2.9B': { n_layer: 32, n_embd: 2560 },
  '7B': { n_layer: 32, n_embd: 4096 },
  '14B': { n_layer: 61, n_embd: 4096 }
}

const modelSizeList = Object.keys(modelSizeMap)

const loraParams = reactive({
  r: 32,
  lora_alpha: 32,
  lora_dropout: 0.01
})

const modelList = ref([])

const trainDataFolder = ref('')
const trainDataFolderList = ref([])
const trainDataFileList = ref([])
const dataList = ref([])

const trainingStatus = ref('idle')
const currentEpoch = ref(0)
const currentStep = ref(0)
const currentLr = ref(0)
const itsPerSec = ref(0)
const sumLoss = ref(0)

const epochProgress = computed(() => {
  if (trainParams.epoch_count === 0) return 0
  return Math.round((currentEpoch.value / trainParams.epoch_count) * 100)
})

const stepProgress = computed(() => {
  if (trainParams.epoch_steps === 0) return 0
  return Math.round((currentStep.value / trainParams.epoch_steps) * 100)
})
const logs = ref([])
const lossData = ref([])
const lossCanvas = ref(null)

const logDialogVisible = ref(false)
const autoScroll = ref(true)
const stopConfirmDialogVisible = ref(false)
const logScrollbarRef = ref(null)
const inlineLogScrollbarRef = ref(null)

const clearLogs = () => {
  logs.value = []
}

let pollTimer = null

const loadBaseModels = async () => {
  try {
    const res = await axios.get('/api/data/base-models')
    modelList.value = res.data
  } catch (error) {
    console.error('获取基底模型列表失败', error)
  }
}

const loadTrainDataFolders = async () => {
  try {
    const res = await axios.get('/api/data/folders')
    trainDataFolderList.value = res.data
  } catch (error) {
    console.error('获取训练数据文件夹列表失败', error)
  }
}

const onTrainDataFolderChange = async () => {
  trainParams.train_data = ''
  trainDataFileList.value = []
  const folder = trainDataFolder.value.replace('./', '') || ''
  try {
    const res = await axios.get('/api/data/files', { params: { folder } })
    trainDataFileList.value = res.data
  } catch (error) {
    console.error('获取训练数据文件列表失败', error)
  }
}

const onBaseModelChange = () => {
  trainParams.model_size = '2.9B'
}

const startTraining = async () => {
  try {
    // 保存参数到 localStorage
    localStorage.setItem('trainParams', JSON.stringify(trainParams))
    localStorage.setItem('loraParams', JSON.stringify(loraParams))
    localStorage.setItem('trainDataFolder', trainDataFolder.value)
    
    await axios.post('/api/train/start', {
      base_model: trainParams.base_model,
      model_size: trainParams.model_size,
      train_data: trainParams.train_data,
      train_data_folder: trainDataFolder.value.replace('./', '') || 'out',
      micro_bsz: trainParams.micro_bsz,
      epoch_save: trainParams.epoch_save,
      epoch_steps: trainParams.epoch_steps,
      ctx_len: trainParams.ctx_len,
      epoch_count: trainParams.epoch_count,
      lr_init: trainParams.lr_init,
      lr_final: trainParams.lr_final,
      lora_r: loraParams.r,
      lora_alpha: loraParams.lora_alpha,
      lora_dropout: loraParams.lora_dropout
    })
    trainingStatus.value = 'running'
    logs.value = []
    lossData.value = []
    currentEpoch.value = 0
    currentStep.value = 0
    startPolling()
    ElMessage.success('训练已启动')
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '启动训练失败')
  }
}

const stopTraining = async () => {
  try {
    await axios.post('/api/train/stop')
    trainingStatus.value = 'idle'
    logs.value = []
    lossData.value = []
    currentEpoch.value = 0
    currentStep.value = 0
    stopPolling()
    ElMessage.success('训练已停止')
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '停止训练失败')
  }
}

const handleStopTraining = async () => {
  stopConfirmDialogVisible.value = false
  await stopTraining()
}

const clearSavedParams = () => {
  localStorage.removeItem('trainParams')
  localStorage.removeItem('loraParams')
  localStorage.removeItem('trainDataFolder')
  ElMessage.success('已清除已保存的参数')
}

const startPolling = () => {
  pollTimer = setInterval(async () => {
    try {
      const [statusRes, logsRes, lossRes] = await Promise.all([
        axios.get('/api/train/status'),
        axios.get('/api/train/logs'),
        axios.get('/api/train/loss')
      ])

      const status = statusRes.data
      currentEpoch.value = status.current_epoch
      currentStep.value = status.current_step
      currentLr.value = status.current_lr || 0
      itsPerSec.value = status.its_per_sec || 0
      sumLoss.value = status.sum_loss || 0

      logs.value = logsRes.data

      nextTick(() => {
        if (autoScroll.value) {
          if (inlineLogScrollbarRef.value) {
            inlineLogScrollbarRef.value.setScrollTop(inlineLogScrollbarRef.value.wrapRef.scrollHeight)
          }
          if (logDialogVisible.value && logScrollbarRef.value) {
            logScrollbarRef.value.setScrollTop(logScrollbarRef.value.wrapRef.scrollHeight)
          }
        }
      })

      lossData.value = lossRes.data
      drawLossChart()

      if (status.status === 'completed' || status.status === 'idle') {
        trainingStatus.value = status.status
        stopPolling()
        if (status.status === 'completed') {
          ElMessage.success('训练完成')
        }
      }
    } catch (error) {
      console.error('轮询失败', error)
    }
  }, 1000)
}

const stopPolling = () => {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

const drawLossChart = () => {
  if (!lossCanvas.value || lossData.value.length === 0) return

  const canvas = lossCanvas.value
  const ctx = canvas.getContext('2d')
  const width = canvas.width
  const height = canvas.height

  ctx.clearRect(0, 0, width, height)

  ctx.strokeStyle = '#409eff'
  ctx.lineWidth = 2
  ctx.beginPath()

  const maxLoss = Math.max(...lossData.value.map(d => d.loss))
  const minLoss = Math.min(...lossData.value.map(d => d.loss))
  const lossRange = maxLoss - minLoss || 1

  lossData.value.forEach((point, index) => {
    const x = (index / (lossData.value.length - 1)) * width
    const y = height - ((point.loss - minLoss) / lossRange) * (height - 40) - 20
    if (index === 0) {
      ctx.moveTo(x, y)
    } else {
      ctx.lineTo(x, y)
    }
  })

  ctx.stroke()
}

onMounted(async () => {
  // 加载 localStorage 中的参数
  const savedTrainParams = localStorage.getItem('trainParams')
  if (savedTrainParams) {
    Object.assign(trainParams, JSON.parse(savedTrainParams))
  }
  
  const savedLoraParams = localStorage.getItem('loraParams')
  if (savedLoraParams) {
    Object.assign(loraParams, JSON.parse(savedLoraParams))
  }
  
  const savedTrainDataFolder = localStorage.getItem('trainDataFolder')
  if (savedTrainDataFolder) {
    trainDataFolder.value = savedTrainDataFolder
    // 加载数据文件列表
    const folder = trainDataFolder.value.replace('./', '') || ''
    try {
      const res = await axios.get('/api/data/files', { params: { folder } })
      trainDataFileList.value = res.data
    } catch (error) {
      console.error('获取训练数据文件列表失败', error)
    }
  }
  
  loadBaseModels()
  loadTrainDataFolders()
  
  try {
    const statusRes = await axios.get('/api/train/status')
    const status = statusRes.data
    if (status.status === 'running') {
      trainingStatus.value = 'running'
      currentEpoch.value = status.current_epoch
      currentStep.value = status.current_step
      const [logsRes, lossRes] = await Promise.all([
        axios.get('/api/train/logs'),
        axios.get('/api/train/loss')
      ])
      logs.value = logsRes.data
      lossData.value = lossRes.data
      startPolling()
    }
  } catch (error) {
    console.error('检查训练状态失败', error)
  }
})

onUnmounted(() => {
  stopPolling()
})
</script>

<style scoped>
.content-wrapper {
  display: flex;
  gap: 20px;
}

.left-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.right-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.param-card :deep(.el-form-item__label) {
  font-weight: 500;
}

.progress-info {
  padding: 20px;
}

.progress-item {
  display: flex;
  align-items: center;
  margin-bottom: 10px;
}

.progress-label {
  width: 70px;
  font-size: 13px;
  color: #606266;
  flex-shrink: 0;
}

.progress-bar {
  flex: 1;
}

.progress-detail {
  display: flex;
  justify-content: space-between;
  margin-top: 15px;
  font-size: 14px;
  color: #606266;
}

.progress-metrics {
  display: flex;
  justify-content: space-between;
  margin-top: 10px;
  padding: 8px 12px;
  background: #f5f7fa;
  border-radius: 4px;
  font-size: 13px;
  color: #409eff;
}

.loss-chart {
  height: 200px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.loss-chart canvas {
  width: 100%;
  height: 100%;
}

.loss-empty {
  color: #909399;
  font-size: 14px;
}

.log-card {
  flex: 1;
  min-height: 200px;
}

.log-card :deep(.el-card__body) {
  height: 200px;
  padding: 0;
}

.log-scrollbar {
  height: 100%;
}

.log-content {
  padding: 12px;
  font-family: 'Courier New', monospace;
  font-size: 14px;
  font-weight: bold;
  line-height: 1.6;
}

.log-line {
  color: #606266;
  white-space: pre-wrap;
  word-break: break-all;
  text-align: left;
}

.log-empty {
  color: #909399;
  font-size: 14px;
  text-align: center;
  padding: 20px;
}

.action-bar {
  display: flex;
  justify-content: center;
  gap: 15px;
}

.action-bar .el-button {
  width: 200px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.log-dialog-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
}

.log-dialog-scrollbar {
  height: calc(70vh - 80px);
}
</style>