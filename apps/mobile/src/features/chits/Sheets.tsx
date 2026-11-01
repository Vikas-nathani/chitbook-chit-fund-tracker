/** Bottom-sheet forms on the chit screen: record payout, add member, confirm delete / leave. */
import { useState } from 'react';
import { Pressable, Text } from 'react-native';

import type { Chit } from '@/api/types';
import { MonthStepper, shiftMonth } from '@/components/MonthStepper';
import { useToast } from '@/components/Toast';
import { Button, Field, Muted, Row, Sheet } from '@/components/ui';
import { useI18n } from '@/i18n';
import { currentMonth, formatRupees, formatSignedRupees, monthLabel, todayIso } from '@/lib/format';
import { colors, font } from '@/theme';

import { escalationBump, parseAmount, suggestedPayout, type ChitMoney } from './gridDraft';
import { useAddMember, useDeletePayout, useSavePayout } from './hooks';

/** Mount with key={month}: the form starts from the month's existing payout (or a suggestion). */
export function PayoutSheet({ chit, money, month, onClose }: { chit: Chit; money: ChitMoney; month: number; onClose: () => void }) {
  const { t, tError } = useI18n();
  const toast = useToast();
  const save = useSavePayout(chit.id);
  const remove = useDeletePayout(chit.id);
  const existing = chit.payouts.find((p) => p.month === month) ?? null;
  const [memberId, setMemberId] = useState<number | null>(existing?.memberId ?? null);
  const [amount, setAmount] = useState(String(existing ? existing.amount : suggestedPayout(chit)));
  const [paidOn, setPaidOn] = useState(existing?.paidOn ?? todayIso());

  const collected = money.months[month - 1]?.collected ?? 0;
  const due = money.months[month - 1]?.due ?? 0;
  const amountNum = parseAmount(amount) ?? 0;
  const tookPot = new Map(chit.payouts.filter((p) => p.month !== month).map((p) => [p.memberId, p.month]));
  const chosen = chit.members.find((m) => m.id === memberId);
  const label = monthLabel(chit.startMonth, month);

  async function submit() {
    if (!memberId) return toast(t('payout.errChoose'), 'error');
    if (!(amountNum > 0)) return toast(t('payout.errAmount'), 'error');
    try {
      await save.mutateAsync({ month, input: { memberId, amount: amountNum, paidOn: paidOn || undefined } });
      toast(t('payout.saved', { month: label }));
      onClose();
    } catch (err) {
      toast(tError(err), 'error');
    }
  }

  async function removePayout() {
    try {
      await remove.mutateAsync(month);
      toast(t('payout.removed'), 'info');
      onClose();
    } catch (err) {
      toast(tError(err), 'error');
    }
  }

  return (
    <Sheet visible title={t('payout.title', { month: label })} onClose={onClose}>
      <Muted>
        {t('payout.collectedThisMonth')} {formatRupees(collected)} {t('payout.ofAmount', { amount: formatRupees(due) })}
      </Muted>
      <Text style={{ fontWeight: font.medium, color: colors.text }}>{t('payout.paidTo')}</Text>
      {chit.members.map((m) => {
        const took = tookPot.get(m.id);
        const active = m.id === memberId;
        return (
          <Pressable
            key={m.id}
            accessibilityRole="radio"
            accessibilityState={{ selected: active }}
            onPress={() => setMemberId(m.id)}
            style={{
              padding: 12,
              borderRadius: 10,
              borderWidth: 1,
              borderColor: active ? colors.primary : colors.border,
              backgroundColor: active ? colors.primarySoft : colors.surface,
            }}
          >
            <Text style={{ color: colors.text }}>
              {m.name} {took ? <Muted>{t('payout.alreadyGot', { n: took })}</Muted> : null}
            </Text>
          </Pressable>
        );
      })}
      <Field label={t('payout.amount')} value={amount} onChangeText={setAmount} keyboardType="decimal-pad" />
      <Field label={t('payout.date')} value={paidOn} onChangeText={setPaidOn} placeholder="YYYY-MM-DD" />
      <Muted>
        {t('payout.preview')}{' '}
        <Text style={{ color: collected - amountNum < 0 ? colors.loss : colors.profit, fontWeight: font.bold }}>
          {formatSignedRupees(collected - amountNum)}
        </Text>
      </Muted>
      {chosen && escalationBump(chit) > 0 ? (
        <Muted style={{ color: colors.warning }}>
          {t('payout.escalationPreview', { member: chosen.name, amount: formatRupees(escalationBump(chit)) })}
        </Muted>
      ) : null}
      <Button label={t('payout.save')} onPress={submit} busy={save.isPending} />
      {existing ? <Button variant="ghost" label={t('payout.remove')} onPress={removePayout} busy={remove.isPending} /> : null}
      <Button variant="ghost" label={t('common.cancel')} onPress={onClose} />
    </Sheet>
  );
}

/** Mount only while open, so every opening starts with an empty form. */
export function AddMemberSheet({ chit, onClose }: { chit: Chit; onClose: () => void }) {
  const { t, tError } = useI18n();
  const toast = useToast();
  const add = useAddMember(chit.id);
  const last = shiftMonth(chit.startMonth, chit.months - 1);
  // Joins from the current month by default, kept inside the chit's months
  const suggested = currentMonth() < chit.startMonth ? chit.startMonth : currentMonth() > last ? last : currentMonth();
  const [name, setName] = useState('');
  const [shares, setShares] = useState('1');
  const [startMonth, setStartMonth] = useState(suggested);

  async function submit() {
    const trimmed = name.trim();
    if (!trimmed) return toast(t('addMember.errName'), 'error');
    try {
      await add.mutateAsync({ name: trimmed, shares: Math.max(1, Math.round(Number(shares) || 1)), startMonth });
      toast(t('addMember.saved', { name: trimmed }));
      onClose();
    } catch (err) {
      toast(tError(err), 'error');
    }
  }

  return (
    <Sheet visible title={t('addMember.title')} onClose={onClose}>
      <Field label={t('newChit.memberNamePh')} value={name} onChangeText={setName} maxLength={100} />
      <Field label={t('newChit.shares')} value={shares} onChangeText={setShares} keyboardType="number-pad" />
      <Muted>{t('newChit.joinsFrom')}</Muted>
      <MonthStepper value={startMonth} onChange={setStartMonth} min={chit.startMonth} max={last} accessibilityLabel={t('newChit.joinsFrom')} />
      <Button label={t('addMember.save')} onPress={submit} busy={add.isPending} />
      <Button variant="ghost" label={t('common.cancel')} onPress={onClose} />
    </Sheet>
  );
}

export function ConfirmSheet({
  visible,
  title,
  text,
  confirmLabel,
  cancelLabel,
  danger,
  busy,
  onConfirm,
  onClose,
}: {
  visible: boolean;
  title: string;
  text: string;
  confirmLabel: string;
  cancelLabel: string;
  danger?: boolean;
  busy?: boolean;
  onConfirm: () => void;
  onClose: () => void;
}) {
  return (
    <Sheet visible={visible} title={title} onClose={onClose}>
      <Muted>{text}</Muted>
      <Row>
        <Button style={{ flex: 1 }} variant="secondary" label={cancelLabel} onPress={onClose} />
        <Button style={{ flex: 1 }} variant={danger ? 'danger' : 'primary'} label={confirmLabel} onPress={onConfirm} busy={busy} />
      </Row>
    </Sheet>
  );
}
