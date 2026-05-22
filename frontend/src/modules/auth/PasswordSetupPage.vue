<template>
  <section class="mx-auto flex min-h-full max-w-md items-center">
    <form
      class="page-card w-full space-y-5"
      @submit.prevent="submit"
    >
      <div>
        <h2 class="theme-section-title text-xl font-semibold">
          Set password
        </h2>
        <p class="theme-section-muted mt-2 text-sm">
          <template v-if="username">
            Create a password for {{ username }}.
          </template>
          <template v-else>
            Use this one-time link to create your password.
          </template>
        </p>
      </div>

      <p
        v-if="statusMessage"
        class="theme-section-muted text-sm"
      >
        {{ statusMessage }}
      </p>

      <p
        v-if="errorMessage"
        class="theme-error-text text-sm font-medium"
      >
        {{ errorMessage }}
      </p>

      <template v-if="linkValid">
        <label class="field-label">
          Password
          <input
            v-model="password"
            class="input-base"
            autocomplete="new-password"
            type="password"
          >
        </label>

        <label class="field-label">
          Confirm password
          <input
            v-model="passwordConfirm"
            class="input-base"
            autocomplete="new-password"
            type="password"
          >
        </label>

        <button
          class="btn-primary w-full"
          :disabled="submitting"
          type="submit"
        >
          {{ submitting ? 'Saving password' : 'Set password' }}
        </button>
      </template>

      <RouterLink
        v-else
        class="theme-link inline-flex text-sm font-semibold"
        to="/login"
      >
        Back to sign in
      </RouterLink>
    </form>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { toast } from 'vue-sonner';
import { submitPasswordSetup, validatePasswordSetupLink } from './api';

const route = useRoute();
const router = useRouter();

const uid = ref('');
const token = ref('');
const username = ref('');
const password = ref('');
const passwordConfirm = ref('');
const linkValid = ref(false);
const submitting = ref(false);
const statusMessage = ref('Validating link...');
const errorMessage = ref('');

const load = async (): Promise<void> => {
  uid.value = typeof route.query.uid === 'string' ? route.query.uid : '';
  token.value = typeof route.query.token === 'string' ? route.query.token : '';

  if (!uid.value || !token.value) {
    linkValid.value = false;
    statusMessage.value = '';
    errorMessage.value = 'This password setup link is incomplete.';
    return;
  }

  try {
    const response = await validatePasswordSetupLink(uid.value, token.value);
    linkValid.value = response.valid;
    username.value = response.username ?? '';
    statusMessage.value = response.valid ? '' : response.detail ?? '';
    errorMessage.value = response.valid ? '' : response.detail ?? 'This password setup link is invalid.';
  } catch (error) {
    linkValid.value = false;
    statusMessage.value = '';
    errorMessage.value = extractErrorMessage(error, 'This password setup link is invalid or expired.');
  }
};

const submit = async (): Promise<void> => {
  errorMessage.value = '';
  if (password.value !== passwordConfirm.value) {
    errorMessage.value = 'Passwords do not match.';
    return;
  }
  submitting.value = true;
  try {
    await submitPasswordSetup({
      uid: uid.value,
      token: token.value,
      password: password.value,
    });
    toast.success('Password set. You can sign in now.');
    await router.replace('/login');
  } catch (error) {
    errorMessage.value = extractErrorMessage(error, 'Unable to set password.');
  } finally {
    submitting.value = false;
  }
};

onMounted(() => {
  void load();
});

const extractErrorMessage = (error: unknown, fallback: string): string => {
  if (typeof error === 'object' && error && 'response' in error) {
    const detail = (error as { response?: { data?: { detail?: unknown } } }).response?.data?.detail;
    if (typeof detail === 'string' && detail.length > 0) {
      return detail;
    }
  }
  return fallback;
};
</script>
