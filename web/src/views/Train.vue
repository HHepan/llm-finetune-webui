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
            <el-form-item label="基底模型">
              <el-select v-model="trainParams.base_model" placeholder="请选择基底模型" style="width: 100%">
                <el-option
                  v-for="model in modelList"
                  :key="model"
                  :label="model"
                  :value="model"
                />
              </el-select>
            </el-form-item>

            <el-form-item label="训练数据">
              <el-select v-model="trainParams.train_data" placeholder="请选择训练数据" style="width: 100%">
                <el-option
                  v-for="data in dataList"
                  :key="data"
                  :label="data"
                  :value="data"
                />
              </el-select>
            </el-form-item>

            <el-form-item label="micro_bsz">
              <el-tooltip content="微批次大小，根据显存大小调整，微调时从 1 开始逐渐增大" placement="top">
                <el-input-number v-model="trainParams.micro_bsz" :min="1" :max="64" style="width: 100%" />
              </el-tooltip>
            </el-form-item>

            <el-form-item label="epoch_save">
              <el-tooltip content="每隔多少个训练轮次保存一次 LoRA 文件，注意存储空间是否充足" placement="top">
                <el-input-number v-model="trainParams.epoch_save" :min="1" :max="100" style="width: 100%" />
              </el-tooltip>
            </el-form-item>

            <el-form-item label="epoch_steps">
              <el-tooltip content="每个训练轮次的步数，增加会拉长单个 epoch 的训练时间" placement="top">
                <el-input-number v-model="trainParams.epoch_steps" :min="1" :max="10000" style="width: 100%" />
              </el-tooltip>
            </el-form-item>

            <el-form-item label="ctx_len">
              <el-tooltip content="微调模型的上下文长度，建议根据语料长度修改" placement="top">
                <el-input-number v-model="trainParams.ctx_len" :min="128" :max="4096" :step="128" style="width: 100%" />
              </el-tooltip>
            </el-form-item>

            <el-form-item label="epoch_count">
              <el-tooltip content="总训练轮次" placement="top">
                <el-input-number v-model="trainParams.epoch_count" :min="1" :max="100" style="width: 100%" />
              </el-tooltip>
            </el-form-item>

            <el-form-item label="lr_init">
              <el-tooltip content="初始学习率，DiSHA 建议 2e-5 ，最大不超过 1e-4" placement="top">
                <el-input-number v-model="trainParams.lr_init" :min="1e-6" :max="1e-4" :step="1e-6" :precision="5" style="width: 100%" />
              </el-tooltip>
            </el-form-item>

            <el-form-item label="lr_final">
              <el-tooltip content="最终学习率，建议和初始学习率保持一致" placement="top">
                <el-input-number v-model="trainParams.lr_final" :min="1e-6" :max="1e-4" :step="1e-6" :precision="5" style="width: 100%" />
              </el-tooltip>
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
                <el-input-number v-model="loraParams.r" :min="1" :max="256" style="width: 100%" />
              </el-tooltip>
            </el-form-item>

            <el-form-item label="lora_alpha">
              <el-tooltip content="LoRA 微调的 alpha 参数（缩放因子）" placement="top">
                <el-input-number v-model="loraParams.lora_alpha" :min="1" :max="256" style="width: 100%" />
              </el-tooltip>
            </el-form-item>

            <el-form-item label="lora_dropout">
              <el-tooltip content="LoRA 微调的丢弃率，建议使用 0.01" placement="top">
                <el-input-number v-model="loraParams.lora_dropout" :min="0" :max="1" :step="0.01" :precision="2" style="width: 100%" />
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
            <el-progress :percentage="trainingProgress" :stroke-width="20" />
            <div class="progress-detail">
              <span>Epoch: {{ currentEpoch }} / {{ trainParams.epoch_count }}</span>
              <span>Step: {{ currentStep }} / {{ trainParams.epoch_steps }}</span>
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
            @click="stopTraining"
          >
            停止训练
          </el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { FullScreen } from '@element-plus/icons-vue'
import axios from 'axios'

const trainParams = reactive({
  base_model: '',
  train_data: '',
  micro_bsz: 1,
  epoch_save: 1,
  epoch_steps: 1000,
  ctx_len: 512,
  epoch_count: 1,
  lr_init: 2e-5,
  lr_final: 2e-5
})

const loraParams = reactive({
  r: 32,
  lora_alpha: 32,
  lora_dropout: 0.01
})

const modelList = ref([])
const dataList = ref([])

const trainingStatus = ref('idle')
const trainingProgress = ref(0)
const currentEpoch = ref(0)
const currentStep = ref(0)
const logs = ref([])
const lossData = ref([])
const lossCanvas = ref(null)

const logDialogVisible = ref(false)
const autoScroll = ref(true)
const logScrollbarRef = ref(null)
const inlineLogScrollbarRef = ref(null)

const clearLogs = () => {
  logs.value = []
}

let pollTimer = null

const loadBaseModels = async () => {
  try {
    const res = await axios.get('/api/models')
    modelList.value = res.data
  } catch (error) {
    console.error('获取基底模型列表失败', error)
  }
}

const loadTrainData = async () => {
  try {
    const res = await axios.get('/api/data/files', { params: { folder: 'out' } })
    dataList.value = res.data
  } catch (error) {
    console.error('获取训练数据列表失败', error)
  }
}

const startTraining = async () => {
  try {
    await axios.post('/api/train/start', null, {
      params: {
        total_epochs: trainParams.epoch_count,
        total_steps: trainParams.epoch_steps
      }
    })
    trainingStatus.value = 'running'
    logs.value = []
    lossData.value = []
    currentEpoch.value = 0
    currentStep.value = 0
    trainingProgress.value = 0
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
    stopPolling()
    ElMessage.success('训练已停止')
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '停止训练失败')
  }
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
      trainingProgress.value = Math.round(
        ((status.current_epoch - 1) * status.total_steps + status.current_step) /
        (status.total_epochs * status.total_steps) * 100
      )

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

onMounted(() => {
  loadBaseModels()
  loadTrainData()
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

.progress-detail {
  display: flex;
  justify-content: space-between;
  margin-top: 15px;
  font-size: 14px;
  color: #606266;
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