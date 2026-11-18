import { createContext, useContext, useEffect, useState, type ReactNode } from 'react';
import {
  defaultPreferences as defaults,
  readPreferences,
  persistPreference,
  type Preferences,
} from '../lib/preferences';
const Context = createContext<{
  preferences: Preferences;
  setPreference: (key: keyof Preferences, value: string) => void;
}>({ preferences: defaults, setPreference: () => {} });
export function PreferencesProvider({ children }: { children: ReactNode }) {
  const [preferences, setPreferences] = useState<Preferences>(readPreferences);
  useEffect(() => {
    const media = window.matchMedia('(prefers-color-scheme: dark)');
    const update = () => {
      document.documentElement.dataset.theme =
        preferences.theme === 'system' ? (media.matches ? 'dark' : 'light') : preferences.theme;
      document.documentElement.dataset.motion = preferences.motion;
    };
    update();
    media.addEventListener('change', update);
    return () => media.removeEventListener('change', update);
  }, [preferences]);
  const setPreference = (key: keyof Preferences, value: string) => {
    persistPreference(key, value);
    setPreferences((p) => ({ ...p, [key]: value }));
  };
  return <Context.Provider value={{ preferences, setPreference }}>{children}</Context.Provider>;
}
export const usePreferences = () => useContext(Context);
