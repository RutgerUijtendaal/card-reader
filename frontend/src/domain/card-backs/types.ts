export type CardBackRecord = {
  id: string;
  label: string;
  original_filename: string;
  source_file: string;
  stored_path: string;
  width: number;
  height: number;
  checksum: string;
  is_current: boolean;
  image_url: string | null;
  created_at: string;
  updated_at: string;
};

export type PublicCardBackRecord = Pick<
  CardBackRecord,
  'id' | 'label' | 'width' | 'height' | 'image_url' | 'created_at' | 'updated_at'
>;

export type CardBackCurrentResponse = {
  current: PublicCardBackRecord | null;
};
