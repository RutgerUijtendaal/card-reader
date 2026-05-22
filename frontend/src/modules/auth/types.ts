export type CurrentUser = {
  auth_enabled: boolean;
  authenticated: boolean;
  csrf_token?: string;
  id?: string;
  username?: string;
  is_staff?: boolean;
  is_superuser?: boolean;
  can_manage_settings?: boolean;
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
