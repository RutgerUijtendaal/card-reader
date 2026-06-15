<template>
  <section class="grid min-h-[34rem] gap-6 xl:h-[calc(100vh-12rem)] xl:grid-cols-[18rem_minmax(0,1fr)]">
    <aside class="page-card flex min-h-0 flex-col overflow-hidden">
      <div class="theme-divider border-b pb-4">
        <h3 class="theme-section-title text-base font-semibold">
          Users
        </h3>
        <p class="theme-section-muted mt-1 text-sm">
          Manage account access and setup links.
        </p>
      </div>

      <nav class="grid gap-2 py-4">
        <button
          v-for="section in userSections"
          :key="section.id"
          class="rounded-lg border px-3 py-3 text-left transition"
          type="button"
          :class="activeSection === section.id
            ? 'theme-selected-surface-strong'
            : 'theme-card-frame-muted theme-section-title hover:border-[var(--theme-border-strong)]'"
          @click="activeSection = section.id"
        >
          <div class="flex items-center justify-between gap-3">
            <span class="text-sm font-semibold">{{ section.label }}</span>
            <span class="theme-pill theme-pill-success shrink-0 px-2 py-0.5 text-xs font-semibold">
              {{ section.count }}
            </span>
          </div>
          <p
            class="mt-1 text-xs"
            :class="activeSection === section.id ? 'theme-section-title' : 'theme-section-muted'"
          >
            {{ section.description }}
          </p>
        </button>
      </nav>
    </aside>

    <section class="page-card flex min-h-0 flex-col overflow-hidden">
      <div class="theme-divider flex flex-col gap-4 border-b pb-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <h3 class="theme-section-title text-base font-semibold">
            {{ activeSectionTitle }}
          </h3>
          <p class="theme-section-muted mt-1 text-sm">
            {{ activeSectionDescription }}
          </p>
        </div>

        <label
          v-if="activeSection === 'managed' || activeSection === 'unmanaged'"
          class="theme-section-muted inline-flex items-center gap-2 text-sm font-medium"
        >
          <input
            v-model="includeInactive"
            class="theme-checkbox h-4 w-4"
            type="checkbox"
          >
          <span>Show archived users</span>
        </label>
        <label
          v-else
          class="theme-section-muted inline-flex items-center gap-2 text-sm font-medium"
        >
          <input
            v-model="includeResolvedAccessRequests"
            class="theme-checkbox h-4 w-4"
            type="checkbox"
          >
          <span>Show resolved requests</span>
        </label>
      </div>

      <div class="app-scrollbar min-h-0 flex-1 overflow-y-auto py-5">
        <section
          v-if="setupResponse && activeSection !== 'unmanaged'"
          class="theme-panel-shell mb-4 space-y-3 p-4"
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

        <div
          v-if="activeSection === 'managed'"
          class="space-y-4"
        >
          <form
            class="theme-divider flex flex-col gap-3 border-b pb-4 sm:flex-row"
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

          <div
            v-if="loading"
            class="theme-empty-state"
          >
            Loading managed users...
          </div>

          <div
            v-else-if="users.length === 0"
            class="theme-empty-state"
          >
            No managed users found.
          </div>

          <div
            v-if="!loading && users.length > 0"
            class="space-y-3"
          >
            <article
              v-for="user in users"
              :key="user.id"
              class="theme-card-frame flex flex-col gap-3 rounded-xl p-4 lg:flex-row lg:items-center lg:justify-between"
            >
              <div>
                <div class="flex flex-wrap items-center gap-2">
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
                  Joined {{ formatDate(user.date_joined) }}.
                  <template v-if="currentUserIsSuperuser">
                    Last active {{ formatDate(user.last_active_at, 'Never') }}.
                  </template>
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
        </div>

        <div
          v-else-if="activeSection === 'pending'"
          class="space-y-4"
        >
          <div
            v-if="loadingAccessRequests"
            class="theme-empty-state"
          >
            Loading access requests...
          </div>

          <div
            v-else-if="accessRequests.length === 0"
            class="theme-empty-state"
          >
            No access requests found.
          </div>

          <div
            v-if="!loadingAccessRequests && accessRequests.length > 0"
            class="space-y-3"
          >
            <article
              v-for="request in accessRequests"
              :key="request.id"
              class="theme-card-frame flex flex-col gap-3 rounded-xl p-4 lg:flex-row lg:items-start lg:justify-between"
            >
              <div class="min-w-0">
                <div class="flex flex-wrap items-center gap-2">
                  <p class="theme-section-title break-all text-sm font-semibold">
                    {{ request.contact_handle }}
                  </p>
                  <span
                    class="theme-pill text-nowrap"
                    :class="request.status === 'pending' ? 'theme-pill-accent' : ''"
                  >
                    {{ formatAccessRequestStatus(request.status) }}
                  </span>
                </div>
                <p class="theme-section-muted mt-1 text-xs">
                  Requested {{ formatDate(request.created_at) }}.
                  <template v-if="request.resolved_at">
                    Resolved {{ formatDate(request.resolved_at) }}.
                  </template>
                </p>
                <p
                  v-if="request.message"
                  class="theme-section-muted mt-2 whitespace-pre-wrap text-sm"
                >
                  {{ request.message }}
                </p>
                <p
                  v-if="request.created_user"
                  class="theme-section-muted mt-2 text-xs font-medium"
                >
                  Created user {{ request.created_user.username }}.
                </p>
              </div>

              <form
                v-if="request.status === 'pending'"
                class="flex w-full flex-col gap-2 sm:w-auto sm:min-w-[28rem] sm:flex-row sm:items-center"
                @submit.prevent="approvePendingRequest(request.id)"
              >
                <input
                  v-model="approvalUsernames[request.id]"
                  class="input-base sm:flex-1"
                  placeholder="Username"
                  type="text"
                >
                <div class="flex shrink-0 flex-wrap gap-2">
                  <button
                    class="btn-primary px-3 py-2 text-xs"
                    :disabled="resolvingRequestId === request.id"
                    type="submit"
                  >
                    Approve
                  </button>
                  <button
                    class="btn-danger-secondary px-3 py-2 text-xs"
                    :disabled="resolvingRequestId === request.id"
                    type="button"
                    @click="declinePendingRequest(request.id)"
                  >
                    Decline
                  </button>
                </div>
              </form>
            </article>
          </div>
        </div>

        <div
          v-else
          class="space-y-4"
        >
          <div
            v-if="loading"
            class="theme-empty-state"
          >
            Loading unmanaged users...
          </div>

          <div
            v-else-if="unmanagedUsers.length === 0"
            class="theme-empty-state"
          >
            No unmanaged users found.
          </div>

          <div
            v-if="!loading && unmanagedUsers.length > 0"
            class="space-y-3"
          >
            <article
              v-for="user in unmanagedUsers"
              :key="user.id"
              class="theme-card-frame flex flex-col gap-3 rounded-xl p-4 lg:flex-row lg:items-center lg:justify-between"
            >
              <div>
                <div class="flex flex-wrap items-center gap-2">
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
                  <template v-if="currentUserIsSuperuser">
                    Last active {{ formatDate(user.last_active_at, 'Never') }}.
                  </template>
                </p>
              </div>

              <p class="theme-section-muted text-xs font-medium">
                Managed outside this screen
              </p>
            </article>
          </div>
        </div>
      </div>
    </section>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { toast } from 'vue-sonner';
import { useManagedUsers } from '@/modules/admin/composables/useManagedUsers';
import { useAuthStore } from '@/modules/auth/authStore';

const {
  users,
  unmanagedUsers,
  includeInactive,
  includeResolvedAccessRequests,
  accessRequests,
  loading,
  loadingAccessRequests,
  setupResponse,
  loadUsers,
  loadAccessRequests,
  createUser,
  deactivateUser,
  restoreUser,
  resetPassword,
  approveRequest,
  declineRequest,
} = useManagedUsers();

const auth = useAuthStore();
const newUsername = ref('');
const creating = ref(false);
const resolvingRequestId = ref<string | null>(null);
const approvalUsernames = ref<Record<string, string>>({});
type UserSection = 'managed' | 'pending' | 'unmanaged';
const activeSection = ref<UserSection>('managed');
const pendingAccessRequestCount = computed(
  () => accessRequests.value.filter((request) => request.status === 'pending').length,
);
const currentUserIsSuperuser = computed(() => auth.user?.is_superuser === true);
const userSections = computed(() => [
  {
    id: 'managed' as const,
    label: 'Managed',
    description: 'Regular accounts',
    count: users.value.length,
  },
  {
    id: 'pending' as const,
    label: 'Pending',
    description: 'Access requests',
    count: pendingAccessRequestCount.value,
  },
  {
    id: 'unmanaged' as const,
    label: 'Unmanaged',
    description: 'Staff and admins',
    count: unmanagedUsers.value.length,
  },
]);
const activeSectionTitle = computed(() => {
  if (activeSection.value === 'pending') {
    return 'Pending access';
  }
  if (activeSection.value === 'unmanaged') {
    return 'Unmanaged users';
  }
  return 'Managed users';
});
const activeSectionDescription = computed(() => {
  if (activeSection.value === 'pending') {
    return 'Approve requests by choosing a username, then share the setup link out of band.';
  }
  if (activeSection.value === 'unmanaged') {
    return 'Staff and admin accounts are visible here but cannot be changed from this screen.';
  }
  return 'Create regular users, deactivate access, and issue setup links.';
});

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

const approvePendingRequest = async (requestId: string): Promise<void> => {
  const username = (approvalUsernames.value[requestId] ?? '').trim();
  if (!username) {
    toast.error('Enter a username.');
    return;
  }
  resolvingRequestId.value = requestId;
  try {
    await approveRequest(requestId, username);
    delete approvalUsernames.value[requestId];
    toast.success('Access request approved.');
  } catch (error) {
    toast.error(extractErrorMessage(error, 'Failed to approve access request.'));
  } finally {
    resolvingRequestId.value = null;
  }
};

const declinePendingRequest = async (requestId: string): Promise<void> => {
  resolvingRequestId.value = requestId;
  try {
    await declineRequest(requestId);
    delete approvalUsernames.value[requestId];
    toast.success('Access request declined.');
  } catch (error) {
    toast.error(extractErrorMessage(error, 'Failed to decline access request.'));
  } finally {
    resolvingRequestId.value = null;
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
  void loadAccessRequests();
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

const formatAccessRequestStatus = (status: string): string => {
  if (status === 'approved') {
    return 'Approved';
  }
  if (status === 'declined') {
    return 'Declined';
  }
  return 'Pending';
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
