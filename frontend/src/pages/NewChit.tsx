import { useMemo, useState, type FormEvent } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { api } from '../api';
import { avatarColor, currentMonth, formatRupees, initials, periodLabel, round2 } from '../format';
import { useI18n } from '../i18n';
import { useToast } from '../toast';

/** Names typed one per line (commas also accepted). */
function parseNames(text: string): string[] {
  return text
    .split(/[\n,]/)
    .map((n) => n.trim())
    .filter(Boolean);
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
  const [namesText, setNamesText] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const names = useMemo(() => parseNames(namesText), [namesText]);
  const amountNum = Number(amount);
  const monthsNum = Number(months);
  const monthsShown = monthsNum > 0 ? monthsNum : 0;
  const installment = names.length > 0 && amountNum > 0 ? round2(amountNum / names.length) : 0;
  const commissionNum = Number(commission);
  const commissionOk = commission.trim() !== '' && commissionNum >= 0 && commissionNum <= 20;
  const commissionPerMonth = amountNum > 0 && commissionOk ? round2((amountNum * commissionNum) / 100) : 0;
  const payoutPerMonth = amountNum > 0 ? round2(amountNum - commissionPerMonth) : 0;
  const duplicates = names.filter((n, i) => names.findIndex((m) => m.toLowerCase() === n.toLowerCase()) !== i);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError('');
    if (!name.trim()) return setError(t('newChit.errName'));
    if (!(amountNum > 0)) return setError(t('newChit.errAmount'));
    if (!Number.isInteger(monthsNum) || monthsNum < 1 || monthsNum > 120) return setError(t('newChit.errMonths'));
    if (names.length === 0) return setError(t('newChit.errNoMembers'));
    if (names.length > 100) return setError(t('newChit.errTooMany'));
    if (!commissionOk) return setError(t('newChit.errCommission'));

    setBusy(true);
    try {
      const chit = await api.createChit({
        name: name.trim(),
        totalAmount: amountNum,
        months: monthsNum,
        startMonth,
        memberNames: names,
        commissionPercent: commissionNum,
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
              {t('newChit.members')} <em className="optional">{t('newChit.membersHint')}</em>
            </span>
            <textarea
              rows={7}
              name="members"
              value={namesText}
              onChange={(e) => setNamesText(e.target.value)}
              placeholder={t('newChit.membersPh')}
            />
          </label>

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
              <strong>{names.length}</strong>
            </div>
            <div>
              <span>{t('newChit.previewMonths')}</span>
              <strong>{monthsShown}</strong>
            </div>
            <div>
              <span>{t('newChit.perMember')}</span>
              <strong>{formatRupees(installment)}</strong>
            </div>
          </div>
          {monthsNum > 0 && monthsNum <= 120 && <p className="preview-period">{periodLabel(startMonth, monthsNum)}</p>}
          <div className="preview-split">
            <div>
              <span>{t('newChit.payoutEach')}</span>
              <strong>{formatRupees(payoutPerMonth)}</strong>
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
          <p className="preview-hint">{t('newChit.hint')}</p>
          <div className="chip-list">
            {names.slice(0, 30).map((n, i) => (
              <span key={`${n}-${i}`} className="name-chip">
                <span className="avatar avatar-xs" style={{ background: avatarColor(n) }}>
                  {initials(n)}
                </span>
                {n}
              </span>
            ))}
            {names.length > 30 && <span className="name-chip">{t('newChit.more', { n: names.length - 30 })}</span>}
            {names.length === 0 && <span className="preview-empty">{t('newChit.namesAppear')}</span>}
          </div>
        </aside>
      </div>
    </div>
  );
}
