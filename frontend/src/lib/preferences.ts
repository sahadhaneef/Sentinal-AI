export const preferenceOptions = {
  theme: ['system', 'light', 'dark'],
  motion: ['system', 'reduce'],
  polling: ['3000', '4000', '5000'],
} as const;
export type Preferences = { theme: string; motion: string; polling: string };
export const defaultPreferences: Preferences = {
  theme: 'system',
  motion: 'system',
  polling: '4000',
};
export function readPreferences(): Preferences {
  return Object.fromEntries(
    Object.entries(defaultPreferences).map(([key, fallback]) => {
      let value: string | null = null;
      try {
        value = localStorage.getItem(`sentinel.${key}`);
      } catch {
        /* Browser storage may be disabled. */
      }
      return [
        key,
        value && (preferenceOptions[key as keyof Preferences] as readonly string[]).includes(value)
          ? value
          : fallback,
      ];
    }),
  ) as Preferences;
}
export function persistPreference(key: keyof Preferences, value: string) {
  try {
    localStorage.setItem(`sentinel.${key}`, value);
    return true;
  } catch {
    return false;
  }
}
