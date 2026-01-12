import { createApp } from 'vue'
import { createPinia } from 'pinia'
import Vant from 'vant'
import 'vant/lib/index.css'
import router from './router'
import './style.css'
import App from './App.vue'

// Print version info
const imageTag = import.meta.env.VITE_IMAGE_TAG || 'unknown'
const gitCommit = import.meta.env.VITE_GIT_COMMIT || 'unknown'
const buildTime = import.meta.env.VITE_BUILD_TIME || 'unknown'
console.log('%c🚀 Frontend Version Info', 'color: #42b983; font-weight: bold; font-size: 14px;')
console.log(`%cImage Tag: ${imageTag}`, 'color: #35495e;')
console.log(`%cGit Commit: ${gitCommit}`, 'color: #35495e;')
console.log(`%cBuild Time: ${buildTime}`, 'color: #35495e;')
console.log(`%cAPI Base URL: ${import.meta.env.VITE_API_BASE_URL || 'not set'}`, 'color: #35495e;')

const app = createApp(App)

app.use(createPinia())
app.use(router)
app.use(Vant)

app.mount('#app')
