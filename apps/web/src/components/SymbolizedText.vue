<template>
  <span class="inline-flex min-w-0 flex-wrap items-center gap-1 align-middle">
    <template v-if="segments.length > 0">
      <template
        v-for="(segment, index) in segments"
        :key="`seg-${index}-${segment.raw}`"
      >
        <img
          v-if="segment.kind === 'symbol' && segment.assetUrl"
          :src="toAbsoluteApiUrl(segment.assetUrl)"
          :alt="segment.label"
          class="inline-block h-4 w-4 object-contain align-middle"
        >
        <span
          v-else
          class="inline-block"
        >{{ segment.label }}</span>
      </template>
    </template>
    <span
      v-else
      class="text-slate-400"
    >{{ emptyLabel }}</span>
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { api, DEFAULT_API_BASE_URL } from '@/api/client';

type SymbolLookup = {
  asset_url?: string | null;
  text_token?: string;
};

type Segment = {
  kind: 'text' | 'symbol';
  raw: string;
  label: string;
  assetUrl: string | null;
};

const props = withDefaults(
  defineProps<{
    text?: string | null;
    tokens?: string[] | null;
    symbolByKey?: Record<string, SymbolLookup>;
    emptyLabel?: string;
  }>(),
  {
    text: '',
    tokens: () => [],
    symbolByKey: () => ({}),
    emptyLabel: '-'
  }
);

const segments = computed<Segment[]>(() =>
  tokenizeText(props.text ?? '', props.tokens ?? [], props.symbolByKey)
);

const toAbsoluteApiUrl = (urlPath: string): string => {
  const base = api.defaults.baseURL ?? DEFAULT_API_BASE_URL;
  if (urlPath.startsWith('http://') || urlPath.startsWith('https://')) {
    return urlPath;
  }
  return `${base.replace(/\/$/, '')}/${urlPath.replace(/^\//, '')}`;
};

const tokenizeText = (
  rawValue: string,
  rawTokens: string[],
  symbolByKey: Record<string, SymbolLookup>
): Segment[] => {
  if (rawTokens.length > 0) {
    return rawTokens
      .map((token) => String(token).trim())
      .filter((token) => token.length > 0)
      .map((token) => toSegment(token, symbolByKey));
  }

  const trimmed = rawValue.trim();
  if (!trimmed) {
    return [];
  }

  const jsonTokens = parseJsonTokenArray(trimmed);
  if (jsonTokens) {
    return jsonTokens.map((token) => toSegment(token, symbolByKey));
  }

  return parseBraceTokenString(trimmed).map((token) => toSegment(token, symbolByKey));
};

const parseJsonTokenArray = (value: string): string[] | null => {
  if (!value.startsWith('[') || !value.endsWith(']')) {
    return null;
  }
  try {
    const parsed = JSON.parse(value);
    if (!Array.isArray(parsed)) {
      return null;
    }
    return parsed.map((item) => String(item).trim()).filter((item) => item.length > 0);
  } catch {
    return null;
  }
};

const parseBraceTokenString = (value: string): string[] => {
  const out: string[] = [];
  const regex = /\{([^}]+)\}/g;
  let cursor = 0;

  while (true) {
    const match = regex.exec(value);
    if (!match) break;

    const before = value.slice(cursor, match.index).trim();
    if (before) {
      out.push(...before.split(/\s+/).filter((part) => part.length > 0));
    }

    const token = match[1]?.trim();
    if (token) {
      out.push(token);
    }
    cursor = match.index + match[0].length;
  }

  const remainder = value.slice(cursor).trim();
  if (remainder) {
    out.push(...remainder.split(/\s+/).filter((part) => part.length > 0));
  }

  return out;
};

const toSegment = (rawToken: string, symbolByKey: Record<string, SymbolLookup>): Segment => {
  const normalized = rawToken.trim();
  const symbol = symbolByKey[normalized];
  if (!symbol) {
    return {
      kind: 'text',
      raw: normalized,
      label: normalized,
      assetUrl: null
    };
  }

  return {
    kind: 'symbol',
    raw: normalized,
    label: symbol.text_token?.trim() || `{${normalized}}`,
    assetUrl: symbol.asset_url ?? null
  };
};
</script>
