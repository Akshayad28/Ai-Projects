import categoriesConfig from './categories.json';
import { DynamicCardAttributeDTO } from './types';

export function extractDynamicAttributes(
  title: string,
  categoryId?: string,
  rawAttrs?: Record<string, any>
): DynamicCardAttributeDTO[] {
  const result: DynamicCardAttributeDTO[] = [];
  const attrLib = (categoriesConfig as any).attribute_library || {};

  // First check if specific category defines attributes
  let categoryAttributes: any[] = [];
  if (categoryId) {
    const cat = (categoriesConfig as any).categories?.find((c: any) => c.id === categoryId);
    if (cat?.attributes) {
      categoryAttributes = cat.attributes;
    }
  }

  // If no category attributes, use common attribute library keys
  const targetAttrs = categoryAttributes.length > 0
    ? categoryAttributes
    : Object.keys(attrLib).slice(0, 8).map((k) => ({ use: k }));

  for (const item of targetAttrs) {
    const key = item.key || item.use;
    const def = attrLib[key] || item;
    if (!def) continue;

    const label = item.label || def.label || key;
    const unit = item.unit || def.unit;
    const showOnCard = item.show_on_card ?? def.show_on_card ?? true;
    if (!showOnCard) continue;

    // Check if directly in rawAttrs
    if (rawAttrs && rawAttrs[key] !== undefined) {
      result.push({
        key,
        label,
        value: rawAttrs[key],
        unit,
      });
      continue;
    }

    // Attempt regex extraction from title or raw text
    const patterns = def.patterns || [];
    let extractedValue: any = null;

    for (const pat of patterns) {
      const regexStr = typeof pat === 'string' ? pat : pat.regex;
      const multiplier = typeof pat === 'object' && pat.multiply ? pat.multiply : 1;
      try {
        const re = new RegExp(regexStr, 'i');
        const match = title.match(re);
        if (match && match[1]) {
          const valNum = parseFloat(match[1]);
          extractedValue = !isNaN(valNum) ? valNum * multiplier : match[1];
          break;
        }
      } catch {}
    }

    if (extractedValue !== null) {
      result.push({
        key,
        label,
        value: extractedValue,
        unit,
      });
    }
  }

  return result.slice(0, 4);
}
