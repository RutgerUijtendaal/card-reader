<template>
  <div class="app-shell">
    <aside>
      <h1>Card Reader</h1>
      <nav>
        <RouterLink to="/import-jobs">Import Jobs</RouterLink>
        <RouterLink to="/cards">Card Search</RouterLink>
        <RouterLink to="/review">Review Queue</RouterLink>
      </nav>
    </aside>
    <main>
      <RouterView />
    </main>
  </div>
</template>

<script setup lang="ts"></script>