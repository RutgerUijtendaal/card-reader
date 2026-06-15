export type CurrentUser = {
  auth_enabled: boolean;
  authenticated: boolean;
  csrf_token?: string;
  id?: string;
  username?: string;
  is_staff?: boolean;
  is_superuser?: boolean;
  can_access_admin?: boolean;
  can_manage_users?: boolean;
  can_access_maintenance?: boolean;
};

export type LoginCredentials = {
  username: string;
  password: string;
};

export type PasswordSetupValidationResponse = {
  valid: boolean;
  username?: string;
  detail?: string;
};

export type PasswordSetupRequest = {
  uid: string;
  token: string;
  password: string;
};

export type AccessRequestSubmission = {
  id: string;
  contact_handle: string;
  message: string;
  status: 'pending' | 'approved' | 'declined';
};
