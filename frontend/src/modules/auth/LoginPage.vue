<template>
  <section class="mx-auto flex min-h-full max-w-md items-center">
    <form
      class="page-card w-full space-y-5"
      @submit.prevent="submit"
    >
      <div>
        <h2 class="text-xl font-semibold text-slate-900">
          Sign in
        </h2>
      </div>

      <label class="field-label">
        Username
        <input
          v-model="username"
          class="input-base"
          autocomplete="username"
          autofocus
          type="text"
        >
      </label>

      <label class="field-label">
        Password
        <input
          v-model="password"
          class="input-base"
          autocomplete="current-password"
          type="password"
        >
      </label>

      <p
        v-if="errorMessage"
        class="text-sm font-medium text-rose-700"
      >
        {{ errorMessage }}
      </p>

      <button
        class="btn-primary w-full gap-2"
        :disabled="auth.loading"
        type="submit"
      >
        <LogIn class="h-4 w-4" />
        <span>{{ auth.loading ? 'Signing in' : 'Sign in' }}</span>
      </button>
    </form>
  </section>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { LogIn } from 'lucide-vue-next';
import { useAuthStore } from './authStore';

const auth = useAuthStore();
const route = useRoute();
const router = useRouter();

const username = ref('');
const password = ref('');
const errorMessage = ref('');

const submit = async (): Promise<void> => {
  errorMessage.value = '';
  try {
    await auth.login({ username: username.value, password: password.value });
    const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : '/cards';
    await router.replace(redirect);
  } catch {
    errorMessage.value = 'Invalid username or password.';
  }
};
</script>
