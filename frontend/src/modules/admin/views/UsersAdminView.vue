<template>
  <div class="page-card space-y-5">
    <div class="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
      <div>
        <h3 class="theme-section-title text-base font-semibold">
          Users
        </h3>
        <p class="theme-section-muted mt-1 text-sm">
          Create regular users, deactivate access, and issue password setup links.
        </p>
      </div>

      <label class="theme-section-muted inline-flex items-center gap-2 text-sm font-medium">
        <input
          v-model="includeInactive"
          class="theme-checkbox h-4 w-4"
          type="checkbox"
        >
        <span>Show archived users</span>
      </label>
    </div>

    <section class="theme-muted-panel space-y-3">
      <div>
        <h4 class="theme-section-title text-sm font-semibold">
          Create user
        </h4>
        <p class="theme-section-muted mt-1 text-xs">
          New users are always regular accounts without staff or maintenance access.
        </p>
      </div>

      <form
        class="flex flex-col gap-3 sm:flex-row"
        @submit.prevent="submitCreate"
      >
        <input
          v-model="newUsername"
          class="input-base"
          placeholder="Username"
          type="text"
        >
        <button
          class="btn-primary text-nowrap"
          :disabled="creating"
          type="submit"
        >
          {{ creating ? 'Creating' : 'Create user' }}
        </button>
      </form>
    </section>

    <section
      v-if="setupResponse"
      class="theme-panel-shell space-y-3 p-4"
    >
      <div class="flex items-start justify-between gap-3">
        <div>
          <h4 class="theme-section-title text-sm font-semibold">
            Password setup link
          </h4>
          <p class="theme-section-muted mt-1 text-xs">
            Share this link with {{ setupResponse.user.username }}. It expires in
            {{ formatExpiry(setupResponse.expires_in_seconds) }}.
          </p>
        </div>
        <button
          class="btn-secondary px-3 py-2 text-xs"
          type="button"
          @click="copySetupUrl"
        >
          Copy link
        </button>
      </div>

      <div class="theme-card-frame rounded-xl p-3">
        <code class="block break-all text-xs">{{ setupResponse.setup_url }}</code>
      </div>
    </section>

    <section class="space-y-3">
      <div class="flex items-center justify-between gap-3">
        <h4 class="theme-section-title text-sm font-semibold">
          Managed users
        </h4>
        <span class="theme-section-muted text-xs font-medium">
          {{ users.length }} shown
        </span>
      </div>

      <div
        v-if="loading"
        class="theme-empty-state"
      >
        Loading users...
      </div>

      <div
        v-else-if="users.length === 0"
        class="theme-empty-state"
      >
        No managed users found.
      </div>

      <div
        v-else
        class="space-y-3"
      >
        <article
          v-for="user in users"
          :key="user.id"
          class="theme-card-frame flex flex-col gap-3 rounded-xl p-4 lg:flex-row lg:items-center lg:justify-between"
        >
          <div>
            <div class="flex items-center gap-2">
              <p class="theme-section-title text-sm font-semibold">
                {{ user.username }}
              </p>
              <span
                class="theme-pill text-nowrap"
                :class="user.is_active ? 'theme-pill-accent' : ''"
              >
                {{ user.is_active ? 'Active' : 'Archived' }}
              </span>
            </div>
            <p class="theme-section-muted mt-1 text-xs">
              Joined {{ formatDate(user.date_joined) }}. Last sign-in {{ formatDate(user.last_login, 'Never') }}.
            </p>
          </div>

          <div class="flex flex-wrap gap-2">
            <button
              class="btn-secondary px-3 py-2 text-xs"
              type="button"
              @click="issueReset(user.id)"
            >
              Reset password
            </button>
            <button
              v-if="user.is_active"
              class="btn-danger-secondary px-3 py-2 text-xs"
              type="button"
              @click="archiveUser(user.id)"
            >
              Archive
            </button>
            <button
              v-else
              class="btn-secondary px-3 py-2 text-xs"
              type="button"
              @click="restoreArchivedUser(user.id)"
            >
              Restore
            </button>
          </div>
        </article>
      </div>
    </section>

    <section class="space-y-3">
      <div class="flex items-center justify-between gap-3">
        <div>
          <h4 class="theme-section-title text-sm font-semibold">
            Unmanaged users
          </h4>
          <p class="theme-section-muted mt-1 text-xs">
            Staff and admin accounts are visible here but cannot be changed from this screen.
          </p>
        </div>
        <span class="theme-section-muted text-xs font-medium">
          {{ unmanagedUsers.length }} shown
        </span>
      </div>

      <div
        v-if="loading"
        class="theme-empty-state"
      >
        Loading users...
      </div>

      <div
        v-else-if="unmanagedUsers.length === 0"
        class="theme-empty-state"
      >
        No unmanaged users found.
      </div>

      <div
        v-else
        class="space-y-3"
      >
        <article
          v-for="user in unmanagedUsers"
          :key="user.id"
          class="theme-card-frame flex flex-col gap-3 rounded-xl p-4 lg:flex-row lg:items-center lg:justify-between"
        >
          <div>
            <div class="flex items-center gap-2">
              <p class="theme-section-title text-sm font-semibold">
                {{ user.username }}
              </p>
              <span
                class="theme-pill text-nowrap"
                :class="user.is_active ? 'theme-pill-accent' : ''"
              >
                {{ user.is_active ? 'Active' : 'Archived' }}
              </span>
              <span class="theme-pill text-nowrap">
                {{ formatRole(user) }}
              </span>
            </div>
            <p class="theme-section-muted mt-1 text-xs">
              Joined {{ formatDate(user.date_joined) }}.
              <template v-if="user.last_login">
                Last sign-in {{ formatDate(user.last_login) }}.
              </template>
            </p>
          </div>

          <p class="theme-section-muted text-xs font-medium">
            Managed outside this screen
          </p>
        </article>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { toast } from 'vue-sonner';
import { useManagedUsers } from '@/modules/admin/composables/useManagedUsers';

const {
  users,
  unmanagedUsers,
  includeInactive,
  loading,
  setupResponse,
  loadUsers,
  createUser,
  deactivateUser,
  restoreUser,
  resetPassword,
} = useManagedUsers();

const newUsername = ref('');
const creating = ref(false);

const submitCreate = async (): Promise<void> => {
  const username = newUsername.value.trim();
  if (!username) {
    toast.error('Enter a username.');
    return;
  }
  creating.value = true;
  try {
    await createUser(username);
    newUsername.value = '';
    toast.success('User created.');
  } catch (error) {
    toast.error(extractErrorMessage(error, 'Failed to create user.'));
  } finally {
    creating.value = false;
  }
};

const archiveUser = async (userId: string): Promise<void> => {
  try {
    await deactivateUser(userId);
    toast.success('User archived.');
  } catch (error) {
    toast.error(extractErrorMessage(error, 'Failed to archive user.'));
  }
};

const restoreArchivedUser = async (userId: string): Promise<void> => {
  try {
    await restoreUser(userId);
    toast.success('User restored.');
  } catch (error) {
    toast.error(extractErrorMessage(error, 'Failed to restore user.'));
  }
};

const issueReset = async (userId: string): Promise<void> => {
  try {
    await resetPassword(userId);
    toast.success('Password setup link generated.');
  } catch (error) {
    toast.error(extractErrorMessage(error, 'Failed to generate password setup link.'));
  }
};

const copySetupUrl = async (): Promise<void> => {
  if (!setupResponse.value) {
    return;
  }
  await navigator.clipboard.writeText(setupResponse.value.setup_url);
  toast.success('Password setup link copied.');
};

onMounted(() => {
  void loadUsers();
});

const formatDate = (value: string | null, fallback = 'Unknown'): string => {
  if (!value) {
    return fallback;
  }
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? fallback : date.toLocaleString();
};

const formatExpiry = (seconds: number): string => {
  if (seconds < 3600) {
    return `${Math.max(1, Math.round(seconds / 60))} minutes`;
  }
  if (seconds < 86400) {
    return `${Math.max(1, Math.round(seconds / 3600))} hours`;
  }
  return `${Math.max(1, Math.round(seconds / 86400))} days`;
};

const formatRole = (user: { is_superuser: boolean; is_staff: boolean }): string => {
  if (user.is_superuser) {
    return user.is_staff ? 'Superuser + Staff' : 'Superuser';
  }
  if (user.is_staff) {
    return 'Staff';
  }
  return 'User';
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
