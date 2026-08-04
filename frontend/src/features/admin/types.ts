import type { TemplateParserType } from '@/domain/templates/types';
import type { JsonObject } from '@/shared/types/json';

export type KnownCatalogKind = 'keywords' | 'tags' | 'symbols' | 'types' | 'deck-roles' | 'deck-types';
export type SuggestedCatalogKind = 'suggested-tags' | 'suggested-types' | 'suggested-deck-types';
export type CatalogKind = KnownCatalogKind | SuggestedCatalogKind;

export type CatalogSearchState = Record<CatalogKind, string>;

export type TemplatePreviewCardOption = {
  id: string;
  label: string;
  name: string;
  template_id: string;
  image_url: string | null;
};

export type TemplatePreviewScope = 'current-template' | 'all-cards';

export type TemplatePreviewSelectionState = TemplatePreviewCardOption & {
  scope: TemplatePreviewScope;
};

export type TemplatePreviewRenderRegion = {
  region_id: string;
  parser_type: TemplateParserType;
  left_pct: number;
  top_pct: number;
  width_pct: number;
  height_pct: number;
};

export type ContentVersionRecord = {
  id: string;
  version_number: string;
  base_version: string;
  description: string;
  card_count: number;
  created_at: string;
  updated_at: string;
};

export type CardMergeCardSummary = {
  id: string;
  key: string;
  label: string;
  latest_name: string;
  version_count: number;
};

export type CardMergeAliasPreview = {
  key: string;
  label: string;
  conflict_card_id: string | null;
};

export type CardMergePreview = {
  target: CardMergeCardSummary;
  sources: CardMergeCardSummary[];
  aliases: CardMergeAliasPreview[];
  relations: {
    deck_entry_collisions: number;
    sideboard_entry_collisions: number;
    group_member_collisions: number;
    hero_references: number;
    anchored_groups: number;
  };
  resulting_version_count: number;
  blocking_conflicts: string[];
  can_apply: boolean;
};

export type CardMergeApplyResponse = {
  message: string;
  preview: CardMergePreview;
};

export type ManagedUserRecord = {
  id: string;
  username: string;
  is_active: boolean;
  is_staff: boolean;
  is_superuser: boolean;
  date_joined: string | null;
  last_login: string | null;
  last_active_at: string | null;
};

export type ManagedUserListResponse = {
  managed_results: ManagedUserRecord[];
  unmanaged_results: ManagedUserRecord[];
};

export type CreateManagedUserRequest = {
  username: string;
};

export type PasswordSetupResponse = {
  user: ManagedUserRecord;
  uid: string;
  token: string;
  setup_url: string;
  expires_in_seconds: number;
};

export type AccessRequestStatus = 'pending' | 'approved' | 'declined';

export type AccessRequestStatusFilter = 'pending' | 'all';

export type AccessRequestUserReference = {
  id: string;
  username: string;
};

export type AccessRequestRecord = {
  id: string;
  contact_handle: string;
  message: string;
  status: AccessRequestStatus;
  created_at: string | null;
  updated_at: string | null;
  resolved_at: string | null;
  resolved_by: AccessRequestUserReference | null;
  created_user: AccessRequestUserReference | null;
};

export type AccessRequestApprovalResponse = {
  access_request: AccessRequestRecord;
  password_setup: PasswordSetupResponse;
};

export type CardGroupMemberRecord = {
  card_id: string;
  card_label: string;
  card_name: string;
  position: number;
  is_anchor: boolean;
  image_url: string | null;
};

export type CardGroupRecord = {
  id: string;
  key: string;
  name: string;
  anchor_card_id: string;
  anchor_card_name: string;
  member_count: number;
  members: CardGroupMemberRecord[];
};

export type LinkedCardPreview = {
  card_id: string;
  card_label: string;
  card_version_id: string;
  card_version_name: string;
  image_url: string | null;
};

export type LinkedDeckPreview = {
  id: string;
  name: string;
  visibility: 'private' | 'unlisted' | 'public';
  owner: { id: string; username: string };
  hero_card: { id: string; name: string; image_url: string | null };
  updated_at: string;
};

export type DeckTagRecord = {
  id: string;
  kind: 'role' | 'type';
  key: string;
  label: string;
  identifiers: string[];
  identifiers_text: string;
  linked_decks?: LinkedDeckPreview[];
  linked_deck_count?: number;
};

export type KeywordRecord = {
  id: string;
  key: string;
  label: string;
  identifiers: string[];
  identifiers_text: string;
  linked_cards?: LinkedCardPreview[];
  linked_card_count?: number;
};

export type TagRecord = {
  id: string;
  key: string;
  label: string;
  identifiers: string[];
  identifiers_text: string;
  linked_cards?: LinkedCardPreview[];
  linked_card_count?: number;
};

export type TypeRecord = {
  id: string;
  key: string;
  label: string;
  identifiers: string[];
  identifiers_text: string;
  linked_cards?: LinkedCardPreview[];
  linked_card_count?: number;
};

export type SymbolRecord = {
  id: string;
  key: string;
  label: string;
  symbol_type: string;
  detector_type: SymbolDetectorType;
  detection_config_json: string;
  text_enrichment_json: string;
  reference_assets_json: string;
  text_token: string;
  enabled: boolean;
  linked_cards?: LinkedCardPreview[];
  linked_card_count?: number;
};

export type CatalogResponse = {
  known: {
    keywords: KeywordRecord[];
    tags: TagRecord[];
    symbols: SymbolRecord[];
    types: TypeRecord[];
  };
  suggested: {
    tags: SuggestionRecord[];
    types: SuggestionRecord[];
  };
};

export type SymbolAssetUploadResponse = {
  relative_path: string;
  absolute_path: string;
};

export type SymbolApiRecord = {
  id: string;
  key: string;
  label: string;
  symbol_type: string;
  detector_type: SymbolDetectorType;
  detection_config_json: JsonObject;
  text_enrichment_json: JsonObject;
  reference_assets_json: string[];
  text_token: string;
  enabled: boolean;
  linked_card_count?: number;
};

export type CatalogApiResponse = {
  known: {
    keywords: KeywordRecord[];
    tags: TagRecord[];
    symbols: SymbolApiRecord[];
    types: TypeRecord[];
  };
  suggested: {
    tags: SuggestionApiRecord[];
    types: SuggestionApiRecord[];
  };
};

export type KeywordUpsertRequest = {
  label?: string;
  key?: string;
  identifiers?: string[];
};

export type TagUpsertRequest = {
  label?: string;
  key?: string;
  identifiers?: string[];
};

export type TypeUpsertRequest = {
  label?: string;
  key?: string;
  identifiers?: string[];
};

export type SymbolDetectorType = 'template';

export type SymbolDetectorOption = {
  value: SymbolDetectorType;
  label: string;
};

export const SYMBOL_DETECTOR_OPTIONS: SymbolDetectorOption[] = [
  { value: 'template', label: 'Template Match' },
];

export type SymbolUpsertRequest = {
  label?: string;
  key?: string;
  symbol_type?: string;
  detector_type?: SymbolDetectorType;
  detection_config_json?: JsonObject;
  text_enrichment_json?: JsonObject;
  reference_assets_json?: string[];
  text_token?: string;
  enabled?: boolean;
};

export type DeckTagUpsertRequest = {
  kind?: 'role' | 'type';
  label?: string;
  key?: string;
};

export type SuggestionStatus = 'pending' | 'accepted' | 'rejected';
export type SuggestionKind = 'tag' | 'type';

export type SuggestionOccurrencePreview = {
  card_id: string;
  card_label: string;
  card_version_id: string;
  card_version_name: string;
  image_url: string | null;
  source_text: string;
  normalized_source_text: string;
};

export type SuggestionAcceptedTarget = {
  id: string;
  key: string;
  label: string;
  identifiers?: string[];
};

export type SuggestionApiRecord = {
  id: string;
  kind: SuggestionKind;
  display_value: string;
  normalized_value: string;
  status: SuggestionStatus;
  occurrence_count: number;
  active_occurrence_count?: number;
  rejected_resubmission_count?: number;
  accepted_target: SuggestionAcceptedTarget | null;
  occurrences: SuggestionOccurrencePreview[];
  linked_decks?: LinkedDeckPreview[];
};

export type SuggestionRecord = SuggestionApiRecord & {
  label: string;
  key: string;
};

export type DeckTagCatalogApiResponse = {
  roles: Array<Omit<DeckTagRecord, 'identifiers' | 'identifiers_text'>>;
  types: Array<Omit<DeckTagRecord, 'identifiers' | 'identifiers_text'>>;
  suggested_types: Array<Omit<SuggestionApiRecord, 'occurrences'> & { linked_decks?: LinkedDeckPreview[] }>;
};

export type CatalogRow = KeywordRecord | TagRecord | TypeRecord | SymbolRecord | DeckTagRecord | SuggestionRecord;

export type CatalogFormEntry = {
  label: string;
  key: string;
  deck_tag_kind?: 'role' | 'type';
  identifiers_text?: string;
  symbol_type: string;
  detector_type: SymbolDetectorType;
  detection_config_json: string;
  text_enrichment_json: string;
  reference_assets_json: string;
  text_token: string;
  enabled: boolean;
};

export type SuggestionAcceptExistingRequest = {
  target_id: string;
};

export type SuggestionAcceptNewRequest = {
  label?: string;
  key?: string;
};
