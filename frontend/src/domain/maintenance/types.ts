export type MaintenanceActionResponse = {
  message: string;
  removed_paths: string[];
  converted?: number;
  already_webp?: number;
  missing?: number;
  failed?: number;
  bytes_before?: number;
  bytes_after?: number;
  failures?: {
    image_id: string;
    path: string;
    detail: string;
  }[];
};
