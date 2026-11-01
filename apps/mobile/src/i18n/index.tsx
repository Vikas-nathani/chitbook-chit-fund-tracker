/**
 * English / Telugu UI text.
 * - t(key, params) fills {placeholders}; tn(base, n) picks `_one` / `_other`.
 * - tError(error) turns an API error into text using its stable `code` (errors.<CODE> keys).
 */
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';

import { ApiError, NETWORK_ERROR } from '@/api/client';
import { prefs } from '@/lib/prefs';

import { en, type MessageKey } from './en';
import { te } from './te';

export type Lang = 'en' | 'te';
type Params = Record<string, string | number>;

const DICTS = { en, te } as const;
const PREF_KEY = 'lang';

// Module-level copy so plain helpers (format.ts) can localise without React context
let currentLang: Lang = 'en';
export const getLang = () => currentLang;
export const intlLocale = () => (currentLang === 'te' ? 'te-IN' : 'en-IN');

function interpolate(text: string, params?: Params) {
  if (!params) return text;
  return text.replace(/\{(\w+)\}/g, (match, name: string) => (name in params ? String(params[name]) : match));
}

export function translate(lang: Lang, key: MessageKey, params?: Params) {
  return interpolate(DICTS[lang][key] ?? en[key], params);
}

const hasKey = (key: string): key is MessageKey => key in en;

export function translateError(lang: Lang, error: unknown): string {
  if (!(error instanceof ApiError)) return translate(lang, 'errors.unknown');
  if (error.code === NETWORK_ERROR) return translate(lang, 'errors.network');
  if (error.code === 'AUTH_ACCOUNT_LOCKED') {
    const seconds = (error.details as { retryAfterSeconds?: number } | null)?.retryAfterSeconds ?? 60;
    return translate(lang, 'errors.AUTH_ACCOUNT_LOCKED', { minutes: Math.max(1, Math.ceil(seconds / 60)) });
  }
  const key = `errors.${error.code}`;
  if (hasKey(key)) return translate(lang, key);
  // Codes without a dedicated text (e.g. CHIT_INVALID_INPUT) carry a precise English message
  return error.message || translate(lang, 'errors.unknown');
}

interface I18nValue {
  lang: Lang;
  setLang: (lang: Lang) => void;
  t: (key: MessageKey, params?: Params) => string;
  tn: (base: string, n: number, params?: Params) => string;
  tError: (error: unknown) => string;
}

const I18nContext = createContext<I18nValue | null>(null);

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<Lang>(currentLang);

  useEffect(() => {
    prefs.get(PREF_KEY).then((stored) => {
      if (stored === 'te' || stored === 'en') {
        currentLang = stored;
        setLangState(stored);
      }
    });
  }, []);

  const setLang = useCallback((next: Lang) => {
    currentLang = next;
    setLangState(next);
    void prefs.set(PREF_KEY, next);
  }, []);

  const value = useMemo<I18nValue>(
    () => ({
      lang,
      setLang,
      t: (key, params) => translate(lang, key, params),
      tn: (base, n, params) => translate(lang, `${base}_${n === 1 ? 'one' : 'other'}` as MessageKey, { n, ...params }),
      tError: (error) => translateError(lang, error),
    }),
    [lang, setLang],
  );

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n() {
  const ctx = useContext(I18nContext);
  if (!ctx) throw new Error('useI18n must be used inside LanguageProvider');
  return ctx;
}
