<template>
  <div class="grid h-screen grid-cols-1 overflow-hidden lg:grid-cols-[260px_1fr]">
    <aside class="h-full overflow-y-auto bg-slate-900 px-6 py-7 text-slate-50">
      <h1 class="mb-4 text-2xl font-semibold">
        Card Reader
      </h1>
      <nav class="grid gap-2">
        <RouterLink
          class="nav-link"
          to="/cards"
        >
          <Images class="h-4 w-4" />
          <span>Card Gallery</span>
        </RouterLink>

        <RouterLink
          class="nav-link"
          to="/import-jobs"
        >
          <Upload class="h-4 w-4" />
          <span>Import Jobs</span>
        </RouterLink>

        <RouterLink
          class="nav-link"
          to="/review"
        >
          <ClipboardCheck class="h-4 w-4" />
          <span>Review Queue</span>
        </RouterLink>

        <RouterLink
          class="nav-link"
          to="/settings"
        >
          <Settings class="h-4 w-4" />
          <span>Settings</span>
        </RouterLink>
      </nav>
    </aside>

    <main class="h-full overflow-y-auto p-4 sm:p-6">
      <RouterView />
    </main>
  </div>
  <Toaster
    rich-colors
    position="top-right"
  />
</template>

<script setup lang="ts">
import { ClipboardCheck, Images, Settings, Upload } from 'lucide-vue-next';
import { Toaster } from 'vue-sonner';
</script>
