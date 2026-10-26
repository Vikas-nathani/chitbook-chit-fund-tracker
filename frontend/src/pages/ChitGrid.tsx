import { useEffect, useMemo, useRef, useState, type FormEvent, type KeyboardEvent } from 'react';
import { Link, useBlocker, useNavigate, useParams } from 'react-router-dom';
import { api, type Chit, type Payout } from '../api';
import {
  avatarColor,
  currentMonthIndex,
  formatNumber,
  formatRupees,
  formatSignedRupees,
  initials,
  monthLabel,
  periodLabel,
  round2,
  todayIso,
} from '../format';
import { useI18n } from '../i18n';
import { useToast } from '../toast';

const cellKey = (memberId: number, month: number) => `${memberId}:${month}`;

/** '' counts as 0; anything else must be a non-negative number (commas allowed). */
function parseAmount(text: string): number | null {
  const cleaned = text.replace(/,/g, '').trim();
  if (cleaned === '') return 0;
  const n = Number(cleaned);
  return Number.isFinite(n) && n >= 0 ? round2(n) : null;
}

interface PayoutDraft {
  month: number;
  memberId: string;
  amount: string;
  paidOn: string;
  existing: boolean;
}

export function ChitGrid() {
  const { id } = useParams();
  const chitId = Number(id);
  const navigate = useNavigate();
  const toast = useToast();
  const { t, tn, tError } = useI18n();

  const [chit, setChit] = useState<Chit | null>(null);
  const [loadError, setLoadError] = useState('');
  // Unsaved edits: cell amount text and paid ticks, keyed by "memberId:month"
  const [amountEdits, setAmountEdits] = useState<Record<string, string>>({});
  const [paidEdits, setPaidEdits] = useState<Record<string, boolean>>({});
  const [totalEdit, setTotalEdit] = useState<string | null>(null);
  const [commissionEdit, setCommissionEdit] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [payoutDraft, setPayoutDraft] = useState<PayoutDraft | null>(null);
  const [payoutBusy, setPayoutBusy] = useState(false);
  const skipBlock = useRef(false);

  useEffect(() => {
    api.getChit(chitId).then(setChit).catch((err) => setLoadError(err.message));
  }, [chitId]);

  const memberIndex = useMemo(() => new Map(chit?.members.map((m, i) => [m.id, i]) ?? []), [chit]);
  const serverAmount = (memberId: number, month: number) => chit?.members[memberIndex.get(memberId) ?? -1]?.amounts[month - 1] ?? 0;
  const serverPaid = (memberId: number, month: number) => chit?.members[memberIndex.get(memberId) ?? -1]?.paid[month - 1] ?? false;

  // Cells always display Indian-grouped text (25,000). The text never changes on focus,
  // so selecting and typing replaces it cleanly; parseAmount accepts commas.
  const cellText = (memberId: number, month: number) => {
    const key = cellKey(memberId, month);
    return key in amountEdits ? amountEdits[key] : formatNumber(serverAmount(memberId, month));
  };
  const cellValue = (memberId: number, month: number) => parseAmount(cellText(memberId, month)) ?? 0;
  const cellPaid = (memberId: number, month: number) => {
    const key = cellKey(memberId, month);
    return key in paidEdits ? paidEdits[key] : serverPaid(memberId, month);
  };

  const invalidCells = Object.values(amountEdits).filter((text) => parseAmount(text) === null).length;
  const totalValue = totalEdit === null ? chit?.totalAmount ?? 0 : Number(totalEdit);
  const totalInvalid = totalEdit !== null && !(Number(totalEdit) > 0);
  const totalChanged = totalEdit !== null && chit !== null && Number(totalEdit) !== chit.totalAmount;
  const commissionValue = commissionEdit === null ? chit?.commissionPercent ?? 0 : Number(commissionEdit);
  const commissionInvalid = commissionEdit !== null && !(commissionEdit.trim() !== '' && commissionValue >= 0 && commissionValue <= 20);
  const commissionChanged = commissionEdit !== null && chit !== null && commissionValue !== chit.commissionPercent;
  const changedCells = new Set([...Object.keys(amountEdits), ...Object.keys(paidEdits)]);
  const dirtyCount = changedCells.size + (totalChanged ? 1 : 0) + (commissionChanged ? 1 : 0);
  const dirty = dirtyCount > 0;
  const hasErrors = invalidCells > 0 || totalInvalid || commissionInvalid;

  // Guard in-app navigation and tab close while there are unsaved edits
  const blocker = useBlocker(
    ({ currentLocation, nextLocation }) => dirty && !skipBlock.current && currentLocation.pathname !== nextLocation.pathname,
  );
  useEffect(() => {
    if (!dirty) return;
    const handler = (e: BeforeUnloadEvent) => {
      e.preventDefault();
      e.returnValue = '';
    };
    window.addEventListener('beforeunload', handler);
    return () => window.removeEventListener('beforeunload', handler);
  }, [dirty]);

  // Live money figures (include unsaved edits), using the same rules as the backend
  const money = useMemo(() => {
    if (!chit) return null;
    const payoutByMonth = new Map(chit.payouts.map((p) => [p.month, p]));
    const rowTotals = chit.members.map(() => 0);
    const months = Array.from({ length: chit.months }, (_, i) => {
      const month = i + 1;
      let due = 0;
      let collected = 0;
      let paidCount = 0;
      chit.members.forEach((m, r) => {
        const v = cellValue(m.id, month);
        due += v;
        rowTotals[r] += v;
        if (cellPaid(m.id, month)) {
          collected += v;
          paidCount++;
        }
      });
      const payout = payoutByMonth.get(month) ?? null;
      return {
        month,
        due: round2(due),
        collected: round2(collected),
        pending: round2(Math.max(due - collected, 0)),
        allPaid: paidCount === chit.members.length,
        payout,
        pnl: payout ? round2(collected - payout.amount) : null,
        isDue: chit.monthSummaries[i]?.isDue ?? false,
      };
    });
    const sum = (f: (m: (typeof months)[number]) => number) => round2(months.reduce((a, m) => a + f(m), 0));
    return {
      months,
      rowTotals: rowTotals.map(round2),
      grand: sum((m) => m.due),
      collected: sum((m) => m.collected),
      pending: sum((m) => (m.isDue ? m.pending : 0)),
      paidOut: sum((m) => m.payout?.amount ?? 0),
      profit: sum((m) => m.pnl ?? 0),
    };
  }, [chit, amountEdits, paidEdits]);

  function onCellChange(memberId: number, month: number, text: string) {
    const key = cellKey(memberId, month);
    setAmountEdits((prev) => {
      const next = { ...prev };
      const parsed = parseAmount(text);
      // Typing the original value back clears the edit
      if (parsed !== null && text.trim() !== '' && parsed === serverAmount(memberId, month)) delete next[key];
      else next[key] = text;
      return next;
    });
  }

  /** On blur, tidy a valid edit into grouped form (20000 -> 20,000). */
  function onCellBlur(key: string) {
    setAmountEdits((prev) => {
      if (!(key in prev)) return prev;
      const parsed = parseAmount(prev[key]);
      return parsed === null ? prev : { ...prev, [key]: formatNumber(parsed) };
    });
  }

  function setPaid(pairs: { memberId: number; month: number }[], paid: boolean) {
    setPaidEdits((prev) => {
      const next = { ...prev };
      for (const { memberId, month } of pairs) {
        const key = cellKey(memberId, month);
        if (paid === serverPaid(memberId, month)) delete next[key];
        else next[key] = paid;
      }
      return next;
    });
  }

  function toggleMonth(month: number, allPaid: boolean) {
    if (!chit) return;
    setPaid(
      chit.members.map((m) => ({ memberId: m.id, month })),
      !allPaid,
    );
  }

  function onCellKeyDown(e: KeyboardEvent<HTMLInputElement>, row: number, col: number) {
    if (e.key !== 'Enter') return;
    e.preventDefault();
    const target = document.querySelector<HTMLInputElement>(`[data-cell="${row + (e.shiftKey ? -1 : 1)}-${col}"]`);
    target?.focus();
    target?.select();
  }

  async function save() {
    if (!chit || hasErrors) return;
    setSaving(true);
    try {
      const entries = [...changedCells].map((key) => {
        const [memberId, month] = key.split(':').map(Number);
        return {
          memberId,
          month,
          amount: key in amountEdits ? parseAmount(amountEdits[key]) ?? 0 : undefined,
          paid: key in paidEdits ? paidEdits[key] : undefined,
        };
      });
      const updated = await api.updateChit(chit.id, {
        totalAmount: totalChanged ? Number(totalEdit) : undefined,
        commissionPercent: commissionChanged ? commissionValue : undefined,
        entries,
      });
      setChit(updated);
      discard();
      toast(tn('grid.saved', dirtyCount));
    } catch (err) {
      toast(tError((err as Error).message), 'error');
    } finally {
      setSaving(false);
    }
  }

  function discard() {
    setAmountEdits({});
    setPaidEdits({});
    setTotalEdit(null);
    setCommissionEdit(null);
  }

  async function deleteChit() {
    if (!chit) return;
    try {
      await api.deleteChit(chit.id);
      skipBlock.current = true;
      toast(t('delete.done', { name: chit.name }), 'info');
      navigate('/', { replace: true });
    } catch (err) {
      toast(tError((err as Error).message), 'error');
      setConfirmDelete(false);
    }
  }

  function openPayout(month: number, existing: Payout | null) {
    if (!chit) return;
    const suggested = round2(chit.totalAmount * (1 - chit.commissionPercent / 100));
    setPayoutDraft({
      month,
      memberId: existing ? String(existing.memberId) : '',
      amount: String(existing ? existing.amount : suggested),
      paidOn: existing ? existing.paidOn : todayIso(),
      existing: existing !== null,
    });
  }

  async function savePayout(e: FormEvent) {
    e.preventDefault();
    if (!chit || !payoutDraft) return;
    const amount = parseAmount(payoutDraft.amount);
    if (!payoutDraft.memberId) return toast(t('payout.errChoose'), 'error');
    if (!amount || amount <= 0) return toast(t('payout.errAmount'), 'error');
    setPayoutBusy(true);
    try {
      const updated = await api.savePayout(chit.id, payoutDraft.month, {
        memberId: Number(payoutDraft.memberId),
        amount,
        paidOn: payoutDraft.paidOn || undefined,
      });
      setChit(updated);
      setPayoutDraft(null);
      toast(t('payout.saved', { month: monthLabel(chit.startMonth, payoutDraft.month) }));
    } catch (err) {
      toast(tError((err as Error).message), 'error');
    } finally {
      setPayoutBusy(false);
    }
  }

  async function removePayout() {
    if (!chit || !payoutDraft) return;
    setPayoutBusy(true);
    try {
      setChit(await api.deletePayout(chit.id, payoutDraft.month));
      setPayoutDraft(null);
      toast(t('payout.removed'), 'info');
    } catch (err) {
      toast(tError((err as Error).message), 'error');
    } finally {
      setPayoutBusy(false);
    }
  }

  if (loadError) {
    return (
      <div className="empty-state">
        <h2>{t('grid.couldntOpen')}</h2>
        <p className="muted">{tError(loadError)}</p>
        <Link to="/" className="btn btn-primary">
          {t('grid.backToAll')}
        </Link>
      </div>
    );
  }

  if (!chit || !money) return <div className="card skeleton skeleton-tall" />;

  const nowIndex = currentMonthIndex(chit.startMonth);
  const commissionTarget = round2((chit.totalAmount * chit.commissionPercent) / 100);
  const receivedBy = new Map(chit.payouts.map((p) => [p.memberId, p.month]));

  return (
    <div className="stack-lg">
      <Link to="/" className="back-link">
        {t('common.allChits')}
      </Link>

      <section className="hero-card">
        <div className="hero-card-main">
          <div>
            <p className="eyebrow light">{periodLabel(chit.startMonth, chit.months)}</p>
            <h1>{chit.name}</h1>
            <p className="hero-sub">
              {t('grid.subtitle', {
                members: chit.members.length,
                months: chit.months,
                amount: formatRupees(round2(totalValue / chit.members.length)),
              })}
            </p>
          </div>
          <div className="hero-editors">
            <label className={`amount-editor ${totalChanged ? 'is-dirty' : ''} ${totalInvalid ? 'is-invalid' : ''}`}>
              <span>{t('grid.chitAmount')}</span>
              <div className="amount-editor-input">
                <span>₹</span>
                <input
                  type="number"
                  name="totalAmount"
                  min="1"
                  step="any"
                  inputMode="decimal"
                  value={totalEdit ?? String(chit.totalAmount)}
                  onChange={(e) => setTotalEdit(e.target.value)}
                  aria-label={t('grid.chitAmount')}
                />
              </div>
            </label>
            <label className={`amount-editor commission-editor ${commissionChanged ? 'is-dirty' : ''} ${commissionInvalid ? 'is-invalid' : ''}`}>
              <span>{t('grid.commission')}</span>
              <div className="amount-editor-input">
                <input
                  type="number"
                  name="commission"
                  min="0"
                  max="20"
                  step="0.5"
                  inputMode="decimal"
                  value={commissionEdit ?? String(chit.commissionPercent)}
                  onChange={(e) => setCommissionEdit(e.target.value)}
                  aria-label={t('grid.commissionAria')}
                />
                <span>%</span>
              </div>
            </label>
          </div>
        </div>
        <div className="hero-stats">
          <div>
            <span>{t('grid.collected')}</span>
            <strong>{formatRupees(money.collected)}</strong>
          </div>
          <div>
            <span>{t('grid.pendingSoFar')}</span>
            <strong>{formatRupees(money.pending)}</strong>
          </div>
          <div>
            <span>{t('grid.paidOut')}</span>
            <strong>{formatRupees(money.paidOut)}</strong>
          </div>
          <div className={`hero-profit ${money.profit < 0 ? 'is-loss' : ''}`}>
            <span>{t('grid.profit')}</span>
            <strong>{formatSignedRupees(money.profit)}</strong>
          </div>
        </div>
      </section>

      <section className="card grid-card">
        <div className="grid-card-head">
          <div>
            <h2>{t('grid.paymentsTitle')}</h2>
            <p className="muted small">{t('grid.paymentsHelp')}</p>
          </div>
          <div className="grid-legend">
            <span>
              <i className="lg lg-paid">✓</i> {t('grid.paid')}
            </span>
            <span>
              <i className="lg lg-pending" /> {t('grid.pending')}
            </span>
            <span>
              <i className="lg lg-overdue">!</i> {t('grid.overdue')}
            </span>
          </div>
        </div>

        <div className="table-scroll">
          <table className="amount-table">
            <thead>
              <tr>
                <th className="sticky-col">{t('grid.member')}</th>
                {money.months.map((m) => {
                  const label = monthLabel(chit.startMonth, m.month);
                  return (
                    <th key={m.month} className={m.month === nowIndex ? 'is-now' : ''}>
                      <span className="month-num">{t('common.monthNum', { n: m.month })}</span>
                      <span className="month-head">
                        {label}
                        <button
                          type="button"
                          className={`tick tick-sm ${m.allPaid ? 'is-paid' : ''}`}
                          onClick={() => toggleMonth(m.month, m.allPaid)}
                          title={m.allPaid ? t('grid.unmarkAll') : t('grid.markAll')}
                          aria-label={m.allPaid ? t('grid.unmarkAllAria', { month: label }) : t('grid.markAllAria', { month: label })}
                        >
                          ✓
                        </button>
                      </span>
                    </th>
                  );
                })}
                <th className="total-col">{t('grid.total')}</th>
              </tr>
            </thead>
            <tbody>
              {chit.members.map((member, row) => (
                <tr key={member.id}>
                  <th className="sticky-col" scope="row">
                    <div className="member-cell">
                      <span className="avatar avatar-sm" style={{ background: avatarColor(member.name) }}>
                        {initials(member.name)}
                      </span>
                      <span className="member-name" title={member.name}>
                        {member.name}
                        {receivedBy.has(member.id) && (
                          <span className="received-tag">{t('grid.gotPot', { n: receivedBy.get(member.id)! })}</span>
                        )}
                      </span>
                    </div>
                  </th>
                  {money.months.map((m, i) => {
                    const month = m.month;
                    const key = cellKey(member.id, month);
                    const text = cellText(member.id, month);
                    const paid = cellPaid(member.id, month);
                    const invalid = key in amountEdits && parseAmount(text) === null;
                    const overdue = !paid && month < nowIndex && cellValue(member.id, month) > 0;
                    const state = paid ? 'is-paid' : overdue ? 'is-overdue' : '';
                    const label = monthLabel(chit.startMonth, month);
                    const status = paid ? t('grid.statusPaid') : overdue ? t('grid.statusOverdue') : t('grid.statusPending');
                    return (
                      <td key={month} className={month === nowIndex ? 'is-now' : ''}>
                        <div className={`cell ${state} ${changedCells.has(key) ? 'is-dirty' : ''} ${invalid ? 'is-invalid' : ''}`}>
                          <button
                            type="button"
                            className={`tick ${paid ? 'is-paid' : ''}`}
                            onClick={() => setPaid([{ memberId: member.id, month }], !paid)}
                            aria-pressed={paid}
                            aria-label={t('grid.cellAria', { member: member.name, month: label, status })}
                          >
                            {paid ? '✓' : overdue ? '!' : ''}
                          </button>
                          <input
                            className="cell-input"
                            type="text"
                            inputMode="decimal"
                            autoComplete="off"
                            value={text}
                            data-cell={`${row}-${i}`}
                            onChange={(e) => onCellChange(member.id, month, e.target.value)}
                            onKeyDown={(e) => onCellKeyDown(e, row, i)}
                            onFocus={(e) => e.target.select()}
                            onBlur={() => onCellBlur(key)}
                            aria-label={t('grid.amountAria', { member: member.name, month: label })}
                          />
                        </div>
                      </td>
                    );
                  })}
                  <td className="total-col">{formatNumber(money.rowTotals[row])}</td>
                </tr>
              ))}
            </tbody>
            <tfoot>
              <tr>
                <th className="sticky-col">{t('grid.collectedDue')}</th>
                {money.months.map((m) => (
                  <td key={m.month} className={m.month === nowIndex ? 'is-now' : ''}>
                    <span className="foot-collected">{formatNumber(m.collected)}</span>
                    <span className="foot-due">{t('grid.ofAmount', { amount: formatNumber(m.due) })}</span>
                  </td>
                ))}
                <td className="total-col grand">{formatNumber(money.grand)}</td>
              </tr>
            </tfoot>
          </table>
        </div>
      </section>

      <section className="card grid-card">
        <div className="grid-card-head">
          <div>
            <h2>{t('grid.payoutsTitle')}</h2>
            <p className="muted small">
              {t('grid.payoutsHelp', { pct: chit.commissionPercent, amount: formatRupees(commissionTarget) })}
            </p>
          </div>
        </div>
        <div className="table-scroll">
          <table className="data-table payout-table">
            <thead>
              <tr>
                <th>{t('grid.colMonth')}</th>
                <th>{t('grid.colDue')}</th>
                <th>{t('grid.colCollected')}</th>
                <th>{t('grid.colPending')}</th>
                <th>{t('grid.colPaidTo')}</th>
                <th>{t('grid.colPayout')}</th>
                <th>{t('grid.colPl')}</th>
                <th aria-label={t('grid.colActions')} />
              </tr>
            </thead>
            <tbody>
              {money.months.map((m) => (
                <tr key={m.month} className={`${m.month === nowIndex ? 'is-now' : ''} ${m.isDue ? '' : 'is-future'}`}>
                  <td>
                    <b>{monthLabel(chit.startMonth, m.month)}</b>{' '}
                    <span className="muted small">{t('common.monthNum', { n: m.month })}</span>
                  </td>
                  <td>{formatRupees(m.due)}</td>
                  <td>{formatRupees(m.collected)}</td>
                  <td>{m.pending > 0 ? formatRupees(m.pending) : <span className="muted">–</span>}</td>
                  <td>
                    {m.payout ? (
                      <span className="payee">
                        <span className="avatar avatar-xs" style={{ background: avatarColor(m.payout.memberName) }}>
                          {initials(m.payout.memberName)}
                        </span>
                        {m.payout.memberName}
                      </span>
                    ) : (
                      <span className="muted">–</span>
                    )}
                  </td>
                  <td>{m.payout ? formatRupees(m.payout.amount) : <span className="muted">–</span>}</td>
                  <td className={m.pnl === null ? '' : m.pnl > 0 ? 'text-profit' : m.pnl < 0 ? 'text-loss' : ''}>
                    {m.pnl === null ? <span className="muted">–</span> : <b>{formatSignedRupees(m.pnl)}</b>}
                  </td>
                  <td className="row-action">
                    <button
                      className={`btn btn-sm ${m.payout ? 'btn-ghost' : 'btn-soft'}`}
                      data-month={m.month}
                      onClick={() => openPayout(m.month, m.payout)}
                    >
                      {m.payout ? t('grid.edit') : t('grid.recordPayout')}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
            <tfoot>
              <tr>
                <td>
                  <b>{t('grid.total')}</b>
                </td>
                <td>{formatRupees(money.grand)}</td>
                <td>{formatRupees(money.collected)}</td>
                <td>{formatRupees(money.pending)}</td>
                <td>{t('grid.paidCount', { n: chit.payouts.length, total: chit.months })}</td>
                <td>{formatRupees(money.paidOut)}</td>
                <td className={money.profit > 0 ? 'text-profit' : money.profit < 0 ? 'text-loss' : ''}>
                  <b>{formatSignedRupees(money.profit)}</b>
                </td>
                <td />
              </tr>
            </tfoot>
          </table>
        </div>
        <div className="danger-zone">
          <button className="btn btn-danger-ghost" data-action="delete-chit" onClick={() => setConfirmDelete(true)}>
            {t('grid.deleteChit')}
          </button>
        </div>
      </section>

      {dirty && (
        <div className="save-bar" role="region" aria-label={t('grid.unsavedAria')}>
          <span className="save-bar-text">
            <span className="dot" /> {tn('grid.unsaved', dirtyCount)}
            {hasErrors && <em>{t('grid.fixRed')}</em>}
          </span>
          <div className="save-bar-actions">
            <button className="btn btn-ghost-light" data-action="discard" onClick={discard} disabled={saving}>
              {t('grid.discard')}
            </button>
            <button className="btn btn-success" data-action="save" onClick={save} disabled={saving || hasErrors}>
              {saving ? t('common.saving') : t('grid.saveChanges')}
            </button>
          </div>
        </div>
      )}

      {payoutDraft && (
        <div className="modal-backdrop" onClick={() => !payoutBusy && setPayoutDraft(null)}>
          <form
            className="modal modal-form"
            role="dialog"
            aria-modal="true"
            onClick={(e) => e.stopPropagation()}
            onSubmit={savePayout}
            noValidate
          >
            <div className="modal-icon payout">₹</div>
            <h3>
              {t('payout.title', { month: monthLabel(chit.startMonth, payoutDraft.month) })}{' '}
              <span className="muted">({t('common.monthNum', { n: payoutDraft.month })})</span>
            </h3>
            <p className="muted small">
              {t('payout.collectedThisMonth')} <b>{formatRupees(money.months[payoutDraft.month - 1].collected)}</b>{' '}
              {t('payout.ofAmount', { amount: formatRupees(money.months[payoutDraft.month - 1].due) })}
            </p>
            <label className="field">
              <span>{t('payout.paidTo')}</span>
              <select
                name="payee"
                value={payoutDraft.memberId}
                onChange={(e) => setPayoutDraft({ ...payoutDraft, memberId: e.target.value })}
                autoFocus
              >
                <option value="">{t('payout.choose')}</option>
                {chit.members.map((m) => {
                  const got = receivedBy.get(m.id);
                  return (
                    <option key={m.id} value={m.id}>
                      {m.name}
                      {got && got !== payoutDraft.month ? ` ${t('payout.alreadyGot', { n: got })}` : ''}
                    </option>
                  );
                })}
              </select>
            </label>
            <div className="form-row">
              <label className="field">
                <span>{t('payout.amount')}</span>
                <input
                  type="number"
                  name="payoutAmount"
                  min="1"
                  step="any"
                  inputMode="decimal"
                  value={payoutDraft.amount}
                  onChange={(e) => setPayoutDraft({ ...payoutDraft, amount: e.target.value })}
                />
              </label>
              <label className="field">
                <span>{t('payout.date')}</span>
                <input
                  type="date"
                  name="paidOn"
                  value={payoutDraft.paidOn}
                  onChange={(e) => setPayoutDraft({ ...payoutDraft, paidOn: e.target.value })}
                />
              </label>
            </div>
            {(() => {
              const amount = parseAmount(payoutDraft.amount) ?? 0;
              const pnl = round2(money.months[payoutDraft.month - 1].collected - amount);
              return (
                <p className={`payout-preview ${pnl < 0 ? 'is-loss' : ''}`}>
                  {t('payout.preview')} <b>{formatSignedRupees(pnl)}</b>
                </p>
              );
            })()}
            <div className="modal-actions">
              {payoutDraft.existing && (
                <button type="button" className="btn btn-danger-ghost" onClick={removePayout} disabled={payoutBusy}>
                  {t('payout.remove')}
                </button>
              )}
              <button type="button" className="btn btn-ghost" onClick={() => setPayoutDraft(null)} disabled={payoutBusy}>
                {t('common.cancel')}
              </button>
              <button type="submit" className="btn btn-primary" data-action="save-payout" disabled={payoutBusy}>
                {payoutBusy ? t('common.saving') : t('payout.save')}
              </button>
            </div>
          </form>
        </div>
      )}

      {confirmDelete && (
        <div className="modal-backdrop" onClick={() => setConfirmDelete(false)}>
          <div className="modal" role="dialog" aria-modal="true" onClick={(e) => e.stopPropagation()}>
            <div className="modal-icon danger">!</div>
            <h3>{t('delete.title', { name: chit.name })}</h3>
            <p className="muted">{t('delete.text')}</p>
            <div className="modal-actions">
              <button className="btn btn-ghost" onClick={() => setConfirmDelete(false)}>
                {t('common.cancel')}
              </button>
              <button className="btn btn-danger" data-action="confirm-delete" onClick={deleteChit}>
                {t('delete.confirm')}
              </button>
            </div>
          </div>
        </div>
      )}

      {blocker.state === 'blocked' && (
        <div className="modal-backdrop">
          <div className="modal" role="dialog" aria-modal="true">
            <div className="modal-icon warn">!</div>
            <h3>{t('leave.title')}</h3>
            <p className="muted">{tn('leave.text', dirtyCount)}</p>
            <div className="modal-actions">
              <button className="btn btn-ghost" data-action="stay" onClick={() => blocker.reset()}>
                {t('leave.stay')}
              </button>
              <button className="btn btn-danger" data-action="leave" onClick={() => blocker.proceed()}>
                {t('leave.leave')}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
