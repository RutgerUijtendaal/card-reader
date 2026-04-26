export type CurrentUser = {
  auth_enabled: boolean;
  authenticated: boolean;
  csrf_token?: string;
  id?: string;
  username?: string;
  is_staff?: boolean;
  is_superuser?: boolean;
};

export type LoginCredentials = {
  username: string;
  password: string;
};
