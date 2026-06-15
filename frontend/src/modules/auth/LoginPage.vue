<template>
  <section class="mx-auto flex min-h-full max-w-md items-center">
    <div class="page-card w-full space-y-6">
      <form
        class="space-y-5"
        @submit.prevent="submit"
      >
        <div>
          <h2 class="theme-section-title text-xl font-semibold">
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
          class="theme-error-text text-sm font-medium"
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

      <form
        class="theme-divider border-t pt-5"
        @submit.prevent="submitRequest"
      >
        <div class="space-y-4">
          <Transition name="access-request-expand">
            <div
              v-if="accessRequestExpanded"
              class="space-y-4 overflow-hidden"
            >
              <div>
                <h3 class="theme-section-title text-sm font-semibold">
                  Request access
                </h3>
                <p class="theme-section-muted mt-1 text-xs">
                  Send a contact handle so we know how to reach you.
                </p>
              </div>

              <label class="field-label">
                Contact handle
                <input
                  v-model="contactHandle"
                  class="input-base"
                  autocomplete="email"
                  placeholder="Email, Discord, or other handle"
                  type="text"
                >
              </label>

              <label class="field-label">
                Note
                <textarea
                  v-model="accessMessage"
                  class="input-base min-h-20 resize-y"
                  placeholder="Optional"
                />
              </label>
            </div>
          </Transition>

          <p
            v-if="requestSuccessMessage"
            class="theme-success-text text-sm font-medium"
          >
            {{ requestSuccessMessage }}
          </p>
          <p
            v-else-if="requestErrorMessage"
            class="theme-error-text text-sm font-medium"
          >
            {{ requestErrorMessage }}
          </p>

          <button
            class="btn-secondary w-full gap-2"
            :disabled="requestSubmitting"
            type="submit"
          >
            <UserPlus class="h-4 w-4" />
            <span>{{ requestButtonLabel }}</span>
          </button>
        </div>
      </form>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { LogIn, UserPlus } from 'lucide-vue-next';
import { submitAccessRequest } from './api';
import { useAuthStore } from './authStore';

const auth = useAuthStore();
const route = useRoute();
const router = useRouter();

const username = ref('');
const password = ref('');
const errorMessage = ref('');
const contactHandle = ref('');
const accessMessage = ref('');
const accessRequestExpanded = ref(false);
const requestSubmitting = ref(false);
const requestSuccessMessage = ref('');
const requestErrorMessage = ref('');
const requestButtonLabel = computed(() => {
  if (requestSubmitting.value) {
    return 'Sending request';
  }
  return accessRequestExpanded.value ? 'Send request' : 'Request access';
});

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

const submitRequest = async (): Promise<void> => {
  requestSuccessMessage.value = '';
  requestErrorMessage.value = '';
  if (!accessRequestExpanded.value) {
    accessRequestExpanded.value = true;
    return;
  }

  const normalizedContactHandle = contactHandle.value.trim();
  if (!normalizedContactHandle) {
    requestErrorMessage.value = 'Enter a contact handle.';
    return;
  }

  requestSubmitting.value = true;
  try {
    await submitAccessRequest({
      contact_handle: normalizedContactHandle,
      message: accessMessage.value.trim(),
    });
    contactHandle.value = '';
    accessMessage.value = '';
    accessRequestExpanded.value = false;
    requestSuccessMessage.value = 'Request received. We will reach out if access is approved.';
  } catch (error) {
    requestErrorMessage.value = extractErrorMessage(error, 'Failed to send access request.');
  } finally {
    requestSubmitting.value = false;
  }
};

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

<style scoped>
.access-request-expand-enter-active,
.access-request-expand-leave-active {
  max-height: 24rem;
  transition:
    max-height 180ms ease,
    opacity 160ms ease,
    transform 180ms ease;
}

.access-request-expand-enter-from,
.access-request-expand-leave-to {
  max-height: 0;
  opacity: 0;
  transform: translateY(-0.25rem);
}

.access-request-expand-enter-to,
.access-request-expand-leave-from {
  max-height: 24rem;
  opacity: 1;
  transform: translateY(0);
}
</style>
