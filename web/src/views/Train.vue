<template>
  <div class="page-container">
    <!-- 顶部导航 -->
    <el-tabs v-model="activeTab" class="train-tabs">
      <el-tab-pane label="训练记录" name="record" />
      <el-tab-pane label="启动训练" name="start" />
    </el-tabs>

    <!-- 训练记录页面 -->
    <div v-show="activeTab === 'record'" class="record-view">
      <el-table v-if="trainRecords.length > 0" :data="paginatedRecords" border stripe style="width: 100%">
        <el-table-column prop="time" label="训练时间" width="180" align="center" />
        <el-table-column prop="base_model" label="基底模型" />
        <el-table-column prop="train_data" label="训练数据" />
        <el-table-column label="操作" width="160" align="center">
          <template #default="{ row }">
            <el-button size="small" type="primary" @click="showDetail(row)">详情</el-button>
            <el-button size="small" type="danger" @click="confirmDeleteRecord(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-empty v-if="trainRecords.length === 0" description="暂无训练记录" />

      <div v-if="trainRecords.length > 0" class="pagination-container">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          :total="totalRecords"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>

      <el-dialog v-model="detailDialogVisible" title="训练详情" width="80%" top="5vh">
        <el-tabs v-model="detailActiveTab" class="detail-tabs">
<el-tab-pane label="基本信息与参数" name="info">
            <div class="detail-info-section">
              <div class="left-panel">
                <el-card class="param-card">
                  <template #header>
                    <div class="card-header">
                      <span>基本信息</span>
                    </div>
                  </template>
                  <el-descriptions :column="1" border label-width="80px">
                    <el-descriptions-item label="训练时间">{{ currentDetail.time }}</el-descriptions-item>
                    <el-descriptions-item label="基底模型">{{ currentDetail.base_model }}</el-descriptions-item>
                    <el-descriptions-item label="训练数据">{{ currentDetail.train_data }}</el-descriptions-item>
                    <el-descriptions-item label="状态">
                      <el-tag type="success">已完成</el-tag>
                    </el-descriptions-item>
                  </el-descriptions>
                </el-card>

                <el-card class="param-card">
                  <template #header>
                    <div class="card-header">
                      <span>训练进度</span>
                    </div>
                  </template>
                  <div class="detail-progress">
                    <div class="progress-item">
                      <span class="progress-label">Epoch 进度</span>
                      <el-progress class="progress-bar" :percentage="100" :stroke-width="12" status="success" />
                    </div>
                    <div class="progress-item">
                      <span class="progress-label">Step 进度</span>
                      <el-progress class="progress-bar" :percentage="100" :stroke-width="12" status="success" />
                    </div>
                    <div class="progress-detail">
                      <span>Epoch: {{ currentDetail.params?.epoch_count || 1 }} / {{ currentDetail.params?.epoch_count || 1 }}</span>
                      <span>Step: {{ currentDetail.params?.epoch_steps || 1000 }} / {{ currentDetail.params?.epoch_steps || 1000 }}</span>
                    </div>
                    <div class="progress-metrics">
                      <span>loss: {{ (Math.random() * 2).toFixed(3) }}</span>
                      <span>lr: {{ currentDetail.params?.lr_init || 2e-5 }}</span>
                    </div>
                  </div>
                </el-card>
              </div>

              <div class="right-panel">
                <el-card class="param-card">
                  <template #header>
                    <div class="card-header">
                      <span>训练参数</span>
                    </div>
                  </template>
                  <el-descriptions :column="2" border label-width="100px">
                    <el-descriptions-item label="模型参数量">{{ currentDetail.params?.model_size || '2.9B' }}</el-descriptions-item>
                    <el-descriptions-item label="micro_bsz">{{ currentDetail.params?.micro_bsz || 1 }}</el-descriptions-item>
                    <el-descriptions-item label="epoch_save">{{ currentDetail.params?.epoch_save || 1 }}</el-descriptions-item>
                    <el-descriptions-item label="epoch_steps">{{ currentDetail.params?.epoch_steps || 1000 }}</el-descriptions-item>
                    <el-descriptions-item label="ctx_len">{{ currentDetail.params?.ctx_len || 512 }}</el-descriptions-item>
                    <el-descriptions-item label="epoch_count">{{ currentDetail.params?.epoch_count || 1 }}</el-descriptions-item>
                    <el-descriptions-item label="lr_init">{{ currentDetail.params?.lr_init || 2e-5 }}</el-descriptions-item>
                    <el-descriptions-item label="lr_final">{{ currentDetail.params?.lr_final || 2e-5 }}</el-descriptions-item>
                  </el-descriptions>
                </el-card>

                <el-card class="param-card">
                  <template #header>
                    <div class="card-header">
                      <span>LoRA参数</span>
                    </div>
                  </template>
                  <el-descriptions :column="2" border label-width="100px">
                    <el-descriptions-item label="r (rank)">{{ currentDetail.params?.lora_r || 32 }}</el-descriptions-item>
                    <el-descriptions-item label="lora_alpha">{{ currentDetail.params?.lora_alpha || 32 }}</el-descriptions-item>
                    <el-descriptions-item label="lora_dropout">{{ currentDetail.params?.lora_dropout || 0.01 }}</el-descriptions-item>
                  </el-descriptions>
                </el-card>
              </div>
            </div>
          </el-tab-pane>

          <el-tab-pane label="损失曲线" name="loss">
            <div class="loss-chart detail-loss-chart">
              <canvas ref="detailLossCanvas" width="600" height="250"></canvas>
            </div>
          </el-tab-pane>

          <el-tab-pane label="训练日志" name="logs">
            <el-scrollbar class="detail-log-scrollbar">
              <div class="log-content">
                <div v-for="(log, index) in currentDetail.logs || []" :key="index" class="log-line">{{ log }}</div>
                <div v-if="!currentDetail.logs || currentDetail.logs.length === 0" class="log-empty">
                  暂无日志
                </div>
              </div>
            </el-scrollbar>
          </el-tab-pane>
        </el-tabs>
      </el-dialog>
    </div>

    <!-- 启动训练页面 -->
    <div v-show="activeTab === 'start'" class="content-wrapper">
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
              <div style="display: flex; align-items: center; width: 100%; gap: 8px;">
                <el-input disabled value="llm-finetune-webui/workspace/checkpoints/" style="flex: 0 0 70%;" />
                <el-input
                  v-model="saveFolder"
                  placeholder="请输入文件夹名称（必填）"
                  style="flex: 0 0 30%;"
                  :class="{ 'is-invalid': saveFolderInvalid }"
                  @input="validateSaveFolder"
                />
              </div>
              <div v-if="saveFolderInvalid" class="el-form-item__error">只允许输入字母、数字、下划线和连字符</div>
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
              <span>Step: {{ currentStep }} / {{ Math.floor(trainParams.epoch_steps / trainParams.micro_bsz) }}</span>
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
            :disabled="!canStartTraining"
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
import { ElMessage, ElMessageBox } from 'element-plus'
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

const saveFolder = ref('')
const saveFolderInvalid = ref(false)

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
  if (trainParams.epoch_steps === 0 || trainParams.micro_bsz === 0) return 0
  const totalSteps = trainParams.epoch_steps / trainParams.micro_bsz
  return Math.round((currentStep.value / totalSteps) * 100)
})

const canStartTraining = computed(() => {
  return (
    !saveFolderInvalid.value &&
    saveFolder.value.trim() !== '' &&
    trainParams.base_model !== '' &&
    trainParams.train_data !== ''
  )
})

const validateSaveFolder = () => {
  const regex = /^[a-zA-Z0-9_-]*$/
  if (saveFolder.value && !regex.test(saveFolder.value)) {
    saveFolderInvalid.value = true
  } else {
    saveFolderInvalid.value = false
  }
}
const logs = ref([])
const lossData = ref([])
const lossCanvas = ref(null)

const logDialogVisible = ref(false)
const autoScroll = ref(true)
const stopConfirmDialogVisible = ref(false)
const logScrollbarRef = ref(null)
const inlineLogScrollbarRef = ref(null)

const activeTab = ref('record')

const detailActiveTab = ref('info')
const detailLossCanvas = ref(null)

const trainRecords = ref([
  { id: 1, time: '2026-04-13 12:10', base_model: 'xxxxxxxxxxxxxxxxx.pth', train_data: 'all_data.jsonl', params: { model_size: '2.9B', micro_bsz: 1, epoch_save: 1, epoch_steps: 1000, ctx_len: 512, epoch_count: 3, lr_init: 2e-5, lr_final: 2e-5, lora_r: 32, lora_alpha: 32, lora_dropout: 0.01 }, logs: ['[INFO] Loading model...', '[INFO] Model loaded successfully', '[INFO] Starting training...', 'Epoch 1/3, Step 100/1000, loss: 1.234', 'Epoch 2/3, Step 500/1000, loss: 0.876', 'Epoch 3/3, Step 1000/1000, loss: 0.543', '[INFO] Training completed'] },
  { id: 2, time: '2026-04-12 10:00', base_model: 'model2.pth', train_data: 'data2.jsonl', params: { model_size: '1.5B', micro_bsz: 2, epoch_save: 1, epoch_steps: 800, ctx_len: 512, epoch_count: 2, lr_init: 1e-4, lr_final: 1e-4, lora_r: 64, lora_alpha: 64, lora_dropout: 0.01 }, logs: ['[INFO] Loading model...', '[INFO] Model loaded successfully', '[INFO] Starting training...', 'Epoch 1/2, loss: 1.456', 'Epoch 2/2, loss: 0.987', '[INFO] Training completed'] },
  { id: 3, time: '2026-04-11 09:30', base_model: 'RWKV-4-1.5B.pth', train_data: 'dataset_v2.jsonl', params: { model_size: '1.5B', micro_bsz: 1, epoch_save: 1, epoch_steps: 1200, ctx_len: 512, epoch_count: 5, lr_init: 3e-5, lr_final: 3e-5, lora_r: 32, lora_alpha: 32, lora_dropout: 0.01 }, logs: ['[INFO] Training completed'] },
  { id: 4, time: '2026-04-10 15:20', base_model: 'model_v1.pth', train_data: 'train_final.jsonl', params: { model_size: '2.9B', micro_bsz: 1, epoch_save: 1, epoch_steps: 1000, ctx_len: 512, epoch_count: 3, lr_init: 2e-5, lr_final: 2e-5, lora_r: 16, lora_alpha: 16, lora_dropout: 0.01 }, logs: ['[INFO] Training completed'] },
  { id: 5, time: '2026-04-09 11:00', base_model: 'checkpoint_4.5b.pth', train_data: 'qa_data.jsonl', params: { model_size: '0.4B', micro_bsz: 1, epoch_save: 1, epoch_steps: 600, ctx_len: 256, epoch_count: 4, lr_init: 1e-5, lr_final: 1e-5, lora_r: 64, lora_alpha: 64, lora_dropout: 0.02 }, logs: ['[INFO] Training completed'] },
  { id: 6, time: '2026-04-08 14:45', base_model: 'base_model_v3.pth', train_data: 'chat_data.jsonl', params: { model_size: '2.9B', micro_bsz: 1, epoch_save: 1, epoch_steps: 500, ctx_len: 512, epoch_count: 2, lr_init: 5e-5, lr_final: 5e-5, lora_r: 32, lora_alpha: 32, lora_dropout: 0.01 }, logs: ['[INFO] Training completed'] },
  { id: 7, time: '2026-04-07 08:30', base_model: 'rwkv_2.9b.pth', train_data: 'medical_qa.jsonl', params: { model_size: '2.9B', micro_bsz: 1, epoch_save: 1, epoch_steps: 1500, ctx_len: 512, epoch_count: 6, lr_init: 2e-5, lr_final: 2e-5, lora_r: 48, lora_alpha: 48, lora_dropout: 0.01 }, logs: ['[INFO] Training completed'] },
  { id: 8, time: '2026-04-06 16:10', base_model: 'pretrain_model.pth', train_data: 'user_logs.jsonl', params: { model_size: '2.9B', micro_bsz: 2, epoch_save: 1, epoch_steps: 1000, ctx_len: 512, epoch_count: 3, lr_init: 3e-5, lr_final: 3e-5, lora_r: 32, lora_alpha: 32, lora_dropout: 0.01 }, logs: ['[INFO] Training completed'] },
  { id: 9, time: '2026-04-05 10:20', base_model: 'finetune_latest.pth', train_data: 'code_examples.jsonl', params: { model_size: '7B', micro_bsz: 1, epoch_save: 1, epoch_steps: 2000, ctx_len: 1024, epoch_count: 5, lr_init: 1e-5, lr_final: 1e-5, lora_r: 64, lora_alpha: 64, lora_dropout: 0.01 }, logs: ['[INFO] Training completed'] },
  { id: 10, time: '2026-04-04 13:00', base_model: 'model_v2.pth', train_data: 'instruction_data.jsonl', params: { model_size: '2.9B', micro_bsz: 1, epoch_save: 1, epoch_steps: 500, ctx_len: 512, epoch_count: 2, lr_init: 4e-5, lr_final: 4e-5, lora_r: 32, lora_alpha: 32, lora_dropout: 0.01 }, logs: ['[INFO] Training completed'] },
  { id: 11, time: '2026-04-03 09:15', base_model: 'adapter_model.pth', train_data: 'domain_knowledge.jsonl', params: { model_size: '0.1B', micro_bsz: 1, epoch_save: 1, epoch_steps: 800, ctx_len: 256, epoch_count: 4, lr_init: 2e-5, lr_final: 2e-5, lora_r: 48, lora_alpha: 48, lora_dropout: 0.01 }, logs: ['[INFO] Training completed'] },
  { id: 12, time: '2026-04-02 11:40', base_model: 'lora_weights.pth', train_data: 'science_qa.jsonl', params: { model_size: '2.9B', micro_bsz: 1, epoch_save: 1, epoch_steps: 1000, ctx_len: 512, epoch_count: 3, lr_init: 1e-4, lr_final: 1e-4, lora_r: 32, lora_alpha: 32, lora_dropout: 0.01 }, logs: ['[INFO] Training completed'] },
  { id: 13, time: '2026-04-01 14:25', base_model: 'experiment_v1.pth', train_data: 'general_data.jsonl', params: { model_size: '7B', micro_bsz: 1, epoch_save: 1, epoch_steps: 1500, ctx_len: 1024, epoch_count: 5, lr_init: 2e-5, lr_final: 2e-5, lora_r: 64, lora_alpha: 64, lora_dropout: 0.01 }, logs: ['[INFO] Training completed'] },
  { id: 14, time: '2026-03-31 08:50', base_model: 'backup_model.pth', train_data: 'mixed_data.jsonl', params: { model_size: '0.4B', micro_bsz: 1, epoch_save: 1, epoch_steps: 400, ctx_len: 256, epoch_count: 2, lr_init: 3e-5, lr_final: 3e-5, lora_r: 16, lora_alpha: 16, lora_dropout: 0.02 }, logs: ['[INFO] Training completed'] },
  { id: 15, time: '2026-03-30 10:30', base_model: 'production.pth', train_data: 'production_data.jsonl', params: { model_size: '2.9B', micro_bsz: 1, epoch_save: 1, epoch_steps: 2000, ctx_len: 512, epoch_count: 6, lr_init: 2e-5, lr_final: 2e-5, lora_r: 32, lora_alpha: 32, lora_dropout: 0.01 }, logs: ['[INFO] Training completed'] },
])

const currentPage = ref(1)
const pageSize = ref(10)
const totalRecords = computed(() => trainRecords.value.length)

const paginatedRecords = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  const end = start + pageSize.value
  return trainRecords.value.slice(start, end)
})

const handleSizeChange = (val) => {
  pageSize.value = val
  currentPage.value = 1
}

const handleCurrentChange = (val) => {
  currentPage.value = val
}

const detailDialogVisible = ref(false)
const currentDetail = ref({})

const showDetail = (row) => {
  currentDetail.value = row
  detailDialogVisible.value = true
}

const confirmDeleteRecord = async (row) => {
  try {
    await ElMessageBox.confirm(`确定要删除该训练记录吗？`, '删除确认', {
      confirmButtonText: '确定删除',
      cancelButtonText: '取消',
      type: 'warning'
    })
    trainRecords.value = trainRecords.value.filter(r => r.id !== row.id)
    const total = trainRecords.value.length
    const maxPage = Math.ceil(total / pageSize.value)
    if (currentPage.value > maxPage && maxPage > 0) {
      currentPage.value = maxPage
    }
    ElMessage.success('删除成功')
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

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
    localStorage.setItem('saveFolder', saveFolder.value)
    
    await axios.post('/api/train/start', {
      base_model: trainParams.base_model,
      model_size: trainParams.model_size,
      train_data: trainParams.train_data,
      train_data_folder: trainDataFolder.value.replace('./', '') || 'out',
      save_folder: saveFolder.value,
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
  localStorage.removeItem('saveFolder')
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
        if (status.status === 'completed') {
          trainingStatus.value = 'idle'
          currentEpoch.value = trainParams.epoch_count
          currentStep.value = Math.floor(trainParams.epoch_steps / trainParams.micro_bsz)
          ElMessage.success('训练完成')
        } else {
          trainingStatus.value = 'idle'
        }
        stopPolling()
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
  
  const savedSaveFolder = localStorage.getItem('saveFolder')
  if (savedSaveFolder) {
    saveFolder.value = savedSaveFolder
    validateSaveFolder()
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
.train-tabs {
  margin-bottom: 20px;
}

.record-view {
  background: #fff;
  padding: 20px;
  border-radius: 8px;
}

.pagination-container {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}

.detail-tabs {
  margin-top: 10px;
}

.detail-info-section {
  display: flex;
  gap: 20px;
}

.detail-info-section .left-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.detail-info-section .right-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.detail-info-section .el-divider {
  margin: 10px 0;
  text-align: left;
}

.detail-info-section .el-divider::before,
.detail-info-section .el-divider::after {
  border-color: #dcdfe6;
}

.detail-progress {
  padding: 20px;
}

.detail-progress .progress-item {
  display: flex;
  align-items: center;
  margin-bottom: 15px;
}

.detail-progress .progress-label {
  width: 80px;
  font-size: 13px;
  color: #606266;
  flex-shrink: 0;
}

.detail-progress .progress-bar {
  flex: 1;
}

.detail-progress .progress-detail {
  display: flex;
  justify-content: space-between;
  margin-top: 15px;
  font-size: 14px;
  color: #606266;
}

.detail-progress .progress-metrics {
  display: flex;
  justify-content: space-between;
  margin-top: 10px;
  padding: 8px 12px;
  background: #f0f9eb;
  border-radius: 4px;
  font-size: 13px;
  color: #67c23a;
}

.loss-chart.detail-loss-chart {
  height: 280px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.loss-chart.detail-loss-chart canvas {
  width: 100%;
  height: 100%;
}

.detail-log-scrollbar {
  height: 400px;
}

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

.is-invalid :deep(.el-input__wrapper) {
  box-shadow: 0 0 0 1px #f56c6c inset;
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