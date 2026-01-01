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

  // 模拟上传和 AI 分析过程
  setTimeout(() => {
    // 1. 保存基础信息
    projectStore.setProjectInfo({ ...formData })
    projectStore.currentProject.id = Date.now().toString()

    // 2. 处理上传的文件 (Mock Assets)
    const newAssets: Asset[] = fileList.value.map((fileItem, index) => {
      // 模拟 AI 识别结果
      const mockScenes = ['小区大门', '客厅', '卧室', '厨房', '卫生间', '阳台']
      const randomScene = mockScenes[index % mockScenes.length] || '其他'
      
      return {
        id: `asset-${Date.now()}-${index}`,
        file: fileItem.file,
        url: fileItem.objectUrl || URL.createObjectURL(fileItem.file),
        sceneLabel: randomScene,
        userLabel: randomScene, // 初始默认一致
        duration: 10 + Math.random() * 10, // 模拟时长
        sortOrder: index,
        thumbnail: '' // 实际项目中需要生成缩略图，这里暂略或用视频第一帧逻辑(复杂)
      }
    })

    // 3. 智能排序 (Mock: 外景 -> 客厅 -> 厨房/卫 -> 卧室)
    // 简单模拟排序权重
    const scenePriority: Record<string, number> = {
      '小区大门': 1,
      '客厅': 2,
      '厨房': 3,
      '卫生间': 4,
      '卧室': 5,
      '阳台': 6
    }
    
    newAssets.sort((a, b) => {
      const pA = scenePriority[a.sceneLabel] || 99
      const pB = scenePriority[b.sceneLabel] || 99
      return pA - pB
    })
    
    // 更新 sortOrder
    newAssets.forEach((asset, idx) => asset.sortOrder = idx)

    projectStore.setTimeline(newAssets)
    projectStore.currentProject.status = 'review'

    // 生成模拟脚本
    const script = `哈喽大家好，今天带大家看一套${formData.communityName}的房子。
这套房子是${formData.layout.room}室${formData.layout.hall}厅，面积${formData.area}平米。
进门就是${newAssets.find(a => a.sceneLabel === '客厅')?.userLabel || '宽敞的客厅'}，采光非常好。
${formData.sellingPoints.length > 0 ? '核心卖点是' + formData.sellingPoints.join('，') + '。' : ''}
总价只要${formData.price}万，性价比超高，喜欢的赶紧联系我吧！`
    
    projectStore.currentProject.script = script

    isSubmitting.value = false
    // 跳转到确认页
    router.push(`/review/${projectStore.currentProject.id}`)
  }, 2000)
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
