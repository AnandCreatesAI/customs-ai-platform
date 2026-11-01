export const BUSINESS_MODEL_KEYS = ['user', 'ebooks', 'employee', 'hs_code'] as const;

export type BusinessModelKey = (typeof BUSINESS_MODEL_KEYS)[number];

export type BusinessModelOption = {
  key: BusinessModelKey;
  label: string;
  description: string;
};

export const BUSINESS_MODELS: BusinessModelOption[] = [
  {
    key: 'user',
    label: 'User Model',
    description: 'General customs guidance for authorized platform users.',
  },
  {
    key: 'ebooks',
    label: 'eBooks Model',
    description: 'Answers grounded in customs eBooks and reference material.',
  },
  {
    key: 'employee',
    label: 'Employee Model',
    description: 'Internal workflows and policies for staff members.',
  },
  {
    key: 'hs_code',
    label: 'HS Code Model',
    description: 'Classification support for harmonized system codes.',
  },
];

export const DEFAULT_BUSINESS_MODEL_KEY: BusinessModelKey = 'user';

export const MODEL_SELECTOR_PLACEHOLDER = 'Select Model';

export const COMPOSER_MODEL_REQUIRED_PLACEHOLDER = 'Select a model to start chatting';

export const MODEL_SELECTION_VALIDATION_MESSAGE =
  'Select a business model before sending a message.';

export function getBusinessModelLabel(key: BusinessModelKey): string {
  const match = BUSINESS_MODELS.find((model) => model.key === key);
  return match?.label ?? key;
}

export function isBusinessModelKey(value: string): value is BusinessModelKey {
  return (BUSINESS_MODEL_KEYS as readonly string[]).includes(value);
}
