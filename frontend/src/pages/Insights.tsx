import { useEffect, useState, type ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { api, type Stats } from '../api';
import { MonthlyChart } from '../components/charts/MonthlyChart';
import {
  avatarColor,
  calendarLabel,
  currentMonth,
  formatPercent,
  formatRupees,
  formatSignedRupees,
  initials,
} from '../format';
import { useI18n } from '../i18n';

// Validated with the dataviz palette checker against the white card surface (CVD-safe)
const PROFIT = '#0d9488';
const LOSS = '#e11d48';
const CUMULATIVE = '#4f46e5';
const DUE = '#4f46e5';
const COLLECTED = '#0d9488';

const DUES_PAGE = 8;

function ChartCard({ title, subtitle, children, table }: { title: string; subtitle: string; children: ReactNode; table: ReactNode }) {
  const { t } = useI18n();
  const [showTable, setShowTable] = useState(false);
  return (
    <section className="card chart-card">
      <div className="chart-card-head">
        <div>
          <h2>{title}</h2>
          <p className="muted small">{subtitle}</p>
        </div>
        <div className="seg-toggle" role="group">
          <button className={!showTable ? 'is-on' : ''} data-view="chart" onClick={() => setShowTable(false)}>
            {t('insights.chart')}
          </button>
          <button className={showTable ? 'is-on' : ''} data-view="table" onClick={() => setShowTable(true)}>
            {t('insights.table')}
          </button>
        </div>
      </div>
      {showTable ? <div className="table-scroll">{table}</div> : children}
    </section>
  );
}

export function Insights() {
  const { t, tn, tError } = useI18n();
  const [stats, setStats] = useState<Stats | null>(null);
  const [error, setError] = useState('');
  const [duesShown, setDuesShown] = useState(DUES_PAGE);

  useEffect(() => {
    api.getStats().then(setStats).catch((err) => setError(err.message));
  }, []);

  if (error) return <div className="alert alert-error">{tError(error)}</div>;
  if (!stats) return <div className="card skeleton skeleton-tall" />;

  const totals = stats.totals;
  const thisMonth = currentMonth();
  const nowLabel = calendarLabel(thisMonth);

  if (totals.chits === 0) {
    return (
      <section className="empty-state">
        <div className="empty-illustration">📈</div>
        <h2>{t('insights.emptyTitle')}</h2>
        <p className="muted">{t('insights.emptyText')}</p>
        <Link to="/new" className="btn btn-primary">
          <span className="btn-plus">+</span> {t('insights.emptyCta')}
        </Link>
      </section>
    );
  }

  const monthlyData = stats.monthly.map((m) => ({
    label: calendarLabel(m.month),
    // The cumulative line stops at the current month; later months have no results yet
    values: { pnl: m.pnl, cumulative: m.month > thisMonth ? NaN : m.cumulativePnl, due: m.due, collected: m.collected },
  }));

  return (
    <div className="stack-lg">
      <section className="page-head">
        <div>
          <p className="eyebrow">{t('insights.eyebrow')}</p>
          <h1>{t('insights.title')}</h1>
        </div>
      </section>

      <section className="kpi-hero">
        <div className="kpi-hero-main">
          <span className="kpi-label">{t('insights.realisedProfit')}</span>
          <span className="kpi-hero-value">{formatSignedRupees(totals.profit)}</span>
          <span className="kpi-hero-note">
            {t('insights.expectedCommission')} <b>{formatRupees(totals.expectedCommission)}</b>
          </span>
        </div>
        <div className="kpi-grid">
          <div className="kpi">
            <span className="kpi-label">{t('insights.cashInHand')}</span>
            <span className="kpi-value">{formatRupees(totals.cashInHand)}</span>
            <span className="kpi-note">{t('insights.cashNote')}</span>
          </div>
          <div className="kpi">
            <span className="kpi-label">{t('insights.collected')}</span>
            <span className="kpi-value">{formatRupees(totals.collected)}</span>
            <span className="kpi-note">{t('insights.collectedNote', { amount: formatRupees(totals.dueToDate) })}</span>
          </div>
          <div className="kpi">
            <span className="kpi-label">{t('insights.pending')}</span>
            <span className="kpi-value">{formatRupees(totals.pending)}</span>
            <span className="kpi-note">{t('insights.pendingNote')}</span>
          </div>
          <div className="kpi kpi-alert">
            <span className="kpi-label">
              <span className="status-dot" aria-hidden /> {t('insights.overdue')}
            </span>
            <span className="kpi-value">{formatRupees(totals.overdue)}</span>
            <span className="kpi-note">{t('insights.overdueNote')}</span>
          </div>
          <div className="kpi">
            <span className="kpi-label">{t('insights.paidOut')}</span>
            <span className="kpi-value">{formatRupees(totals.paidOut)}</span>
            <span className="kpi-note">{t('insights.paidOutNote')}</span>
          </div>
          <div className="kpi">
            <span className="kpi-label">{t('insights.rate')}</span>
            <span className="kpi-value">{formatPercent(totals.collectionRate)}</span>
            <div className="meter" aria-hidden>
              <span style={{ width: `${Math.round((totals.collectionRate ?? 0) * 100)}%` }} />
            </div>
          </div>
        </div>
      </section>

      <div className="chart-row">
        <ChartCard
          title={t('insights.plTitle')}
          subtitle={t('insights.plSub')}
          table={
            <table className="data-table">
              <thead>
                <tr>
                  <th>{t('insights.colMonth')}</th>
                  <th>{t('insights.colCollected')}</th>
                  <th>{t('insights.colPaidOut')}</th>
                  <th>{t('insights.colPl')}</th>
                  <th>{t('insights.colCumulative')}</th>
                </tr>
              </thead>
              <tbody>
                {stats.monthly.map((m) => (
                  <tr key={m.month}>
                    <td>{calendarLabel(m.month)}</td>
                    <td>{formatRupees(m.collected)}</td>
                    <td>{formatRupees(m.payout)}</td>
                    <td className={m.pnl > 0 ? 'text-profit' : m.pnl < 0 ? 'text-loss' : ''}>{formatSignedRupees(m.pnl)}</td>
                    <td>{formatSignedRupees(m.cumulativePnl)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          }
        >
          <MonthlyChart
            data={monthlyData}
            bars={[{ key: 'pnl', label: t('insights.monthPl'), color: PROFIT }]}
            barColor={(_, v) => (v < 0 ? LOSS : PROFIT)}
            line={{ key: 'cumulative', label: t('insights.cumulative'), color: CUMULATIVE }}
            legend={[
              { label: t('insights.profitMonth'), color: PROFIT, kind: 'bar' },
              { label: t('insights.lossMonth'), color: LOSS, kind: 'bar' },
              { label: t('insights.cumulative'), color: CUMULATIVE, kind: 'line' },
            ]}
            signed
            highlightLabel={nowLabel}
            ariaLabel={t('insights.plAria')}
          />
        </ChartCard>

        <ChartCard
          title={t('insights.collTitle')}
          subtitle={t('insights.collSub')}
          table={
            <table className="data-table">
              <thead>
                <tr>
                  <th>{t('insights.colMonth')}</th>
                  <th>{t('insights.due')}</th>
                  <th>{t('insights.colCollected')}</th>
                  <th>{t('insights.gap')}</th>
                </tr>
              </thead>
              <tbody>
                {stats.monthly.map((m) => (
                  <tr key={m.month}>
                    <td>{calendarLabel(m.month)}</td>
                    <td>{formatRupees(m.due)}</td>
                    <td>{formatRupees(m.collected)}</td>
                    <td>{formatRupees(Math.max(m.due - m.collected, 0))}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          }
        >
          <MonthlyChart
            data={monthlyData}
            bars={[
              { key: 'due', label: t('insights.due'), color: DUE },
              { key: 'collected', label: t('insights.collected'), color: COLLECTED },
            ]}
            legend={[
              { label: t('insights.due'), color: DUE, kind: 'bar' },
              { label: t('insights.collected'), color: COLLECTED, kind: 'bar' },
            ]}
            highlightLabel={nowLabel}
            ariaLabel={t('insights.collAria')}
          />
        </ChartCard>
      </div>

      <section className="card flush">
        <div className="section-head">
          <h2>{t('insights.healthTitle')}</h2>
          <p className="muted small">{t('insights.healthSub')}</p>
        </div>
        <div className="table-scroll">
          <table className="data-table health-table">
            <thead>
              <tr>
                <th>{t('insights.colChit')}</th>
                <th>{t('insights.colProgress')}</th>
                <th>{t('insights.colCollected')}</th>
                <th>{t('insights.colPending')}</th>
                <th>{t('insights.colPayouts')}</th>
                <th>{t('insights.colProfit')}</th>
              </tr>
            </thead>
            <tbody>
              {stats.perChit.map((c) => {
                const rate = c.dueToDate > 0 ? Math.min(c.collected / c.dueToDate, 1) : null;
                const elapsed = Math.min(c.monthsElapsed, c.months);
                return (
                  <tr key={c.id}>
                    <td>
                      <Link to={`/chits/${c.id}`} className="chit-link">
                        {c.name}
                      </Link>
                      <span className="muted small block">{formatRupees(c.totalAmount)}</span>
                    </td>
                    <td>
                      <span className="small">{t('insights.monthOf', { n: elapsed, total: c.months })}</span>
                      <div className="meter meter-sm" aria-hidden>
                        <span style={{ width: `${(elapsed / c.months) * 100}%` }} />
                      </div>
                    </td>
                    <td>
                      {formatRupees(c.collected)}
                      <span className="muted small block">{t('insights.pctOfDue', { pct: formatPercent(rate) })}</span>
                    </td>
                    <td>
                      {formatRupees(c.pending)}
                      {c.overdue > 0 && (
                        <span className="badge-overdue">{t('insights.overdueBadge', { amount: formatRupees(c.overdue) })}</span>
                      )}
                    </td>
                    <td>
                      {c.payoutsDone}/{c.months}
                    </td>
                    <td className={c.profit > 0 ? 'text-profit' : c.profit < 0 ? 'text-loss' : ''}>
                      <b>{formatSignedRupees(c.profit)}</b>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>

      <section className="card flush">
        <div className="section-head">
          <h2>{t('insights.duesTitle')}</h2>
          <p className="muted small">
            {stats.pendingDues.length === 0 ? t('insights.allPaid') : tn('insights.duesCount', stats.pendingDues.length)}
          </p>
        </div>
        {stats.pendingDues.length > 0 && (
          <ul className="dues-list">
            {stats.pendingDues.slice(0, duesShown).map((d) => (
              <li key={`${d.chitId}-${d.memberId}-${d.month}`}>
                <span className="avatar avatar-sm" style={{ background: avatarColor(d.memberName) }}>
                  {initials(d.memberName)}
                </span>
                <span className="dues-who">
                  <b>{d.memberName}</b>
                  <Link to={`/chits/${d.chitId}`} className="muted small">
                    {d.chitName} · {calendarLabel(d.calendarMonth)}
                  </Link>
                </span>
                <span className="dues-amount">{formatRupees(d.amount)}</span>
                {d.overdue ? (
                  <span className="badge-overdue">
                    <span aria-hidden>⚠</span> {t('insights.daysOverdue', { n: d.daysOverdue })}
                  </span>
                ) : (
                  <span className="badge-due">{t('insights.dueThisMonth')}</span>
                )}
              </li>
            ))}
          </ul>
        )}
        {stats.pendingDues.length > duesShown && (
          <button className="btn btn-ghost show-more" onClick={() => setDuesShown((n) => n + DUES_PAGE * 2)}>
            {t('insights.showMore', { n: stats.pendingDues.length - duesShown })}
          </button>
        )}
      </section>
    </div>
  );
}
