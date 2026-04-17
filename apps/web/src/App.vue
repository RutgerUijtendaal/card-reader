<template>
  <div class="grid min-h-screen grid-cols-1 lg:grid-cols-[260px_1fr]">
    <aside class="bg-slate-900 px-6 py-7 text-slate-50">
      <h1 class="mb-4 text-2xl font-semibold">Card Reader</h1>
      <nav class="grid gap-2">
        <RouterLink class="nav-link" to="/import-jobs">Import Jobs</RouterLink>
        <RouterLink class="nav-link" to="/cards">Card Search</RouterLink>
        <RouterLink class="nav-link" to="/review">Review Queue</RouterLink>
      </nav>
    </aside>

    <main class="p-4 sm:p-6">
      <RouterView />
    </main>
  </div>
</template>

<script setup lang="ts"></script>