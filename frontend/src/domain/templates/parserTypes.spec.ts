import { describe, expect, test } from 'vitest';
import {
  TEMPLATE_PARSER_TYPE_DEFINITIONS,
  TEMPLATE_PARSER_TYPE_KEYS,
  TEMPLATE_PARSER_TYPES_HINT,
  type TemplateParserType,
} from '@/domain/templates/parserTypes';

describe('template parser types', () => {
  test('exposes the canonical parser types in order', () => {
    expect(TEMPLATE_PARSER_TYPE_KEYS).toEqual([
      'name',
      'name_mana_cost',
      'type_tag',
      'rules_text',
      'attack',
      'health',
      'affinity',
    ]);
    expect(TEMPLATE_PARSER_TYPE_DEFINITIONS.map(({ label }) => label)).toEqual([
      'Name',
      'Name + mana cost',
      'Type + tag',
      'Rules text',
      'Attack',
      'Health',
      'Affinity',
    ]);
  });

  test('builds the Admin hint from the canonical keys', () => {
    const nameParser: TemplateParserType = 'name';

    expect(nameParser).toBe('name');
    expect(TEMPLATE_PARSER_TYPES_HINT).toBe(
      'name, name_mana_cost, type_tag, rules_text, attack, health, affinity',
    );
  });
});
