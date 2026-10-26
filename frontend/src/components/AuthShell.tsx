import type { ReactNode } from 'react';
import { monthShortName } from '../format';
import { useI18n } from '../i18n';
import { Brand } from './Layout';
import { LangSwitch } from './LangSwitch';

/** Split-screen frame for the login and sign-up pages. */
export function AuthShell({ title, subtitle, children }: { title: string; subtitle: string; children: ReactNode }) {
  const { t } = useI18n();
  const samples: [string, string][] = [
    [t('auth.sample1'), '#f97316'],
    [t('auth.sample2'), '#10b981'],
    [t('auth.sample3'), '#06b6d4'],
  ];

  return (
    <div className="auth-page">
      <section className="auth-hero">
        <div className="auth-hero-glow" aria-hidden />
        <Brand />
        <div className="auth-hero-copy">
          <h1>{t('auth.heroTitle')}</h1>
          <p>{t('auth.heroText')}</p>
        </div>
        <div className="hero-preview" aria-hidden>
          <div className="hero-preview-row hero-preview-head">
            <span>{t('auth.previewMember')}</span>
            <span>{monthShortName('2026-11')}</span>
            <span>{monthShortName('2026-12')}</span>
            <span>{monthShortName('2027-01')}</span>
          </div>
          {samples.map(([name, color]) => (
            <div className="hero-preview-row" key={name}>
              <span className="hero-preview-name">
                <span className="avatar avatar-xs" style={{ background: color }}>
                  {[...name][0]}
                </span>
                {name}
              </span>
              <span>10,000</span>
              <span>10,000</span>
              <span className="hero-preview-edit">9,500</span>
            </div>
          ))}
        </div>
      </section>

      <section className="auth-panel">
        <div className="auth-lang">
          <LangSwitch />
        </div>
        <div className="auth-card">
          <div className="auth-mobile-brand">
            <Brand />
          </div>
          <h2>{title}</h2>
          <p className="muted">{subtitle}</p>
          {children}
        </div>
      </section>
    </div>
  );
}
