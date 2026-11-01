/** Whole chit as a scrollable table (members × months). Tap a cell to tick paid / pending. */
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';

import type { Chit } from '@/api/types';
import { Card, Muted } from '@/components/ui';
import { useI18n } from '@/i18n';
import { formatNumber, formatRupees, monthLabel } from '@/lib/format';
import { colors, font, space } from '@/theme';

import { cellPaid, cellValue, type ChitMoney, type Draft } from './gridDraft';

const NAME_W = 110;
const CELL_W = 84;

export function TableView({
  chit,
  draft,
  money,
  nowIndex,
  onTogglePaid,
}: {
  chit: Chit;
  draft: Draft;
  money: ChitMoney;
  nowIndex: number;
  onTogglePaid: (memberId: number, month: number) => void;
}) {
  const { t } = useI18n();
  return (
    <Card>
      <Muted>{t('grid.paymentsHelp')}</Muted>
      <ScrollView horizontal>
        <View>
          <View style={styles.row}>
            <Text style={[styles.head, { width: NAME_W }]}>{t('grid.member')}</Text>
            {money.months.map((m) => (
              <Text key={m.month} style={[styles.head, { width: CELL_W }, m.month === nowIndex && styles.now]}>
                {monthLabel(chit.startMonth, m.month)}
              </Text>
            ))}
            <Text style={[styles.head, { width: CELL_W }]}>{t('grid.total')}</Text>
          </View>
          {chit.members.map((member) => (
            <View key={member.id} style={styles.row}>
              <Text style={[styles.name, { width: NAME_W }]} numberOfLines={1}>
                {member.name}
              </Text>
              {money.months.map((m) => {
                const joined = member.startMonth <= m.calendarMonth;
                if (!joined) return <View key={m.month} style={[styles.cell, styles.notJoined]} />;
                const paid = cellPaid(chit, draft, member.id, m.month);
                const overdue = !paid && m.month < nowIndex;
                return (
                  <Pressable
                    key={m.month}
                    accessibilityRole="checkbox"
                    accessibilityState={{ checked: paid }}
                    onPress={() => onTogglePaid(member.id, m.month)}
                    style={[styles.cell, paid ? styles.paid : overdue ? styles.overdue : null]}
                  >
                    <Text style={styles.cellText}>
                      {paid ? '✓ ' : ''}
                      {formatNumber(cellValue(chit, draft, member.id, m.month))}
                    </Text>
                  </Pressable>
                );
              })}
              <Text style={[styles.cellText, { width: CELL_W, fontWeight: font.bold }]}>
                {formatNumber(money.rowTotals[member.id] ?? 0)}
              </Text>
            </View>
          ))}
          <View style={styles.row}>
            <Text style={[styles.head, { width: NAME_W }]}>{t('grid.collectedDue')}</Text>
            {money.months.map((m) => (
              <Text key={m.month} style={[styles.foot, { width: CELL_W }]}>
                {formatRupees(m.collected)}
                {'\n'}
                <Text style={{ color: colors.textMuted }}>{formatRupees(m.due)}</Text>
              </Text>
            ))}
          </View>
        </View>
      </ScrollView>
    </Card>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: 'row', alignItems: 'center', borderBottomWidth: 1, borderBottomColor: colors.border },
  head: { fontSize: font.xs, fontWeight: font.semibold, color: colors.textMuted, paddingVertical: space.sm, textAlign: 'center' },
  now: { color: colors.primary },
  name: { fontSize: font.sm, fontWeight: font.semibold, color: colors.text, paddingVertical: space.md },
  cell: { width: CELL_W - 4, margin: 2, minHeight: 40, borderRadius: 6, justifyContent: 'center', backgroundColor: colors.surfaceMuted },
  notJoined: { backgroundColor: 'transparent' },
  paid: { backgroundColor: colors.profitSoft },
  overdue: { backgroundColor: colors.lossSoft },
  cellText: { fontSize: font.xs, color: colors.text, textAlign: 'center' },
  foot: { fontSize: 10, color: colors.text, textAlign: 'center', paddingVertical: space.sm },
});
