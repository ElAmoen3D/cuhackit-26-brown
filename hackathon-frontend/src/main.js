import { createApp } from 'vue'
import { createAuth0 } from '@auth0/auth0-vue';
import App from './App.vue' // <-- The .vue extension here is MANDATORY
import router from './router' // (If you are using vue-router)

const app = createApp(App)

app.use(
  createAuth0({
    domain: import.meta.env.VITE_AUTH0_DOMAIN,
    clientId: import.meta.env.VITE_AUTH0_CLIENT_ID,
    authorizationParams: {
      redirect_uri: import.meta.env.VITE_AUTH0_REDIRECT_URI
    }
  })
);

app.use(router)
app.mount('#app')