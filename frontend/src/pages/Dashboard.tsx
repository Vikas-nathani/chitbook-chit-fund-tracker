import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api, type ChitSummary } from '../api';
import { useAuth } from '../auth';
import { currentMonthIndex, formatRupees, formatSignedRupees, periodLabel, round2 } from '../format';
import { useI18n } from '../i18n';

const CARD_ACCENTS = ['accent-indigo', 'accent-pink', 'accent-emerald', 'accent-amber', 'accent-cyan', 'accent-violet'];

export function Dashboard() {
  const { session } = useAuth();
  const { t, tError } = useI18n();
  const [chits, setChits] = useState<ChitSummary[] | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    api.listChits().then(setChits).catch((err) => setError(err.message));
  }, []);

  const firstName = (session!.user.name || session!.user.username).split(' ')[0];
  const hour = new Date().getHours();
  const greetingKey = hour < 12 ? 'dashboard.morning' : hour < 17 ? 'dashboard.afternoon' : 'dashboard.evening';
  const sum = (f: (c: ChitSummary) => number) => round2(chits?.reduce((total, c) => total + f(c), 0) ?? 0);
  const totalCollected = sum((c) => c.collected);
  const totalPending = sum((c) => c.pending);
  const totalOverdue = sum((c) => c.overdue);
  const totalProfit = sum((c) => c.profit);

  return (
    <div className="stack-lg">
      <section className="page-head">
        <div>
          <p className="eyebrow">{t(greetingKey, { name: firstName })}</p>
          <h1>{t('dashboard.title')}</h1>
        </div>
        <Link to="/new" className="btn btn-primary">
          <span className="btn-plus">+</span> {t('dashboard.newChit')}
        </Link>
      </section>

      <section className="stat-grid">
        <div className="stat-tile tile-indigo">
          <span className="stat-label">{t('dashboard.activeChits')}</span>
          <span className="stat-value">{chits?.length ?? '–'}</span>
        </div>
        <div className="stat-tile tile-violet">
          <span className="stat-label">{t('dashboard.collected')}</span>
          <span className="stat-value">{formatRupees(totalCollected)}</span>
        </div>
        <div className="stat-tile tile-amber">
          <span className="stat-label">{t('dashboard.pendingDues')}</span>
          <span className="stat-value">{formatRupees(totalPending)}</span>
          {totalOverdue > 0 && <span className="stat-sub">{t('dashboard.overdueSub', { amount: formatRupees(totalOverdue) })}</span>}
        </div>
        <Link to="/insights" className={`stat-tile ${totalProfit < 0 ? 'tile-rose' : 'tile-emerald'}`}>
          <span className="stat-label">{t('dashboard.profit')}</span>
          <span className="stat-value">{formatSignedRupees(totalProfit)}</span>
          <span className="stat-sub">{t('dashboard.seeInsights')}</span>
        </Link>
      </section>

      {error && <div className="alert alert-error">{tError(error)}</div>}

      {chits === null && !error && (
        <div className="chit-grid">
          {[0, 1, 2].map((i) => (
            <div key={i} className="chit-card skeleton" />
          ))}
        </div>
      )}

      {chits?.length === 0 && (
        <section className="empty-state">
          <div className="empty-illustration">₹</div>
          <h2>{t('dashboard.emptyTitle')}</h2>
          <p className="muted">{t('dashboard.emptyText')}</p>
          <Link to="/new" className="btn btn-primary">
            <span className="btn-plus">+</span> {t('dashboard.emptyCta')}
          </Link>
        </section>
      )}

      {chits && chits.length > 0 && (
        <section className="chit-grid">
          {chits.map((chit, i) => {
            const nowIndex = currentMonthIndex(chit.startMonth);
            const rate = chit.dueToDate > 0 ? Math.min(chit.collected / chit.dueToDate, 1) : 0;
            const pct = Math.round(rate * 100);
            const status =
              nowIndex < 1
                ? t('dashboard.startsSoon')
                : nowIndex > chit.months
                  ? t('dashboard.completed')
                  : t('dashboard.monthOf', { n: nowIndex, total: chit.months });
            return (
              <Link key={chit.id} to={`/chits/${chit.id}`} className={`chit-card ${CARD_ACCENTS[i % CARD_ACCENTS.length]}`}>
                <div className="chit-card-top">
                  <span className="chit-card-icon">{[...chit.name][0]?.toUpperCase()}</span>
                  <span className="pill">{status}</span>
                </div>
                <h3>{chit.name}</h3>
                <p className="chit-card-amount">{formatRupees(chit.totalAmount)}</p>
                <div className="chit-card-meta">
                  <span>👥 {t('dashboard.members', { n: chit.memberCount })}</span>
                  <span>🗓 {t('dashboard.months', { n: chit.months })}</span>
                </div>
                <div className="chit-card-collect">
                  <span>
                    {t('dashboard.collectedAmount')} <b>{formatRupees(chit.collected)}</b>
                  </span>
                  <span className="muted">{chit.dueToDate > 0 ? t('dashboard.pctOfDue', { pct }) : t('dashboard.nothingDue')}</span>
                </div>
                <div className="progress" aria-label={t('dashboard.progressAria', { pct })}>
                  <span style={{ width: `${rate * 100}%` }} />
                </div>
                <div className="chit-card-foot">
                  <span className="muted">{periodLabel(chit.startMonth, chit.months)}</span>
                  <span className={chit.profit < 0 ? 'text-loss' : chit.profit > 0 ? 'text-profit' : 'muted'}>
                    {t('dashboard.pl')} <b>{formatSignedRupees(chit.profit)}</b>
                  </span>
                </div>
              </Link>
            );
          })}
        </section>
      )}
    </div>
  );
}
