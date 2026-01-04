<template>
  <div class="create-project">
    <van-nav-bar title="发布房源视频" />

    <van-form @submit="onSubmit">
      <!-- 1. 基础信息 -->
      <div class="section-title">1. 基础信息</div>
      <van-cell-group class="form-card app-card">
        <van-field
          v-model="formData.communityName"
          name="communityName"
          label="小区名称"
          placeholder="例如: 阳光花园"
          :rules="[{ required: true, message: '请填写小区名称' }]"
        />
        
        <van-field name="layout" label="户型结构">
          <template #input>
            <div class="layout-inputs">
              <div class="input-item">
                <input 
                  type="number" 
                  v-model="formData.layout.room" 
                  class="mini-input"
                  placeholder="2"
                />
                <span class="unit">室</span>
              </div>
              <div class="input-item">
                <input 
                  type="number" 
                  v-model="formData.layout.hall" 
                  class="mini-input"
                  placeholder="1"
                />
                <span class="unit">厅</span>
              </div>
              <div class="input-item">
                <input 
                  type="number" 
                  v-model="formData.layout.restroom" 
                  class="mini-input"
                  placeholder="1"
                />
                <span class="unit">卫</span>
              </div>
            </div>
          </template>
        </van-field>

        <van-field
          v-model="formData.area"
          name="area"
          label="建筑面积"
          type="number"
          placeholder="0"
          :rules="[{ required: true, message: '请填写面积' }]"
        >
          <template #right-icon>㎡</template>
        </van-field>

        <van-field
          v-model="formData.price"
          name="price"
          label="挂牌价格"
          type="number"
          placeholder="0"
          :rules="[{ required: true, message: '请填写价格' }]"
        >
          <template #right-icon>万</template>
        </van-field>
      </van-cell-group>

      <!-- 2. 核心卖点 -->
      <div class="section-title">
        2. 核心卖点 <span class="sub-title">(帮助 AI 生成专业文案)</span>
      </div>
      <van-cell-group class="form-card app-card">
        <div class="selling-points-container">
          <div 
            v-for="item in sellingPointOptions" 
            :key="item"
            class="tag-item"
            :class="{ active: formData.sellingPoints.includes(item) }"
            @click="toggleSellingPoint(item)"
          >
            {{ item }}
          </div>
        </div>
        <van-field
          v-model="formData.remarks"
          rows="2"
          autosize
          label="补充说明"
          type="textarea"
          placeholder="例如: 房东急售，看房方便..."
          class="remark-field"
        />
      </van-cell-group>

      <!-- 3. 素材上传 -->
      <div class="section-title">
        3. 素材上传 <span class="sub-title">(建议 3-5 段竖屏视频)</span>
      </div>
      <van-cell-group class="form-card upload-card app-card">
        <div class="upload-grid">
          <div v-for="(item, index) in fileList" :key="index" class="preview-item">
            <video 
              :src="item.objectUrl || getObjectURL(item.file)" 
              class="video-thumb" 
              muted 
              preload="metadata"
              playsinline
            ></video>
            <div class="delete-mask" @click.stop="removeFile(index)">
              <van-icon name="cross" size="12" />
            </div>
          </div>
          
          <van-uploader
            v-model="fileList"
            multiple
            accept="video/*"
            :max-size="500 * 1024 * 1024"
            @oversize="onOversize"
            :preview-image="false"
            :after-read="afterRead"
          >
            <div class="upload-placeholder">
              <div class="icon-wrapper">
                <van-icon name="plus" size="24" color="#fff" />
              </div>
              <div class="text">点击上传视频</div>
              <div class="sub-text">支持批量上传</div>
            </div>
          </van-uploader>
        </div>
      </van-cell-group>

      <div class="submit-bar">
        <van-button 
           
          block 
          type="primary" 
          native-type="submit" 
          :loading="isSubmitting" 
          loading-text="正在智能分析画面..."
          color="linear-gradient(to right, #1989fa, #39b9f5)"
        >
          一键生成视频
        </van-button>
      </div>
    </van-form>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { type ProjectInfo } from '../stores/project'
import { projectApi } from '../api/project'
import { showToast } from 'vant'

const router = useRouter()

const sellingPointOptions = ['学区房', '地铁沿线', '南北通透', '急售', '全新装修', '满五唯一', '视野开阔', '带车位']

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

const toggleSellingPoint = (item: string) => {
  const index = formData.sellingPoints.indexOf(item)
  if (index > -1) {
    formData.sellingPoints.splice(index, 1)
  } else {
    formData.sellingPoints.push(item)
  }
}

const onOversize = () => {
  showToast('文件大小不能超过 500MB')
}

const getObjectURL = (file: File) => {
  if (!file) return ''
  return URL.createObjectURL(file)
}

const removeFile = (index: number) => {
  fileList.value.splice(index, 1)
}

const afterRead = (file: any) => {
  const files = Array.isArray(file) ? file : [file]
  files.forEach((f: any) => {
    if (f.file) {
      f.objectUrl = URL.createObjectURL(f.file)
    }
  })
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

    // 2. 上传文件 (FormData 模式，上传到后端本地)
    const uploadPromises = fileList.value.map(async (fileItem) => {
      try {
        fileItem.status = 'uploading'
        fileItem.message = '0%'

        // 使用 FormData 直接上传 (强制使用 Local Upload 接口)
        await projectApi.uploadAssetLocal(projectId, fileItem.file)

        fileItem.status = 'done'
        fileItem.message = '完成'
      } catch (err) {
        console.error('Upload failed for file:', fileItem.file.name, err)
        fileItem.status = 'failed'
        fileItem.message = '失败'
        throw err
      }
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
  padding-bottom: 40px;
  background-color: #f7f8fa;
  min-height: 100vh;
}

.section-title {
  padding: 16px 16px 8px;
  font-size: 15px;
  font-weight: 600;
  color: #323233;
}

.sub-title {
  font-size: 12px;
  font-weight: normal;
  color: #969799;
  margin-left: 4px;
}

.form-card {
  margin: 0 0;
  border-radius: var(--app-card-radius);
  overflow: hidden;
}

.layout-inputs {
  display: flex;
  align-items: center;
  gap: 12px;
}

.input-item {
  display: flex;
  align-items: center;
  gap: 4px;
}

.mini-input {
  width: 40px;
  height: 30px;
  border: 1px solid #dcdee0;
  border-radius: 4px;
  text-align: center;
  font-size: 14px;
  color: #323233;
  padding: 0;
  background-color: #f7f8fa;
}

.mini-input:focus {
  border-color: #1989fa;
  background-color: #fff;
  outline: none;
}

.input-item .unit {
  font-size: 14px;
  color: #323233;
}

.selling-points-container {
  padding: 16px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.tag-item {
  padding: 6px 12px;
  background-color: #f5f6f7;
  border-radius: 4px;
  font-size: 13px;
  color: #646566;
  transition: all 0.2s;
  border: 1px solid transparent;
  cursor: pointer;
}

.tag-item.active {
  background-color: #e8f3ff;
  color: #1989fa;
  border-color: #1989fa;
  font-weight: 500;
}

.upload-card {
  padding: 20px 0;
}

.upload-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding: 0 16px;
}

.preview-item {
  position: relative;
  width: 100px;
  height: 100px;
  border-radius: 8px;
  overflow: hidden;
  background-color: #000;
}

.video-thumb {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.delete-mask {
  position: absolute;
  top: 0;
  right: 0;
  width: 20px;
  height: 20px;
  background: rgba(0,0,0,0.5);
  border-bottom-left-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  cursor: pointer;
  z-index: 1;
}

.upload-placeholder {
  width: 100px;
  height: 100px;
  background-color: #f7f8fa;
  border: 1px dashed #dcdee0;
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.icon-wrapper {
  width: 32px;
  height: 32px;
  background: #1989fa;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 8px;
}

.upload-placeholder .text {
  font-size: 12px;
  color: #323233;
  font-weight: 500;
}

.upload-placeholder .sub-text {
  font-size: 10px;
  color: #969799;
  margin-top: 2px;
}

.submit-bar {
  margin: 32px 16px;
}

:deep(.van-field__label) {
  color: #646566;
}
</style>
