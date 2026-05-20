import { createApp } from 'vue';
import { createPinia } from 'pinia';
import { VueQueryPlugin } from '@tanstack/vue-query';
import App from './App.vue';
import { router } from './router';
import { initTheme } from './composables/useTheme';
import './styles.css';
import 'vue-sonner/style.css';

initTheme();

const app = createApp(App);
app.use(createPinia());
app.use(router);
app.use(VueQueryPlugin);
app.mount('#app');
