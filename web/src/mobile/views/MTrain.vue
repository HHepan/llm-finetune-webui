<template>
  <div class="m-train-page">
    <!-- 顶部分页切换 -->
    <div style="display:flex;gap:0;margin-bottom:12px;background:#fff;border-radius:10px;overflow:hidden;box-shadow:0 1px 4px rgba(0,0,0,0.06);">
      <div
        :class="['m-seg-control-item', { active: activeTab === 'record' }]"
        @click="activeTab = 'record'"
      >训练记录</div>
      <div
        :class="['m-seg-control-item', { active: activeTab === 'start' }]"
        @click="activeTab = 'start'"
      >
        <span>启动训练</span>
      </div>
    </div>

    <!-- ====== 训练记录 ====== -->
    <div v-show="activeTab === 'record'">
      <div v-if="trainRecords.length === 0" class="m-empty">
        <div class="m-empty-icon">📋</div>
        <span>暂无训练记录</span>
      </div>
      <div v-for="rec in paginatedRecords" :key="rec.folder_name" class="m-list-item">
        <div class="m-list-item-header">
          <span>{{ rec.time }}</span>
          <span :class="['m-tag', rec.status === 'completed' ? 'm-tag-success' : rec.status === 'running' ? 'm-tag-warning' : 'm-tag-info']">
            {{ rec.status === 'completed' ? '已完成' : rec.status === 'running' ? '训练中' : rec.status === 'stopped' ? '已停止' : '未知' }}
          </span>
        </div>
        <div style="font-size:13px;color:#555;line-height:1.6;">
          <div><strong>模型:</strong> {{ rec.base_model }}</div>
          <div><strong>数据:</strong> {{ rec.train_data }}</div>
          <div><strong>目录:</strong> {{ rec.folder_name }}</div>
          <div v-if="rec.state" style="margin-top:6px;">
            <div style="display:flex;align-items:center;gap:8px;margin-bottom:4px;">
              <span style="font-size:12px;color:#999;">Epoch</span>
              <el-progress :percentage="getEpochProgress(rec)" :stroke-width="8" style="flex:1;" />
            </div>
            <div style="display:flex;align-items:center;gap:8px;">
              <span style="font-size:12px;color:#999;">Step</span>
              <el-progress :percentage="getStepProgress(rec)" :stroke-width="8" style="flex:1;" />
            </div>
          </div>
        </div>
        <div class="m-list-item-footer">
          <el-button size="small" type="primary" plain @click="showDetail(rec)">详情</el-button>
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
        <span style="font-size:15px;color:#999;">请前往 web 端启动训练</span>
      </div>
    </div>

    <!-- ====== 详情弹窗 ====== -->
    <div v-if="showDetailModal" class="m-modal-overlay" @click.self="closeDetailModal">
      <div class="m-modal-content" style="max-height:90vh;">
        <div class="m-modal-header">
          <span>训练详情</span>
          <span class="m-modal-close" @click="closeDetailModal">&times;</span>
        </div>

        <!-- 详情tab切换 -->
        <div style="display:flex;gap:0;margin-bottom:12px;background:#f5f6f8;border-radius:8px;overflow:hidden;">
          <div :class="['m-seg-control-item', { active: detailTab === 'info' }]" @click="detailTab = 'info'">信息</div>
          <div :class="['m-seg-control-item', { active: detailTab === 'loss' }]" @click="detailTab = 'loss'">损失</div>
          <div :class="['m-seg-control-item', { active: detailTab === 'logs' }]" @click="detailTab = 'logs'">日志</div>
        </div>

        <div v-if="detailTab === 'info'">
          <div style="font-size:13px;font-weight:500;margin-bottom:8px;">基本信息</div>
          <div style="font-size:13px;color:#555;line-height:1.8;">
            <div><strong>时间:</strong> {{ detail.time }}</div>
            <div><strong>模型:</strong> {{ detail.base_model }}</div>
            <div><strong>数据:</strong> {{ detail.train_data }}</div>
            <div><strong>状态:</strong> <span :class="['m-tag', detail.state?.status === 'completed' ? 'm-tag-success' : detail.state?.status === 'running' ? 'm-tag-warning' : 'm-tag-info']">{{ detail.state?.status || '未知' }}</span></div>
          </div>
          <div style="font-size:13px;font-weight:500;margin:12px 0 8px;">训练进度</div>
          <div style="margin-bottom:6px;">
            <span style="font-size:12px;color:#999;">Epoch</span>
            <el-progress :percentage="detailEpochPct" :stroke-width="8" />
          </div>
          <div style="margin-bottom:12px;">
            <span style="font-size:12px;color:#999;">Step</span>
            <el-progress :percentage="detailStepPct" :stroke-width="8" />
          </div>
          <div style="display:flex;gap:12px;font-size:12px;color:#666;">
            <span>Epoch: {{ detail.state?.current_epoch || 0 }}/{{ detail.params?.epoch_count || 1 }}</span>
            <span>loss: {{ detail.state?.sum_loss?.toFixed(3) || 0 }}</span>
          </div>
          <div style="font-size:13px;font-weight:500;margin:12px 0 8px;">训练参数</div>
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;font-size:12px;color:#555;background:#f8f9fb;border-radius:8px;padding:10px;">
            <div><strong>参数量:</strong> {{ detail.params?.model_size || '2.9B' }}</div>
            <div><strong>micro_bsz:</strong> {{ detail.params?.micro_bsz || 1 }}</div>
            <div><strong>epoch_save:</strong> {{ detail.params?.epoch_save || 1 }}</div>
            <div><strong>epoch_steps:</strong> {{ detail.params?.epoch_steps || 1000 }}</div>
            <div><strong>ctx_len:</strong> {{ detail.params?.ctx_len || 512 }}</div>
            <div><strong>epoch_count:</strong> {{ detail.params?.epoch_count || 1 }}</div>
            <div><strong>lr_init:</strong> {{ detail.params?.lr_init || '2e-5' }}</div>
            <div><strong>lr_final:</strong> {{ detail.params?.lr_final || '2e-5' }}</div>
          </div>
          <div style="font-size:13px;font-weight:500;margin:12px 0 8px;">LoRA 参数</div>
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;font-size:12px;color:#555;background:#f8f9fb;border-radius:8px;padding:10px;">
            <div><strong>r (rank):</strong> {{ detail.params?.lora_r || 32 }}</div>
            <div><strong>lora_alpha:</strong> {{ detail.params?.lora_alpha || 32 }}</div>
            <div><strong>lora_dropout:</strong> {{ detail.params?.lora_dropout || 0.01 }}</div>
          </div>
        </div>

        <div v-if="detailTab === 'loss'" class="m-empty" style="padding:40px 20px;">
          <div class="m-empty-icon">📈</div>
          <span style="font-size:14px;color:#999;">请前往 web 端查看损失曲线</span>
        </div>

        <div v-if="detailTab === 'logs'" class="m-empty" style="padding:40px 20px;">
          <div class="m-empty-icon">📝</div>
          <span style="font-size:14px;color:#999;">请前往 web 端查看训练日志</span>
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
        <p style="font-size:14px;color:#555;">确定要停止训练吗？停止后训练将被中断。</p>
        <div style="display:flex;gap:10px;margin-top:12px;">
          <el-button size="small" style="flex:1;" @click="showStopConfirm = false">取消</el-button>
          <el-button size="small" type="danger" style="flex:1;" @click="handleStop">确定停止</el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import axios from 'axios'

// ==== Tab 切换 ====
const activeTab = ref('record')

// ==== 训练记录 ====
const trainRecords = ref([])
const currentPage = ref(1)
const pageSize = ref(10)
const totalPages = computed(() => Math.max(1, Math.ceil(trainRecords.value.length / pageSize.value)))
const paginatedRecords = computed(() => {
  const s = (currentPage.value - 1) * pageSize.value
  return trainRecords.value.slice(s, s + pageSize.value)
})

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
  try {
    const res = await axios.get('/api/train/records')
    trainRecords.value = res.data
  } catch { console.error('获取训练记录失败') }
}

// ==== 详情 ====
const showDetailModal = ref(false)
const detail = ref({})
const detailTab = ref('info')
const detailFolderName = ref('')
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
  // 先打开弹窗，用户立刻看到界面，不卡顿
  detail.value = { ...row }
  showDetailModal.value = true
  // 再异步拉详情数据，到了会自动刷新
  try {
    const res = await axios.get(`/api/train/records/${row.folder_name}`)
    detail.value = { ...row, params: res.data.params, state: res.data.state }
  } catch { ElMessage.error('获取详情失败') }
}

const closeDetailModal = () => {
  showDetailModal.value = false
}

onMounted(loadTrainRecords)
</script>

<style scoped>
.m-train-page {
  padding-bottom: 8px;
}
.m-seg-control-item {
  flex: 1;
  text-align: center;
  padding: 10px 0;
  font-size: 13px;
  font-weight: 500;
  color: #666;
  cursor: pointer;
  transition: all 0.2s;
  user-select: none;
}
.m-seg-control-item.active {
  background: #409eff;
  color: #fff;
}
.m-seg-control-item:active {
  opacity: 0.7;
}
</style>