import { Scale, Shield } from 'lucide-vue-next';
import type { Component } from 'vue';
import EvilPoolIcon from '@/domain/cards/components/EvilPoolIcon.vue';
import type { CardPool } from '@/domain/cards/cardPools';

export const CARD_POOL_ICONS: Record<CardPool, Component> = {
  player: Shield,
  evil: EvilPoolIcon,
  neutral: Scale,
};
