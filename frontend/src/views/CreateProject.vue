<template>
  <div class="create-project">
    <van-nav-bar title="新建房源视频" />

    <van-form @submit="onSubmit">
      <!-- 1. 基础信息 -->
      <van-cell-group inset title="基础信息 (必填)">
        <van-field
          v-model="formData.communityName"
          name="communityName"
          label="小区名称"
          placeholder="请输入小区名 (如: 阳光花园)"
          :rules="[{ required: true, message: '请填写小区名称' }]"
        />
        
        <van-field name="layout" label="户型结构">
          <template #input>
            <div class="layout-steppers">
              <van-stepper v-model="formData.layout.room" min="1" max="9" button-size="22" /> 室
              <van-stepper v-model="formData.layout.hall" min="0" max="5" button-size="22" /> 厅
              <van-stepper v-model="formData.layout.restroom" min="0" max="5" button-size="22" /> 卫
            </div>
          </template>
        </van-field>

        <van-field
          v-model="formData.area"
          name="area"
          label="建筑面积"
          type="number"
          placeholder="请输入数字"
          :rules="[{ required: true, message: '请填写面积' }]"
        >
          <template #right-icon>㎡</template>
        </van-field>

        <van-field
          v-model="formData.price"
          name="price"
          label="挂牌价格"
          type="number"
          placeholder="请输入数字"
          :rules="[{ required: true, message: '请填写价格' }]"
        >
          <template #right-icon>万</template>
        </van-field>
      </van-cell-group>

      <!-- 2. 核心卖点 -->
      <van-cell-group inset title="核心卖点 (选填 - 帮助 AI 写文案)">
        <van-field name="sellingPoints">
          <template #input>
            <van-checkbox-group v-model="formData.sellingPoints" direction="horizontal">
              <van-checkbox name="学区房" shape="square">学区房</van-checkbox>
              <van-checkbox name="地铁沿线" shape="square">地铁沿线</van-checkbox>
              <van-checkbox name="南北通透" shape="square">南北通透</van-checkbox>
              <van-checkbox name="急售" shape="square">急售</van-checkbox>
              <van-checkbox name="全新装修" shape="square">全新装修</van-checkbox>
              <van-checkbox name="满五唯一" shape="square">满五唯一</van-checkbox>
            </van-checkbox-group>
          </template>
        </van-field>
        <van-field
          v-model="formData.remarks"
          rows="2"
          autosize
          label="其他补充"
          type="textarea"
          placeholder="如：房东出国，看房方便..."
        />
      </van-cell-group>

      <!-- 3. 素材上传 -->
      <van-cell-group inset title="素材上传">
        <div class="upload-container">
          <van-uploader
            v-model="fileList"
            multiple
            accept="video/*"
            :max-size="500 * 1024 * 1024"
            @oversize="onOversize"
          >
            <div class="upload-placeholder">
              <van-icon name="plus" size="24" />
              <div class="text">点击上传视频片段</div>
              <div class="sub-text">建议 3-5 段竖屏视频</div>
            </div>
          </van-uploader>
        </div>
      </van-cell-group>

      <div style="margin: 12px;">
        <van-button round block type="primary" native-type="submit" :loading="isSubmitting" loading-text="正在处理...">
          开始制作
        </van-button>
      </div>
    </van-form>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useProjectStore, type ProjectInfo, type Asset } from '../stores/project'
import { projectApi } from '../api/project'
import { showToast } from 'vant'

const router = useRouter()
const projectStore = useProjectStore()

const formData = reactive<ProjectInfo>({
  communityName: '',
  layout: { room: 2, hall: 1, restroom: 1 },
  area: undefined,
  price: undefined,
  sellingPoints: [],
  remarks: ''
})

const fileList = ref<any[]>([])
const isSubmitting = ref(false)

const onOversize = () => {
  showToast('文件大小不能超过 500MB')
}

const onSubmit = async () => {
  if (fileList.value.length === 0) {
    showToast('请至少上传一个视频片段')
    return
  }

  isSubmitting.value = true

  try {
    // 1. 创建项目
    const createRes = await projectApi.create({
      userId: 1, // Mock user ID or from auth store
      title: `${formData.communityName} ${formData.layout.room}室${formData.layout.hall}厅`,
      houseInfo: {
        community: formData.communityName,
        room: formData.layout.room,
        hall: formData.layout.hall,
        price: formData.price || 0,
        area: formData.area,
        sellingPoints: formData.sellingPoints,
        remarks: formData.remarks
      }
    })
    
    const projectId = createRes.data.id
    console.log('Project created:', projectId)

    // 2. 并发上传文件
    const uploadPromises = fileList.value.map(fileItem => {
      return projectApi.uploadAsset(projectId, fileItem.file)
    })

    await Promise.all(uploadPromises)
    showToast('项目创建成功，开始智能分析...')
    
    // 3. 跳转到确认页
    router.push(`/review/${projectId}`)

  } catch (error) {
    console.error(error)
    showToast('提交失败，请重试')
  } finally {
    isSubmitting.value = false
  }
}
</script>

<style scoped>
.create-project {
  padding-bottom: 12px;
}

.layout-steppers {
  display: flex;
  align-items: center;
  gap: 8px;
}

.upload-container {
  padding: 12px;
  display: flex;
  justify-content: center;
}

.upload-placeholder {
  width: 100%;
  height: 120px;
  background-color: #f7f8fa;
  border: 1px dashed #dcdee0;
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #969799;
}

.upload-placeholder .text {
  margin-top: 8px;
  font-size: 14px;
}

.upload-placeholder .sub-text {
  margin-top: 4px;
  font-size: 12px;
  color: #c8c9cc;
}

:deep(.van-checkbox) {
  margin-bottom: 8px;
  margin-right: 8px;
}
</style>
