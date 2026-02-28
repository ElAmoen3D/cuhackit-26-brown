import { createApp } from 'vue'
import App from './App.vue' // <-- The .vue extension here is MANDATORY
import router from './router' // (If you are using vue-router)

const app = createApp(App)

app.use(router)
app.mount('#app')