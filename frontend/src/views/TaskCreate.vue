<template>
  <div class="task-create">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>创建新任务</span>
          <el-button @click="$router.push('/tasks')">返回任务列表</el-button>
        </div>
      </template>
      
      <el-form :model="form" :rules="rules" ref="formRef" label-width="120px">
        <el-form-item label="任务名称" prop="name">
          <el-input v-model="form.name" placeholder="请输入任务名称" />
        </el-form-item>
        
        <el-form-item label="任务描述" prop="description">
          <el-input v-model="form.description" type="textarea" placeholder="请输入任务描述" />
        </el-form-item>
        
        <el-form-item label="数据源" prop="data_source_id">
          <el-select v-model="form.data_source_id" placeholder="请选择数据源">
            <el-option
              v-for="source in dataSources"
              :key="source.id"
              :label="`${source.name} (${source.type})`"
              :value="source.id"
            />
          </el-select>
        </el-form-item>
        
        <el-form-item label="执行类型" prop="execution_type">
          <el-select v-model="form.execution_type" @change="onExecutionTypeChange">
            <el-option label="SQL查询" value="sql" />
            <el-option label="自定义脚本" value="script" />
          </el-select>
        </el-form-item>
        
        <el-form-item v-if="form.execution_type === 'sql'" label="SQL内容" prop="sql_content">
          <el-input v-model="form.sql_content" type="textarea" :rows="6" placeholder="请输入SQL查询语句" />
        </el-form-item>
        
        <template v-if="form.execution_type === 'script'">
          <el-form-item label="脚本路径" prop="script_path">
            <el-input v-model="form.script_path" placeholder="例如: scripts/my_script.py" />
          </el-form-item>
          <el-form-item label="函数名" prop="script_function">
            <el-input v-model="form.script_function" placeholder="例如: export_data" />
          </el-form-item>
        </template>
        
        <el-form-item label="导出方式" prop="export_methods">
          <el-checkbox-group v-model="form.export_methods">
            <el-checkbox label="local">本地文件</el-checkbox>
            <el-checkbox label="email">邮件发送</el-checkbox>
            <el-checkbox label="dingtalk">钉钉通知</el-checkbox>
          </el-checkbox-group>
        </el-form-item>
        
        <template v-if="form.export_methods.includes('dingtalk')">
          <el-form-item label="钉钉Webhook" prop="dingtalk_webhook">
            <el-input v-model="form.dingtalk_webhook" placeholder="钉钉机器人Webhook地址（可选，留空使用全局配置）" />
          </el-form-item>
          <el-form-item label="钉钉Secret" prop="dingtalk_secret">
            <el-input v-model="form.dingtalk_secret" placeholder="钉钉机器人签名密钥（可选）" />
          </el-form-item>
          <el-form-item label="钉钉消息模板" prop="dingtalk_message_template">
            <el-input v-model="form.dingtalk_message_template" type="textarea" :rows="3" placeholder="自定义钉钉消息模板（可选，留空使用默认模板）" />
          </el-form-item>
        </template>
        
        <el-form-item label="导出文件名">
          <el-input v-model="form.export_filename" placeholder="支持变量: {date}, {time}, {task_name}" />
        </el-form-item>
        
        <el-form-item label="Cron表达式">
          <el-input v-model="form.cron_expression" placeholder="例如: 0 9 * * * (每天9点执行)" />
        </el-form-item>
        
        <el-form-item label="邮件接收人">
          <el-input v-model="form.email_recipients" placeholder="多个邮箱用逗号分隔" />
        </el-form-item>
        
        <el-form-item label="任务状态" prop="status">
          <el-select v-model="form.status">
            <el-option label="启用" value="active" />
            <el-option label="禁用" value="inactive" />
          </el-select>
        </el-form-item>
        
        <el-form-item>
          <el-button type="primary" @click="submitForm" :loading="submitting">
            创建任务
          </el-button>
          <el-button @click="$router.push('/tasks')">取消</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import api from '../utils/api'

const router = useRouter()
const formRef = ref()
const submitting = ref(false)
const dataSources = ref([])

const form = reactive({
  name: '',
  description: '',
  data_source_id: '',
  execution_type: 'sql',
  sql_content: '',
  script_path: '',
  script_function: '',
  export_methods: ['local'],
  export_filename: '',
  cron_expression: '',
  email_recipients: '',
  email_subject: '',
  email_body: '',
  dingtalk_webhook: '',
  dingtalk_secret: '',
  dingtalk_message_template: '',
  status: 'active'
})

const rules = {
  name: [{ required: true, message: '请输入任务名称', trigger: 'blur' }],
  data_source_id: [{ required: true, message: '请选择数据源', trigger: 'change' }],
  execution_type: [{ required: true, message: '请选择执行类型', trigger: 'change' }],
  sql_content: [{ required: true, message: '请输入SQL内容', trigger: 'blur' }],
  script_path: [{ required: true, message: '请输入脚本路径', trigger: 'blur' }],
  script_function: [{ required: true, message: '请输入函数名', trigger: 'blur' }],
  export_methods: [{ required: true, message: '请选择导出方式', trigger: 'change' }],
  status: [{ required: true, message: '请选择任务状态', trigger: 'change' }]
}

const onExecutionTypeChange = () => {
  if (form.execution_type === 'sql') {
    form.script_path = ''
    form.script_function = ''
  } else {
    form.sql_content = ''
  }
}

const fetchDataSources = async () => {
  try {
    const response = await api.get('/api/data-sources')
    if (response.data.success) {
      dataSources.value = response.data.data.data_sources
    }
  } catch (error) {
    console.error('获取数据源失败:', error)
    ElMessage.error('获取数据源失败')
  }
}

const submitForm = async () => {
  if (!formRef.value) return
  
  try {
    await formRef.value.validate()
    submitting.value = true
    
    const response = await api.post('/api/tasks', form)
    if (response.data.success) {
      ElMessage.success('任务创建成功')
      router.push('/tasks')
    }
  } catch (error) {
    console.error('创建任务失败:', error)
  } finally {
    submitting.value = false
  }
}

onMounted(() => {
  fetchDataSources()
})
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>