export const formatDeckOwnerName = (username: string): string =>
  username.length === 0 ? username : username[0].toLocaleUpperCase() + username.slice(1);
