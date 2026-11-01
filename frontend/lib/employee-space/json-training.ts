export type JsonValidationResult =
  | { status: 'empty' }
  | { status: 'invalid'; message: string }
  | { status: 'valid' };

export function validateTrainingJson(content: string): JsonValidationResult {
  const trimmed = content.trim();
  if (trimmed.length === 0) {
    return { status: 'empty' };
  }
  try {
    JSON.parse(trimmed);
    return { status: 'valid' };
  } catch (error) {
    const message =
      error instanceof Error ? error.message : 'Invalid JSON syntax.';
    return { status: 'invalid', message };
  }
}

export function prettyPrintTrainingJson(content: string): { ok: true; formatted: string } | { ok: false } {
  const validation = validateTrainingJson(content);
  if (validation.status !== 'valid') {
    return { ok: false };
  }
  const parsed: unknown = JSON.parse(content.trim());
  return { ok: true, formatted: `${JSON.stringify(parsed, null, 2)}\n` };
}

export const JSON_TRAINING_PLACEHOLDER = `{
  "hs_code": "847130",
  "description": "Portable automatic data processing machine",
  "country_of_origin": "IN",
  "duty_rate": 10
}`;
