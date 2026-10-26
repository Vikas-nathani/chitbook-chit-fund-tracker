import { useI18n, type Lang } from '../i18n';

const OPTIONS: { lang: Lang; label: string; full: string }[] = [
  { lang: 'en', label: 'EN', full: 'English' },
  { lang: 'te', label: 'తె', full: 'తెలుగు' },
];

/** EN | తె toggle. `tone="dark"` for the gradient top bar, `"light"` on white pages. */
export function LangSwitch({ tone = 'light' }: { tone?: 'light' | 'dark' }) {
  const { lang, setLang, t } = useI18n();
  return (
    <div className={`lang-switch lang-${tone}`} role="group" aria-label={t('common.language')}>
      {OPTIONS.map((o) => (
        <button
          key={o.lang}
          type="button"
          lang={o.lang}
          className={lang === o.lang ? 'is-on' : ''}
          aria-pressed={lang === o.lang}
          title={o.full}
          onClick={() => setLang(o.lang)}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}
