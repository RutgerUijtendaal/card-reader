export type CardTooltipSymbolLookup = {
  asset_url?: string | null;
  text_token?: string;
};

export type CardTooltipMetadata = {
  id: string;
  key: string;
  label: string;
};

export type CardTooltipSymbol = CardTooltipMetadata & {
  symbol_type: string;
  text_token: string;
  asset_url: string | null;
};

export type CardHoverTooltipModel = {
  id: string;
  template_id: string;
  version_id: string;
  version_number: number;
  previous_version_id: string | null;
  is_latest: boolean;
  name: string;
  type_line: string;
  mana_cost: string;
  mana_symbols: string[];
  attack: number | null;
  health: number | null;
  rules_text: string;
  confidence: number;
  created_at: string;
  keywords: string[];
  tags: CardTooltipMetadata[];
  symbols: CardTooltipSymbol[];
  types: CardTooltipMetadata[];
};
