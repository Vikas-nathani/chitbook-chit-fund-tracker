import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react';
import { en, type MessageKey } from './en';
import { te } from './te';

export type Lang = 'en' | 'te';
type Params = Record<string, string | number>;

const DICTS = { en, te } as const;
const STORAGE_KEY = 'chitbook.lang';

function readStoredLang(): Lang {
  try {
    return localStorage.getItem(STORAGE_KEY) === 'te' ? 'te' : 'en';
  } catch {
    return 'en';
  }
}

// Module-level copy so plain helpers (format.ts) can localise without React context
let currentLang: Lang = readStoredLang();
document.documentElement.lang = currentLang;

export const getLang = () => currentLang;
export const intlLocale = () => (currentLang === 'te' ? 'te-IN' : 'en-IN');

function interpolate(text: string, params?: Params) {
  if (!params) return text;
  return text.replace(/\{(\w+)\}/g, (match, name) => (name in params ? String(params[name]) : match));
}

function translate(lang: Lang, key: MessageKey, params?: Params) {
  return interpolate(DICTS[lang][key] ?? en[key], params);
}

/** Known backend/API messages (English) mapped to dictionary keys, so they can be shown in Telugu. */
const ERROR_PATTERNS: { re: RegExp; key: MessageKey; params?: (m: RegExpMatchArray) => Params }[] = [
  { re: /^Invalid username or password\.?$/i, key: 'errors.invalidLogin' },
  { re: /^Cannot reach the server/i, key: 'errors.network' },
  { re: /^Request failed \((\d+)\)$/, key: 'errors.requestFailed', params: (m) => ({ status: m[1] }) },
  { re: /^An unexpected internal server error/i, key: 'errors.server' },
  { re: /^Authentication required|^Authenticated user no longer exists/i, key: 'errors.authRequired' },
  { re: /^Username already exists: (.+)$/, key: 'errors.usernameExists', params: (m) => ({ value: m[1] }) },
  { re: /^Email already exists: (.+)$/, key: 'errors.emailExists', params: (m) => ({ value: m[1] }) },
  { re: /^Name is required$/, key: 'errors.nameRequired' },
  { re: /^Username must be 1 to 15 characters$/, key: 'errors.usernameLength' },
  { re: /^A valid email is required$/, key: 'errors.emailInvalid' },
  { re: /^Password must be at least 6 characters$/, key: 'errors.passwordShort' },
  { re: /^Chit name is required$/, key: 'errors.chitNameRequired' },
  { re: /^Member name is required$/, key: 'errors.memberNameRequired' },
  {
    re: /^(Chit name|Member name) must be at most (\d+) characters$/,
    key: 'errors.tooLong',
    params: (m) => ({ field: m[1] === 'Chit name' ? 'chit' : 'member', max: m[2] }),
  },
  { re: /^Chit amount must be greater than 0$/, key: 'errors.chitAmountPositive' },
  { re: /^Payout amount must be greater than 0$/, key: 'errors.payoutAmountPositive' },
  { re: /^Months must be between 1 and (\d+)$/, key: 'errors.monthsRange', params: (m) => ({ max: m[1] }) },
  { re: /^Add between 1 and (\d+) member names$/, key: 'errors.membersRange', params: (m) => ({ max: m[1] }) },
  { re: /^Member .* is not part of this chit$/, key: 'errors.memberNotInChit' },
  { re: /^Month must be between 1 and (\d+)$/, key: 'errors.monthRange', params: (m) => ({ max: m[1] }) },
  { re: /^Amounts cannot be negative$/, key: 'errors.negativeAmount' },
  { re: /^Commission must be between 0 and (\d+)%$/, key: 'errors.commissionRange', params: (m) => ({ max: m[1] }) },
  { re: /^Start month must be in yyyy-MM format$/, key: 'errors.startMonthFormat' },
  { re: /^No payout recorded for month (\d+)$/, key: 'errors.noPayout', params: (m) => ({ n: m[1] }) },
  { re: /^Chit not found$/, key: 'errors.chitNotFound' },
];

interface I18nValue {
  lang: Lang;
  setLang: (lang: Lang) => void;
  /** Translate a key, filling {placeholders}. */
  t: (key: MessageKey, params?: Params) => string;
  /** Pick `${base}_one` or `${base}_other` by count; {n} is filled with the count. */
  tn: (base: string, n: number, params?: Params) => string;
  /** Translate an error message from the API (falls back to the original text). */
  tError: (message: string) => string;
}

const I18nContext = createContext<I18nValue | null>(null);

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<Lang>(currentLang);

  const setLang = useCallback((next: Lang) => {
    currentLang = next;
    document.documentElement.lang = next;
    try {
      localStorage.setItem(STORAGE_KEY, next);
    } catch {
      // storage unavailable; the choice lasts for this page only
    }
    setLangState(next);
  }, []);

  const value = useMemo<I18nValue>(() => {
    const t = (key: MessageKey, params?: Params) => translate(lang, key, params);
    const tn = (base: string, n: number, params?: Params) =>
      translate(lang, `${base}_${n === 1 ? 'one' : 'other'}` as MessageKey, { n, ...params });
    const tError = (message: string) => {
      for (const p of ERROR_PATTERNS) {
        const m = message.match(p.re);
        if (!m) continue;
        const params = p.params?.(m);
        // The tooLong field name is itself translated
        if (p.key === 'errors.tooLong' && params) {
          params.field = translate(lang, params.field === 'chit' ? 'newChit.name' : 'newChit.members');
        }
        return translate(lang, p.key, params);
      }
      return message;
    };
    return { lang, setLang, t, tn, tError };
  }, [lang, setLang]);

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n() {
  const ctx = useContext(I18nContext);
  if (!ctx) throw new Error('useI18n must be used inside LanguageProvider');
  return ctx;
}
