import { useEffect, useMemo, useRef, useState, type FormEvent } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { api, type CreateChitMemberInput } from '../api';
import { avatarColor, currentMonth, formatRupees, initials, periodLabel, round2 } from '../format';
import { useI18n } from '../i18n';
import { useToast } from '../toast';

interface MemberRow {
  rowId: number;
  name: string;
  shares: string;
  startMonth: string; // '' = defaults to the chit's start month
}

export function NewChit() {
  const navigate = useNavigate();
  const toast = useToast();
  const { t, tError } = useI18n();
  const [name, setName] = useState('');
  const [amount, setAmount] = useState('');
  const [months, setMonths] = useState('');
  const [startMonth, setStartMonth] = useState(currentMonth());
  const [commission, setCommission] = useState('5');
  const [perShare, setPerShare] = useState('');
  const [perShareTouched, setPerShareTouched] = useState(false);
  const [escalationEnabled, setEscalationEnabled] = useState(false);
  const [escalationPercent, setEscalationPercent] = useState('1');
  const nextRowId = useRef(1);
  const [rows, setRows] = useState<MemberRow[]>([{ rowId: 0, name: '', shares: '1', startMonth: '' }]);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const amountNum = Number(amount);
  const monthsNum = Number(months);
  const monthsShown = monthsNum > 0 ? monthsNum : 0;

  // Suggest the common per-share amount as totalAmount / months, until the owner types their own
  useEffect(() => {
    if (perShareTouched) return;
    setPerShare(amountNum > 0 && monthsNum > 0 ? String(round2(amountNum / monthsNum)) : '');
  }, [amountNum, monthsNum, perShareTouched]);

  const perShareNum = Number(perShare);
  const commissionNum = Number(commission);
  const commissionOk = commission.trim() !== '' && commissionNum >= 0 && commissionNum <= 20;
  const commissionPerMonth = amountNum > 0 && commissionOk ? round2((amountNum * commissionNum) / 100) : 0;
  const escalationPercentNum = Number(escalationPercent);

  const namedRows = rows.filter((r) => r.name.trim() !== '');
  const month1Total = useMemo(
    () =>
      round2(
        namedRows.reduce((sum, r) => {
          const shares = Math.max(1, Math.round(Number(r.shares) || 1));
          const joinsAtStart = !r.startMonth || r.startMonth === startMonth;
          return joinsAtStart && perShareNum > 0 ? sum + perShareNum * shares : sum;
        }, 0),
      ),
    [namedRows, perShareNum, startMonth],
  );
  const duplicates = namedRows
    .map((r) => r.name.trim())
    .filter((n, i, arr) => arr.findIndex((m) => m.toLowerCase() === n.toLowerCase()) !== i);

  function addRow() {
    setRows((prev) => [...prev, { rowId: nextRowId.current++, name: '', shares: '1', startMonth: '' }]);
  }

  function removeRow(rowId: number) {
    setRows((prev) => (prev.length > 1 ? prev.filter((r) => r.rowId !== rowId) : prev));
  }

  function updateRow(rowId: number, patch: Partial<MemberRow>) {
    setRows((prev) => prev.map((r) => (r.rowId === rowId ? { ...r, ...patch } : r)));
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError('');
    if (!name.trim()) return setError(t('newChit.errName'));
    if (!(amountNum > 0)) return setError(t('newChit.errAmount'));
    if (!Number.isInteger(monthsNum) || monthsNum < 1 || monthsNum > 120) return setError(t('newChit.errMonths'));
    if (!(perShareNum > 0)) return setError(t('newChit.errPerShare'));
    if (namedRows.length === 0) return setError(t('newChit.errNoMembers'));
    if (namedRows.length > 100) return setError(t('newChit.errTooMany'));
    if (!commissionOk) return setError(t('newChit.errCommission'));
    if (escalationEnabled && !(escalationPercentNum >= 0 && escalationPercentNum <= 100)) {
      return setError(t('newChit.errEscalation'));
    }

    const members: CreateChitMemberInput[] = namedRows.map((r) => ({
      name: r.name.trim(),
      shares: Math.max(1, Math.round(Number(r.shares) || 1)),
      startMonth: r.startMonth || undefined,
    }));

    setBusy(true);
    try {
      const chit = await api.createChit({
        name: name.trim(),
        totalAmount: amountNum,
        months: monthsNum,
        startMonth,
        perShareAmount: perShareNum,
        members,
        commissionPercent: commissionNum,
        escalationEnabled,
        escalationPercent: escalationEnabled ? escalationPercentNum : undefined,
      });
      toast(t('newChit.saved', { name: chit.name }));
      navigate(`/chits/${chit.id}`, { replace: true });
    } catch (err) {
      setError(tError((err as Error).message));
      setBusy(false);
    }
  }

  return (
    <div className="stack-lg">
      <section className="page-head">
        <div>
          <Link to="/" className="back-link">
            {t('common.allChits')}
          </Link>
          <h1>{t('newChit.title')}</h1>
        </div>
      </section>

      <div className="split">
        <form className="card form" onSubmit={onSubmit} noValidate>
          <label className="field">
            <span>{t('newChit.name')}</span>
            <input
              autoFocus
              name="chitName"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder={t('newChit.namePh')}
              maxLength={100}
            />
          </label>

          <div className="form-row">
            <label className="field">
              <span>{t('newChit.amount')}</span>
              <div className="input-prefix">
                <span>₹</span>
                <input
                  type="number"
                  name="amount"
                  min="1"
                  step="any"
                  inputMode="decimal"
                  value={amount}
                  onChange={(e) => setAmount(e.target.value)}
                  placeholder="100000"
                />
              </div>
            </label>
            <label className="field">
              <span>{t('newChit.months')}</span>
              <input
                type="number"
                name="months"
                min="1"
                max="120"
                step="1"
                inputMode="numeric"
                value={months}
                onChange={(e) => setMonths(e.target.value)}
                placeholder="10"
              />
            </label>
          </div>

          <div className="form-row">
            <label className="field">
              <span>{t('newChit.startMonth')}</span>
              <input
                type="month"
                name="startMonth"
                value={startMonth}
                onChange={(e) => setStartMonth(e.target.value || currentMonth())}
              />
            </label>
            <label className="field">
              <span>
                {t('newChit.commission')} <em className="optional">{t('newChit.commissionHint')}</em>
              </span>
              <div className="input-suffix">
                <input
                  type="number"
                  name="commission"
                  min="0"
                  max="20"
                  step="0.5"
                  inputMode="decimal"
                  value={commission}
                  onChange={(e) => setCommission(e.target.value)}
                />
                <span>%</span>
              </div>
            </label>
          </div>

          <label className="field">
            <span>
              {t('newChit.perShare')} <em className="optional">{t('newChit.perShareHint')}</em>
            </span>
            <div className="input-prefix">
              <span>₹</span>
              <input
                type="number"
                name="perShare"
                min="1"
                step="any"
                inputMode="decimal"
                value={perShare}
                onChange={(e) => {
                  setPerShareTouched(true);
                  setPerShare(e.target.value);
                }}
                placeholder="25000"
              />
            </div>
          </label>

          <div className="field">
            <span>
              {t('newChit.members')} <em className="optional">{t('newChit.membersHint')}</em>
            </span>
            <div className="member-rows">
              {rows.map((row) => (
                <div className="member-row" key={row.rowId}>
                  <input
                    className="member-row-name"
                    value={row.name}
                    onChange={(e) => updateRow(row.rowId, { name: e.target.value })}
                    placeholder={t('newChit.memberNamePh')}
                    maxLength={100}
                  />
                  <label className="member-row-shares">
                    <span>{t('newChit.shares')}</span>
                    <input
                      type="number"
                      min="1"
                      step="1"
                      inputMode="numeric"
                      value={row.shares}
                      onChange={(e) => updateRow(row.rowId, { shares: e.target.value })}
                    />
                  </label>
                  <label className="member-row-start">
                    <span>{t('newChit.joinsFrom')}</span>
                    <input
                      type="month"
                      value={row.startMonth}
                      min={startMonth}
                      onChange={(e) => updateRow(row.rowId, { startMonth: e.target.value })}
                    />
                  </label>
                  <button
                    type="button"
                    className="btn btn-icon btn-ghost"
                    onClick={() => removeRow(row.rowId)}
                    disabled={rows.length === 1}
                    aria-label={t('newChit.removeMember')}
                  >
                    ✕
                  </button>
                </div>
              ))}
            </div>
            <button type="button" className="btn btn-secondary btn-sm" onClick={addRow}>
              {t('newChit.addMemberRow')}
            </button>
          </div>

          <div className="field escalation-field">
            <label className="checkbox-row">
              <input
                type="checkbox"
                checked={escalationEnabled}
                onChange={(e) => setEscalationEnabled(e.target.checked)}
              />
              <span>{t('newChit.escalationToggle')}</span>
            </label>
            {escalationEnabled && (
              <label className="field">
                <span>{t('newChit.escalationPercent')}</span>
                <div className="input-suffix">
                  <input
                    type="number"
                    min="0"
                    max="100"
                    step="0.5"
                    inputMode="decimal"
                    value={escalationPercent}
                    onChange={(e) => setEscalationPercent(e.target.value)}
                  />
                  <span>%</span>
                </div>
                <em className="optional">{t('newChit.escalationHint')}</em>
              </label>
            )}
          </div>

          {duplicates.length > 0 && (
            <div className="alert alert-warn">{t('newChit.duplicate', { names: [...new Set(duplicates)].join(', ') })}</div>
          )}
          {error && <div className="alert alert-error">{error}</div>}

          <div className="form-actions">
            <Link to="/" className="btn btn-ghost">
              {t('common.cancel')}
            </Link>
            <button type="submit" className="btn btn-primary" disabled={busy}>
              {busy ? t('common.saving') : t('newChit.save')}
            </button>
          </div>
        </form>

        <aside className="preview-card">
          <p className="eyebrow light">{t('newChit.livePreview')}</p>
          <h2>{name.trim() || t('newChit.yourChit')}</h2>
          <div className="preview-amount">{formatRupees(amountNum > 0 ? amountNum : 0)}</div>
          <div className="preview-stats">
            <div>
              <span>{t('newChit.previewMembers')}</span>
              <strong>{namedRows.length}</strong>
            </div>
            <div>
              <span>{t('newChit.previewMonths')}</span>
              <strong>{monthsShown}</strong>
            </div>
            <div>
              <span>{t('newChit.perShare')}</span>
              <strong>{formatRupees(perShareNum > 0 ? perShareNum : 0)}</strong>
            </div>
          </div>
          {monthsNum > 0 && monthsNum <= 120 && <p className="preview-period">{periodLabel(startMonth, monthsNum)}</p>}
          <div className="preview-split">
            <div>
              <span>{t('newChit.month1Collection')}</span>
              <strong>{formatRupees(month1Total)}</strong>
            </div>
            <div>
              <span>{t('newChit.commissionMonth')}</span>
              <strong>{formatRupees(commissionPerMonth)}</strong>
            </div>
            <div>
              <span>{t('newChit.commissionTotal', { n: monthsShown })}</span>
              <strong>{formatRupees(round2(commissionPerMonth * monthsShown))}</strong>
            </div>
          </div>
          {amountNum > 0 && month1Total > 0 && month1Total < amountNum && (
            <p className="preview-hint preview-warn">{t('newChit.underfunded', { amount: formatRupees(amountNum - month1Total) })}</p>
          )}
          <p className="preview-hint">{t('newChit.hint')}</p>
          <div className="chip-list">
            {namedRows.slice(0, 30).map((r) => (
              <span key={r.rowId} className="name-chip">
                <span className="avatar avatar-xs" style={{ background: avatarColor(r.name) }}>
                  {initials(r.name)}
                </span>
                {r.name}
                {Number(r.shares) > 1 && <em className="shares-badge">×{Math.round(Number(r.shares))}</em>}
              </span>
            ))}
            {namedRows.length > 30 && <span className="name-chip">{t('newChit.more', { n: namedRows.length - 30 })}</span>}
            {namedRows.length === 0 && <span className="preview-empty">{t('newChit.namesAppear')}</span>}
          </div>
        </aside>
      </div>
    </div>
  );
}
