/** One month at a time: big tap targets to tick payments, edit amounts and record the payout. */
import { Pressable, StyleSheet, Text, TextInput, View } from 'react-native';

import type { Chit } from '@/api/types';
import { Avatar, Button, Card, Muted, Pill, Row } from '@/components/ui';
import { useI18n } from '@/i18n';
import { formatRupees, formatSignedRupees, monthLabel } from '@/lib/format';
import { TOUCH, colors, font, radius, space } from '@/theme';

import { cellKey, cellPaid, cellText, membersInMonth, parseAmount, type ChitMoney, type Draft } from './gridDraft';

interface Props {
  chit: Chit;
  draft: Draft;
  money: ChitMoney;
  month: number;
  nowIndex: number;
  onMonthChange: (month: number) => void;
  onAmountChange: (memberId: number, month: number, text: string) => void;
  onTogglePaid: (memberId: number, month: number) => void;
  onToggleMonth: (month: number, allPaid: boolean, memberIds: number[]) => void;
  onOpenPayout: (month: number) => void;
}

export function MonthView({ chit, draft, money, month, nowIndex, ...on }: Props) {
  const { t } = useI18n();
  const data = money.months[month - 1];
  if (!data) return null;
  const members = membersInMonth(chit, month);
  const tookPot = new Map(chit.payouts.map((p) => [p.memberId, p.month]));

  return (
    <Card>
      <Row style={{ justifyContent: 'space-between' }}>
        <NavButton label="◀" a11y={t('grid.prevMonth')} disabled={month <= 1} onPress={() => on.onMonthChange(month - 1)} />
        <View style={{ alignItems: 'center' }}>
          <Text style={styles.monthTitle}>{monthLabel(chit.startMonth, month)}</Text>
          <Muted>{t('common.monthNum', { n: month })}</Muted>
        </View>
        <NavButton label="▶" a11y={t('grid.nextMonth')} disabled={month >= chit.months} onPress={() => on.onMonthChange(month + 1)} />
      </Row>
      {month !== nowIndex && nowIndex >= 1 && nowIndex <= chit.months ? (
        <Button variant="ghost" label={t('grid.jumpToToday')} onPress={() => on.onMonthChange(nowIndex)} />
      ) : null}

      <Row style={{ justifyContent: 'space-between', flexWrap: 'wrap' }}>
        <Text style={{ color: colors.text }}>
          {t('grid.collectedDue')}: <Text style={{ fontWeight: font.bold }}>{formatRupees(data.collected)}</Text>{' '}
          <Muted>{t('grid.ofAmount', { amount: formatRupees(data.due) })}</Muted>
        </Text>
        <Muted>{t('grid.paidCount', { n: data.paidCount, total: data.memberCount })}</Muted>
      </Row>

      {members.length > 1 ? (
        <Button
          variant="secondary"
          label={`✓ ${data.allPaid ? t('grid.unmarkAll') : t('grid.markAll')}`}
          onPress={() => on.onToggleMonth(month, data.allPaid, members.map((m) => m.id))}
        />
      ) : null}
      {members.length === 0 ? <Muted>{t('grid.noMembersYet')}</Muted> : null}

      {members.map((member) => {
        const paid = cellPaid(chit, draft, member.id, month);
        const text = cellText(chit, draft, member.id, month);
        const invalid = parseAmount(text) === null;
        const overdue = !paid && data.isDue && month < nowIndex;
        const status = paid ? t('grid.statusPaid') : overdue ? t('grid.statusOverdue') : t('grid.statusPending');
        const edited = cellKey(member.id, month) in draft.amounts || cellKey(member.id, month) in draft.paid;
        const potMonth = tookPot.get(member.id);
        return (
          <View key={member.id} style={[styles.memberRow, edited && styles.edited]}>
            <Avatar name={member.name} />
            <View style={{ flex: 1, gap: 2 }}>
              <Text style={styles.memberName} numberOfLines={1}>
                {member.name}
                {member.shares > 1 ? <Muted> ×{member.shares}</Muted> : null}
              </Text>
              {potMonth ? <Pill label={t('grid.gotPot', { n: potMonth })} tone="warning" /> : null}
            </View>
            <TextInput
              accessibilityLabel={t('grid.amountAria', { member: member.name, month: monthLabel(chit.startMonth, month) })}
              value={text}
              onChangeText={(v) => on.onAmountChange(member.id, month, v)}
              keyboardType="decimal-pad"
              selectTextOnFocus
              style={[styles.amountInput, invalid && { borderColor: colors.loss }]}
            />
            <Pressable
              accessibilityRole="checkbox"
              accessibilityState={{ checked: paid }}
              accessibilityLabel={t('grid.cellAria', { member: member.name, month: monthLabel(chit.startMonth, month), status })}
              onPress={() => on.onTogglePaid(member.id, month)}
              style={[styles.tick, paid ? styles.tickPaid : overdue ? styles.tickOverdue : null]}
            >
              <Text style={{ color: paid ? colors.onPrimary : overdue ? colors.overdue : colors.pending, fontWeight: font.bold }}>
                {paid ? '✓' : '○'}
              </Text>
            </Pressable>
          </View>
        );
      })}

      <View style={styles.payoutBox}>
        {data.payout ? (
          <>
            <Row style={{ justifyContent: 'space-between' }}>
              <Muted>{t('grid.colPaidTo')}</Muted>
              <Text style={styles.memberName}>{data.payout.memberName}</Text>
            </Row>
            <Row style={{ justifyContent: 'space-between' }}>
              <Muted>{t('grid.colPayout')}</Muted>
              <Text style={{ color: colors.text }}>{formatRupees(data.payout.amount)}</Text>
            </Row>
            <Row style={{ justifyContent: 'space-between' }}>
              <Muted>{t('grid.colPl')}</Muted>
              <Text style={{ color: (data.pnl ?? 0) < 0 ? colors.loss : colors.profit, fontWeight: font.bold }}>
                {formatSignedRupees(data.pnl ?? 0)}
              </Text>
            </Row>
            <Button variant="secondary" label={t('grid.edit')} onPress={() => on.onOpenPayout(month)} />
          </>
        ) : (
          <Button variant="secondary" label={t('grid.recordPayout')} onPress={() => on.onOpenPayout(month)} />
        )}
      </View>
    </Card>
  );
}

function NavButton({ label, a11y, disabled, onPress }: { label: string; a11y: string; disabled: boolean; onPress: () => void }) {
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={a11y}
      disabled={disabled}
      onPress={onPress}
      style={[styles.nav, disabled && { opacity: 0.3 }]}
    >
      <Text style={{ color: colors.primary, fontSize: font.lg }}>{label}</Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  monthTitle: { fontSize: font.xl, fontWeight: font.bold, color: colors.text },
  nav: {
    width: TOUCH,
    height: TOUCH,
    borderRadius: radius.pill,
    backgroundColor: colors.primarySoft,
    alignItems: 'center',
    justifyContent: 'center',
  },
  memberRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: space.sm,
    paddingVertical: space.sm,
    borderTopWidth: 1,
    borderTopColor: colors.border,
  },
  edited: { backgroundColor: colors.warningSoft, borderRadius: radius.sm },
  memberName: { fontSize: font.md, fontWeight: font.semibold, color: colors.text },
  amountInput: {
    width: 100,
    minHeight: TOUCH,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.md,
    paddingHorizontal: space.sm,
    textAlign: 'right',
    color: colors.text,
    fontSize: font.md,
  },
  tick: {
    width: TOUCH,
    height: TOUCH,
    borderRadius: radius.pill,
    borderWidth: 2,
    borderColor: colors.border,
    alignItems: 'center',
    justifyContent: 'center',
  },
  tickPaid: { backgroundColor: colors.paid, borderColor: colors.paid },
  tickOverdue: { borderColor: colors.overdue },
  payoutBox: { backgroundColor: colors.surfaceMuted, borderRadius: radius.md, padding: space.md, gap: space.sm, marginTop: space.sm },
});
