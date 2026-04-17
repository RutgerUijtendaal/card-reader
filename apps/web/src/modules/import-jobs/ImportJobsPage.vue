<template>
  <section class="page-card">
    <h2>Import Jobs</h2>
    <form @submit.prevent="createJob">
      <label>
        Source directory
        <input v-model="sourcePath" required placeholder="/home/user/cards" />
      </label>
      <label>
        Template
        <input v-model="templateId" required placeholder="mtg-like-v1" />
      </label>
      <button type="submit">Create import</button>
    </form>
    <ul>
      <li v-for="job in jobs" :key="job.id">
        {{ job.id }} - {{ job.status }} ({{ job.processed_items }}/{{ job.total_items }})
      </li>
    </ul>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { api } from '@/api/client';

type ImportJob = {
  id: string;
  status: string;
  total_items: number;
  processed_items: number;
};

const sourcePath = ref('');
const templateId = ref('mtg-like-v1');
const jobs = ref<ImportJob[]>([]);

const loadJobs = async (): Promise<void> => {
  const response = await api.get<ImportJob[]>('/imports');
  jobs.value = response.data;
};

const createJob = async (): Promise<void> => {
  await api.post('/imports', { source_path: sourcePath.value, template_id: templateId.value, options: {} });
  await loadJobs();
};

onMounted(loadJobs);
</script>
