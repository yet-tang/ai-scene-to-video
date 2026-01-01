# AI Scene to Video - Frontend

基于 Vue 3 + TypeScript + Vant UI 的房产视频生成工具前端项目。

## 功能模块
1.  **新建项目**: 填写房源信息，上传视频素材。
2.  **智能分段确认**: 拖拽调整视频顺序，修改 AI 识别的场景标签，预览解说词。
3.  **视频生成**: 模拟生成最终视频并提供下载/分享。

## 技术栈
- Vue 3
- TypeScript
- Vite
- Vant UI (Mobile Component Library)
- Pinia (State Management)
- Vue Router
- Vuedraggable (Drag & Drop)

## 开发运行
```bash
# 安装依赖
npm install

# 启动开发服务器
npm run dev

# 构建生产环境
npm run build
```

## Mock 说明
当前版本尚未对接后端 API，所有数据流转（上传、分析、生成）均为前端模拟（Mock），数据存储在 Pinia 内存中，刷新页面会重置。
