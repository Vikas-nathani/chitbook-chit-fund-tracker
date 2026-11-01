import { router } from 'expo-router';
import { useMemo, useRef, useState } from 'react';
import { Pressable, Text, View } from 'react-native';

import type { CreateChitMemberInput } from '@/api/types';
import { MonthStepper, shiftMonth } from '@/components/MonthStepper';
import { useToast } from '@/components/Toast';
import { Avatar, Button, Card, ErrorBanner, Field, Muted, Row, Screen, SectionTitle, Toggle } from '@/components/ui';
import { useCreateChit } from '@/features/chits/hooks';
import { useI18n } from '@/i18n';
import { currentMonth, formatRupees, periodLabel, round2 } from '@/lib/format';
import { colors, font, space } from '@/theme';

interface MemberRow {
  rowId: number;
  name: string;
  shares: string;
  startMonth: string; // '' = from the chit's start month
}

export default function NewChitScreen() {
  const toast = useToast();
  const { t, tError } = useI18n();
  const create = useCreateChit();
  const [name, setName] = useState('');
  const [amount, setAmount] = useState('');
  const [months, setMonths] = useState('');
  const [startMonth, setStartMonth] = useState(currentMonth());
  const [commission, setCommission] = useState('5');
  // null = not typed yet: show the suggestion (total ÷ months)
  const [perShareInput, setPerShareInput] = useState<string | null>(null);
  const [escalationEnabled, setEscalationEnabled] = useState(false);
  const [escalationPercent, setEscalationPercent] = useState('1');
  const nextRowId = useRef(1);
  const [rows, setRows] = useState<MemberRow[]>([{ rowId: 0, name: '', shares: '1', startMonth: '' }]);
  const [error, setError] = useState('');

  const amountNum = Number(amount);
  const monthsNum = Number(months);
  const lastMonth = monthsNum > 0 ? shiftMonth(startMonth, monthsNum - 1) : startMonth;

  // One common per-share amount, suggested as total ÷ months until the owner types their own
  const suggestedPerShare = amountNum > 0 && monthsNum > 0 ? String(round2(amountNum / monthsNum)) : '';
  const perShare = perShareInput ?? suggestedPerShare;
  const perShareNum = Number(perShare);
  const commissionNum = Number(commission);
  const commissionOk = commission.trim() !== '' && commissionNum >= 0 && commissionNum <= 20;
  const commissionPerMonth = amountNum > 0 && commissionOk ? round2((amountNum * commissionNum) / 100) : 0;
  const escalationNum = Number(escalationPercent);
  const namedRows = rows.filter((r) => r.name.trim() !== '');
  const sharesOf = (r: MemberRow) => Math.max(1, Math.round(Number(r.shares) || 1));

  const month1Total = useMemo(
    () =>
      round2(
        namedRows.reduce(
          (sum, r) => (perShareNum > 0 && (!r.startMonth || r.startMonth === startMonth) ? sum + perShareNum * sharesOf(r) : sum),
          0,
        ),
      ),
    [namedRows, perShareNum, startMonth],
  );
  const duplicates = namedRows
    .map((r) => r.name.trim())
    .filter((n, i, arr) => arr.findIndex((m) => m.toLowerCase() === n.toLowerCase()) !== i);

  const updateRow = (rowId: number, patch: Partial<MemberRow>) =>
    setRows((prev) => prev.map((r) => (r.rowId === rowId ? { ...r, ...patch } : r)));

  async function submit() {
    setError('');
    if (!name.trim()) return setError(t('newChit.errName'));
    if (!(amountNum > 0)) return setError(t('newChit.errAmount'));
    if (!Number.isInteger(monthsNum) || monthsNum < 1 || monthsNum > 120) return setError(t('newChit.errMonths'));
    if (!(perShareNum > 0)) return setError(t('newChit.errPerShare'));
    if (namedRows.length === 0) return setError(t('newChit.errNoMembers'));
    if (namedRows.length > 100) return setError(t('newChit.errTooMany'));
    if (!commissionOk) return setError(t('newChit.errCommission'));
    if (escalationEnabled && !(escalationNum >= 0 && escalationNum <= 100)) return setError(t('newChit.errEscalation'));

    const members: CreateChitMemberInput[] = namedRows.map((r) => ({
      name: r.name.trim(),
      shares: sharesOf(r),
      startMonth: r.startMonth || undefined,
    }));
    try {
      const chit = await create.mutateAsync({
        name: name.trim(),
        totalAmount: amountNum,
        months: monthsNum,
        startMonth,
        perShareAmount: perShareNum,
        members,
        commissionPercent: commissionNum,
        escalationEnabled,
        escalationPercent: escalationEnabled ? escalationNum : undefined,
      });
      toast(t('newChit.saved', { name: chit.name }));
      router.replace(`/chits/${chit.id}`);
    } catch (err) {
      setError(tError(err));
    }
  }

  return (
    <Screen>
      <Card>
        <Field label={t('newChit.name')} placeholder={t('newChit.namePh')} value={name} onChangeText={setName} maxLength={100} />
        <Row style={{ alignItems: 'flex-start' }}>
          <Field style={{ flex: 1 }} label={t('newChit.amount')} value={amount} onChangeText={setAmount} keyboardType="decimal-pad" />
          <Field style={{ flex: 1 }} label={t('newChit.months')} value={months} onChangeText={setMonths} keyboardType="number-pad" />
        </Row>
        <Text style={{ fontWeight: font.medium, color: colors.text }}>{t('newChit.startMonth')}</Text>
        <MonthStepper value={startMonth} onChange={setStartMonth} accessibilityLabel={t('newChit.startMonth')} />
        <Field
          label={t('newChit.commission')}
          hint={t('newChit.commissionHint')}
          value={commission}
          onChangeText={setCommission}
          keyboardType="decimal-pad"
          error={!commissionOk}
        />
        <Field
          label={t('newChit.perShare')}
          hint={t('newChit.perShareHint')}
          value={perShare}
          onChangeText={setPerShareInput}
          keyboardType="decimal-pad"
        />
        <Toggle label={t('newChit.escalationToggle')} value={escalationEnabled} onChange={setEscalationEnabled} />
        {escalationEnabled ? (
          <>
            <Field
              label={t('newChit.escalationPercent')}
              hint="%"
              value={escalationPercent}
              onChangeText={setEscalationPercent}
              keyboardType="decimal-pad"
            />
            <Muted>{t('newChit.escalationHint')}</Muted>
          </>
        ) : null}
      </Card>

      <Card>
        <SectionTitle>{t('newChit.members')}</SectionTitle>
        <Muted>{t('newChit.membersHint')}</Muted>
        {rows.map((row) => (
          <View key={row.rowId} style={{ gap: space.sm, borderTopWidth: 1, borderTopColor: colors.border, paddingTop: space.sm }}>
            <Row>
              <Field
                style={{ flex: 1 }}
                label={t('newChit.memberNamePh')}
                value={row.name}
                onChangeText={(v) => updateRow(row.rowId, { name: v })}
                maxLength={100}
              />
              <Field
                style={{ width: 80 }}
                label={t('newChit.shares')}
                value={row.shares}
                onChangeText={(v) => updateRow(row.rowId, { shares: v })}
                keyboardType="number-pad"
              />
            </Row>
            <Muted>{t('newChit.joinsFrom')}</Muted>
            <MonthStepper
              value={row.startMonth || startMonth}
              min={startMonth}
              max={lastMonth}
              onChange={(v) => updateRow(row.rowId, { startMonth: v === startMonth ? '' : v })}
              accessibilityLabel={t('newChit.joinsFrom')}
            />
            {rows.length > 1 ? (
              <Pressable
                accessibilityRole="button"
                onPress={() => setRows((prev) => prev.filter((r) => r.rowId !== row.rowId))}
              >
                <Text style={{ color: colors.loss }}>✕ {t('newChit.removeMember')}</Text>
              </Pressable>
            ) : null}
          </View>
        ))}
        <Button
          variant="secondary"
          label={t('newChit.addMemberRow')}
          onPress={() => setRows((prev) => [...prev, { rowId: nextRowId.current++, name: '', shares: '1', startMonth: '' }])}
        />
        {duplicates.length > 0 ? <Muted style={{ color: colors.warning }}>{t('newChit.duplicate', { names: duplicates.join(', ') })}</Muted> : null}
      </Card>

      <Card style={{ backgroundColor: colors.primarySoft }}>
        <SectionTitle>{t('newChit.livePreview')}</SectionTitle>
        <Text style={{ fontSize: font.lg, fontWeight: font.bold, color: colors.text }}>{name.trim() || t('newChit.yourChit')}</Text>
        {monthsNum > 0 ? <Muted>{periodLabel(startMonth, monthsNum)}</Muted> : null}
        <PreviewLine label={t('newChit.previewMembers')} value={String(namedRows.length)} />
        <PreviewLine label={t('newChit.perShare')} value={perShareNum > 0 ? formatRupees(perShareNum) : '–'} />
        <PreviewLine label={t('newChit.month1Collection')} value={formatRupees(month1Total)} />
        <PreviewLine label={t('newChit.commissionMonth')} value={formatRupees(commissionPerMonth)} />
        {monthsNum > 0 ? (
          <PreviewLine label={t('newChit.commissionTotal', { n: monthsNum })} value={formatRupees(round2(commissionPerMonth * monthsNum))} />
        ) : null}
        {amountNum > 0 && month1Total > 0 && month1Total < amountNum ? (
          <Muted style={{ color: colors.warning }}>{t('newChit.underfunded', { amount: formatRupees(round2(amountNum - month1Total)) })}</Muted>
        ) : null}
        <Row style={{ flexWrap: 'wrap' }}>
          {namedRows.slice(0, 8).map((r) => (
            <Avatar key={r.rowId} name={r.name} size={30} />
          ))}
          {namedRows.length > 8 ? <Muted>{t('newChit.more', { n: namedRows.length - 8 })}</Muted> : null}
          {namedRows.length === 0 ? <Muted>{t('newChit.namesAppear')}</Muted> : null}
        </Row>
        <Muted>{t('newChit.hint')}</Muted>
      </Card>

      <ErrorBanner message={error} />
      <Button label={create.isPending ? t('common.saving') : t('newChit.save')} onPress={submit} busy={create.isPending} />
    </Screen>
  );
}

function PreviewLine({ label, value }: { label: string; value: string }) {
  return (
    <Row style={{ justifyContent: 'space-between' }}>
      <Muted>{label}</Muted>
      <Text style={{ fontWeight: font.semibold, color: colors.text }}>{value}</Text>
    </Row>
  );
}
