export const HOVER_MODE_VALUES = ['none', 'enlarged', 'details', 'enlarged-details'] as const;

export type HoverMode = (typeof HOVER_MODE_VALUES)[number];

export type HoverModeOption = {
  value: HoverMode;
  label: string;
  description: string;
};

export const DEFAULT_HOVER_MODE: HoverMode = 'details';

export const HOVER_MODE_OPTIONS: HoverModeOption[] = [
  {
    value: 'none',
    label: 'Nothing',
    description: 'Do not show a hover preview when browsing cards.',
  },
  {
    value: 'enlarged',
    label: 'Card',
    description: 'Show a larger card image preview on hover.',
  },
  {
    value: 'details',
    label: 'Details',
    description: 'Show the card details panel on hover.',
  },
  {
    value: 'enlarged-details',
    label: 'Card + Details',
    description: 'Show both a larger card image and the card details panel on hover.',
  },
];

export const isHoverMode = (value: unknown): value is HoverMode =>
  typeof value === 'string' && HOVER_MODE_VALUES.includes(value as HoverMode);
