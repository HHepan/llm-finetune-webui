<template>
  <div class="m-train-page">
    <!-- 顶部药丸式分段切换 -->
    <div class="m-seg-control">
      <div
        :class="['m-seg-item', { active: activeTab === 'record' }]"
        @click="activeTab = 'record'"
      >训练记录</div>
      <div
        :class="['m-seg-item', { active: activeTab === 'start' }]"
        @click="activeTab = 'start'"
      >启动训练</div>
    </div>

    <!-- ====== 训练记录 ====== -->
    <div v-show="activeTab === 'record'">
      <div v-if="loading" class="m-empty">
        <div class="m-spinner m-spinner--lg"></div>
        <span style="margin-top:6px;">加载中...</span>
      </div>
      <div v-else-if="trainRecords.length === 0" class="m-empty">
        <div class="m-empty-icon-svg">
          <svg width="44" height="44" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
            <polyline points="14 2 14 8 20 8"/>
            <line x1="16" y1="13" x2="8" y2="13"/>
            <line x1="16" y1="17" x2="8" y2="17"/>
            <line x1="10" y1="9" x2="8" y2="9" opacity="0.4"/>
          </svg>
        </div>
        <span>暂无训练记录</span>
      </div>
      <div v-for="rec in paginatedRecords" :key="rec.folder_name" class="m-list-item">
        <div class="m-list-item-header">
          <span class="m-time-badge">{{ rec.time }}</span>
          <span :class="['m-tag', statusClass(rec.status)]">
            {{ statusLabel(rec.status) }}
          </span>
        </div>
        <div class="m-train-info">
          <div class="m-train-info-row">
            <span class="m-info-key">模型</span>
            <span class="m-info-val">{{ rec.base_model }}</span>
          </div>
          <div class="m-train-info-row">
            <span class="m-info-key">数据</span>
            <span class="m-info-val">{{ rec.train_data }}</span>
          </div>
          <div class="m-train-info-row">
            <span class="m-info-key">目录</span>
            <span class="m-info-val mono">{{ rec.folder_name }}</span>
          </div>
          <div v-if="rec.state" class="m-train-progress-section">
            <div class="m-progress-row">
              <span class="m-progress-label">Epoch</span>
              <el-progress :percentage="getEpochProgress(rec)" :stroke-width="6" class="m-progress-bar" />
              <span class="m-progress-num">{{ rec.state?.current_epoch || 0 }}/{{ rec.params?.epoch_count || 1 }}</span>
            </div>
            <div class="m-progress-row">
              <span class="m-progress-label">Step</span>
              <el-progress :percentage="getStepProgress(rec)" :stroke-width="6" class="m-progress-bar" />
              <span class="m-progress-num">{{ rec.state?.current_step || 0 }}/{{ Math.floor(rec.params?.epoch_steps / rec.params?.micro_bsz) || 0 }}</span>
            </div>
          </div>
        </div>
        <div class="m-list-item-footer">
          <el-button size="small" plain @click="showDetail(rec)">查看详情</el-button>
        </div>
      </div>

      <!-- 分页 -->
      <div class="m-pager">
        <button :disabled="currentPage <= 1" @click="currentPage--; paginate()">上一页</button>
        <span>{{ currentPage }} / {{ totalPages }}</span>
        <button :disabled="currentPage >= totalPages" @click="currentPage++; paginate()">下一页</button>
      </div>
    </div>

    <!-- ====== 启动训练 ====== -->
    <div v-show="activeTab === 'start'" class="m-train-start">
      <div class="m-empty" style="padding:60px 20px;">
        <div class="m-empty-icon">🖥️</div>
        <span style="font-size:15px;color:var(--c-text-muted);">请前往 web 端启动训练</span>
      </div>
    </div>

    <!-- ====== 详情弹窗 ====== -->
    <div v-if="showDetailModal" class="m-modal-overlay" @click.self="closeDetailModal">
      <div class="m-modal-content" style="max-height:90vh;" ref="modalContentRef">
        <!-- 粘性顶部：标题 + tab 选择器 -->
        <div class="m-modal-sticky">
          <div class="m-modal-header">
            <span>训练详情</span>
            <span class="m-modal-close" @click="closeDetailModal">&times;</span>
          </div>
          <div class="m-detail-tabs">
            <div :class="['m-detail-tab', { active: detailTab === 'info' }]" @click="detailTab = 'info'">信息</div>
            <div :class="['m-detail-tab', { active: detailTab === 'loss' }]" @click="detailTab = 'loss'">损失</div>
            <div :class="['m-detail-tab', { active: detailTab === 'logs' }]" @click="detailTab = 'logs'">日志</div>
          </div>
        </div>

        <div v-if="detailTab === 'info'">
          <div class="m-detail-section-title">基本信息</div>
          <div class="m-detail-grid">
            <div class="m-detail-item"><span class="m-di-key">时间</span><span>{{ detail.time }}</span></div>
            <div class="m-detail-item"><span class="m-di-key">模型</span><span>{{ detail.base_model }}</span></div>
            <div class="m-detail-item"><span class="m-di-key">数据</span><span>{{ detail.train_data }}</span></div>
            <div class="m-detail-item">
              <span class="m-di-key">状态</span>
              <span :class="['m-tag', statusClass(detail.state?.status)]">{{ detail.state?.status || '未知' }}</span>
            </div>
          </div>

          <div class="m-detail-section-title">训练进度</div>
          <div class="m-detail-progress-block">
            <div class="m-progress-row">
              <span class="m-progress-label">Epoch</span>
              <el-progress :percentage="detailEpochPct" :stroke-width="6" class="m-progress-bar" />
            </div>
            <div class="m-progress-row">
              <span class="m-progress-label">Step</span>
              <el-progress :percentage="detailStepPct" :stroke-width="6" class="m-progress-bar" />
            </div>
            <div class="m-detail-stats">
              <span>Epoch: {{ detail.state?.current_epoch || 0 }}/{{ detail.params?.epoch_count || 1 }}</span>
              <span>loss: {{ detail.state?.sum_loss?.toFixed(3) || 0 }}</span>
            </div>
          </div>

          <div class="m-detail-section-title">训练参数</div>
          <div class="m-detail-param-grid">
            <div class="m-detail-param"><span class="m-dp-key">参数量</span><span>{{ detail.params?.model_size || '2.9B' }}</span></div>
            <div class="m-detail-param"><span class="m-dp-key">micro_bsz</span><span>{{ detail.params?.micro_bsz || 1 }}</span></div>
            <div class="m-detail-param"><span class="m-dp-key">epoch_save</span><span>{{ detail.params?.epoch_save || 1 }}</span></div>
            <div class="m-detail-param"><span class="m-dp-key">epoch_steps</span><span>{{ detail.params?.epoch_steps || 1000 }}</span></div>
            <div class="m-detail-param"><span class="m-dp-key">ctx_len</span><span>{{ detail.params?.ctx_len || 512 }}</span></div>
            <div class="m-detail-param"><span class="m-dp-key">epoch_count</span><span>{{ detail.params?.epoch_count || 1 }}</span></div>
            <div class="m-detail-param"><span class="m-dp-key">lr_init</span><span>{{ detail.params?.lr_init || '2e-5' }}</span></div>
            <div class="m-detail-param"><span class="m-dp-key">lr_final</span><span>{{ detail.params?.lr_final || '2e-5' }}</span></div>
          </div>

          <div class="m-detail-section-title">LoRA 参数</div>
          <div class="m-detail-param-grid">
            <div class="m-detail-param"><span class="m-dp-key">r (rank)</span><span>{{ detail.params?.lora_r || 32 }}</span></div>
            <div class="m-detail-param"><span class="m-dp-key">lora_alpha</span><span>{{ detail.params?.lora_alpha || 32 }}</span></div>
            <div class="m-detail-param"><span class="m-dp-key">lora_dropout</span><span>{{ detail.params?.lora_dropout || 0.01 }}</span></div>
          </div>
        </div>

        <div v-if="detailTab === 'loss'" class="m-empty" style="padding:40px 20px;">
          <div class="m-empty-icon">📈</div>
          <span style="font-size:14px;color:var(--c-text-muted);">请前往 web 端查看损失曲线</span>
        </div>

        <div v-if="detailTab === 'logs'" class="m-empty" style="padding:40px 20px;">
          <div class="m-empty-icon">📝</div>
          <span style="font-size:14px;color:var(--c-text-muted);">请前往 web 端查看训练日志</span>
        </div>
      </div>
    </div>

    <!-- ====== 停止确认 ====== -->
    <div v-if="showStopConfirm" class="m-modal-overlay" @click.self="showStopConfirm = false">
      <div class="m-modal-content">
        <div class="m-modal-header">
          <span>确认停止训练</span>
          <span class="m-modal-close" @click="showStopConfirm = false">&times;</span>
        </div>
        <p style="font-size:14px;color:var(--c-text-secondary);">确定要停止训练吗？停止后训练将被中断。</p>
        <div style="display:flex;gap:10px;margin-top:16px;">
          <el-button size="small" style="flex:1;" @click="showStopConfirm = false">取消</el-button>
          <el-button size="small" type="danger" style="flex:1;" @click="handleStop">确定停止</el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import axios from 'axios'

// ==== Tab 切换 ====
const activeTab = ref('record')

// ==== 训练记录 ====
const trainRecords = ref([])
const loading = ref(false)
const currentPage = ref(1)
const pageSize = ref(10)
const totalPages = computed(() => Math.max(1, Math.ceil(trainRecords.value.length / pageSize.value)))
const paginatedRecords = computed(() => {
  const s = (currentPage.value - 1) * pageSize.value
  return trainRecords.value.slice(s, s + pageSize.value)
})

// 状态映射
const statusClass = (status) => {
  const map = { completed: 'm-tag-success', running: 'm-tag-warning', stopped: 'm-tag-info' }
  return map[status] || 'm-tag-info'
}
const statusLabel = (status) => {
  const map = { completed: '已完成', running: '训练中', stopped: '已停止' }
  return map[status] || '未知'
}

const getEpochProgress = (row) => {
  if (!row.params || !row.state) return 0
  const total = row.params.epoch_count || 1
  const cur = row.status === 'completed' ? total : (row.state.current_epoch || 0)
  return Math.round((cur / total) * 100)
}

const getStepProgress = (row) => {
  if (!row.params || !row.state) return 0
  const ts = Math.floor(row.params.epoch_steps / row.params.micro_bsz) || 1
  const cur = row.status === 'completed' ? ts : (row.state.current_step || 0)
  return Math.round((cur / ts) * 100)
}

const loadTrainRecords = async () => {
  loading.value = true
  try {
    const res = await axios.get('/api/train/records')
    trainRecords.value = res.data
  } catch { console.error('获取训练记录失败') }
  finally { loading.value = false }
}

// ==== 详情 ====
const showDetailModal = ref(false)
const detail = ref({})
const detailTab = ref('info')
const detailFolderName = ref('')
const modalContentRef = ref(null)
const detailEpochPct = computed(() => {
  if (!detail.value.params || !detail.value.state) return 0
  const total = detail.value.params.epoch_count || 1
  const cur = detail.value.state.status === 'completed' ? total : (detail.value.state.current_epoch || 0)
  return Math.round((cur / total) * 100)
})
const detailStepPct = computed(() => {
  if (!detail.value.params || !detail.value.state) return 0
  const ts = Math.floor(detail.value.params.epoch_steps / detail.value.params.micro_bsz) || 1
  const cur = detail.value.state.status === 'completed' ? ts : (detail.value.state.current_step || 0)
  return Math.round((cur / ts) * 100)
})

const showDetail = async (row) => {
  detailFolderName.value = row.folder_name
  detailTab.value = 'info'
  detail.value = { ...row }
  showDetailModal.value = true

  // 等弹窗 DOM 渲染完成，立即固定高度
  await nextTick()
  if (modalContentRef.value) {
    const h = modalContentRef.value.offsetHeight
    if (h > 0) modalContentRef.value.style.height = h + 'px'
  }

  // 获取详情数据（异步，不影响已固定的弹窗高度）
  try {
    const res = await axios.get(`/api/train/records/${row.folder_name}`)
    detail.value = { ...row, params: res.data.params, state: res.data.state }
  } catch { ElMessage.error('获取详情失败') }
}

const closeDetailModal = () => {
  showDetailModal.value = false
  // 清除固定高度，下次重新计算
  if (modalContentRef.value) {
    modalContentRef.value.style.height = ''
  }
}

// ==== 停止（占位）====
const showStopConfirm = ref(false)

const handleStop = () => {
  ElMessage.success('停止指令已发送（待实现）')
  showStopConfirm.value = false
}

onMounted(loadTrainRecords)
</script>

<style scoped>
.m-train-page {
  padding-bottom: 8px;
}

/* ====== 药丸式分段控制 ====== */
.m-seg-control {
  display: flex;
  gap: 4px;
  margin-bottom: 14px;
  background: var(--c-border-light);
  border-radius: var(--radius-md);
  padding: 4px;
}

.m-seg-item {
  flex: 1;
  text-align: center;
  padding: 8px 0;
  font-size: 13px;
  font-weight: 600;
  color: var(--c-text-muted);
  cursor: pointer;
  border-radius: var(--radius-sm);
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  user-select: none;
}

.m-seg-item.active {
  background: var(--c-surface);
  color: var(--c-primary);
  box-shadow: var(--shadow-sm);
}

.m-seg-item:active {
  opacity: 0.7;
}

/* ====== 训练信息 ====== */
.m-time-badge {
  font-size: 12px;
  color: var(--c-text-muted);
  background: var(--c-bg);
  padding: 2px 8px;
  border-radius: 6px;
}

.m-train-info {
  font-size: 13px;
  line-height: 1.7;
}

.m-train-info-row {
  display: flex;
  gap: 8px;
  padding: 2px 0;
}

.m-info-key {
  flex-shrink: 0;
  width: 40px;
  font-weight: 600;
  color: var(--c-text-secondary);
  font-size: 12px;
}

.m-info-val {
  color: var(--c-text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.m-info-val.mono {
  font-family: 'SF Mono', 'Menlo', monospace;
  font-size: 12px;
}

/* ====== 进度条区 ====== */
.m-train-progress-section {
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px solid var(--c-border-light);
}

.m-progress-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}

.m-progress-row:last-child {
  margin-bottom: 0;
}

.m-progress-label {
  font-size: 11px;
  font-weight: 600;
  color: var(--c-text-muted);
  flex-shrink: 0;
  width: 42px;
  text-align: right;
  letter-spacing: 0.5px;
  text-transform: uppercase;
}

.m-progress-bar {
  flex: 1;
}

.m-progress-bar :deep(.el-progress-bar__outer) {
  background: var(--c-border-light);
  border-radius: 10px;
}

.m-progress-bar :deep(.el-progress-bar__inner) {
  background: linear-gradient(90deg, var(--c-primary), var(--c-primary-light));
  border-radius: 10px;
  transition: width 0.4s ease;
}

.m-progress-num {
  font-size: 11px;
  font-weight: 600;
  color: var(--c-text-muted);
  flex-shrink: 0;
  min-width: 60px;
  text-align: right;
  font-variant-numeric: tabular-nums;
}

/* ====== 详情弹窗 ====== */
.m-modal-sticky {
  position: sticky;
  top: 0;
  z-index: 2;
  background: var(--c-surface);
  padding-bottom: 16px;
}

.m-modal-sticky .m-detail-tabs {
  margin-bottom: 0;
}

.m-detail-tabs {
  display: flex;
  gap: 4px;
  margin-bottom: 16px;
  background: var(--c-border-light);
  border-radius: var(--radius-sm);
  padding: 3px;
}

.m-detail-tab {
  flex: 1;
  text-align: center;
  padding: 7px 0;
  font-size: 12px;
  font-weight: 600;
  color: var(--c-text-muted);
  cursor: pointer;
  border-radius: 6px;
  transition: all 0.2s;
}

.m-detail-tab.active {
  background: var(--c-surface);
  color: var(--c-primary);
  box-shadow: var(--shadow-sm);
}

.m-detail-section-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--c-text-primary);
  margin-bottom: 10px;
  padding-left: 0;
}

.m-detail-grid {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-bottom: 16px;
}

.m-detail-item {
  display: flex;
  gap: 12px;
  font-size: 13px;
  color: var(--c-text-primary);
  padding: 6px 0;
  border-bottom: 1px solid var(--c-border-light);
}

.m-detail-item:last-child {
  border-bottom: none;
}

.m-di-key {
  flex-shrink: 0;
  width: 44px;
  font-weight: 500;
  color: var(--c-text-secondary);
}

.m-detail-progress-block {
  background: var(--c-bg);
  border-radius: var(--radius-sm);
  padding: 14px;
  margin-bottom: 16px;
}

.m-detail-stats {
  display: flex;
  gap: 16px;
  font-size: 12px;
  color: var(--c-text-muted);
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px solid var(--c-border-light);
}

.m-detail-param-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  background: var(--c-bg);
  border-radius: var(--radius-sm);
  padding: 14px;
  margin-bottom: 16px;
  font-size: 12px;
}

.m-detail-param {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.m-dp-key {
  font-weight: 600;
  color: var(--c-text-muted);
  font-size: 11px;
}

.m-detail-param span:last-child {
  color: var(--c-text-primary);
  font-weight: 500;
}
</style>