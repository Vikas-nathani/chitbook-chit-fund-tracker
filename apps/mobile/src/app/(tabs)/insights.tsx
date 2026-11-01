import { router } from 'expo-router';
import { useState } from 'react';
import { RefreshControl, ScrollView, StyleSheet, Text, View } from 'react-native';

import { Button, Card, EmptyState, ErrorBanner, Loading, Muted, Pill, ProgressBar, Row, SectionTitle, StatTile } from '@/components/ui';
import { useStats } from '@/features/chits/hooks';
import { CollectionsChart, PnlChart } from '@/features/insights/Charts';
import { useI18n } from '@/i18n';
import { calendarLabel, currentMonthIndex, formatPercent, formatRupees, formatSignedRupees } from '@/lib/format';
import { colors, font, space } from '@/theme';

const DUES_PAGE = 10;

export default function InsightsScreen() {
  const { t, tn, tError } = useI18n();
  const { data: stats, error, isLoading, refetch, isRefetching } = useStats();
  const [duesShown, setDuesShown] = useState(DUES_PAGE);

  if (isLoading) return <Loading />;
  if (error || !stats) return <View style={styles.content}><ErrorBanner message={tError(error)} /></View>;

  const { totals, monthly, perChit, pendingDues } = stats;
  if (totals.chits === 0) {
    return (
      <View style={styles.content}>
        <EmptyState
          title={t('insights.emptyTitle')}
          text={t('insights.emptyText')}
          action={<Button label={t('insights.emptyCta')} onPress={() => router.push('/chits/new')} />}
        />
      </View>
    );
  }

  const plPoints = monthly.filter((m) => m.payout > 0).map((m) => ({ month: m.month, pnl: m.pnl, cumulative: m.cumulativePnl }));

  return (
    <ScrollView contentContainerStyle={styles.content} refreshControl={<RefreshControl refreshing={isRefetching} onRefresh={() => void refetch()} />}>
      <Card style={{ backgroundColor: totals.profit < 0 ? colors.lossSoft : colors.profitSoft }}>
        <Muted>{t('insights.realisedProfit')}</Muted>
        <Text style={[styles.hero, { color: totals.profit < 0 ? colors.loss : colors.profit }]}>{formatSignedRupees(totals.profit)}</Text>
        <Muted>
          {t('insights.expectedCommission')} <Text style={{ fontWeight: font.bold }}>{formatRupees(totals.expectedCommission)}</Text>
        </Muted>
      </Card>

      <View style={styles.tiles}>
        <StatTile label={t('insights.cashInHand')} value={formatRupees(totals.cashInHand)} sub={t('insights.cashNote')} tone="indigo" />
        <StatTile
          label={t('insights.collected')}
          value={formatRupees(totals.collected)}
          sub={t('insights.collectedNote', { amount: formatRupees(totals.dueToDate) })}
          tone="violet"
        />
        <StatTile label={t('insights.pending')} value={formatRupees(totals.pending)} sub={t('insights.pendingNote')} tone="amber" />
        <StatTile label={t('insights.overdue')} value={formatRupees(totals.overdue)} sub={t('insights.overdueNote')} tone="rose" />
        <StatTile label={t('insights.paidOut')} value={formatRupees(totals.paidOut)} sub={t('insights.paidOutNote')} tone="emerald" />
        <StatTile label={t('insights.rate')} value={formatPercent(totals.collectionRate ?? null)} tone="indigo" />
      </View>

      <Card>
        <SectionTitle>{t('insights.plTitle')}</SectionTitle>
        <Muted>{t('insights.plSub')}</Muted>
        {plPoints.length > 0 ? <PnlChart points={plPoints} label={t('insights.plAria')} /> : <Muted>–</Muted>}
        <Row>
          <Pill label={t('insights.monthPl')} tone="profit" />
          <Pill label={t('insights.cumulative')} />
        </Row>
      </Card>

      <Card>
        <SectionTitle>{t('insights.collTitle')}</SectionTitle>
        <Muted>{t('insights.collSub')}</Muted>
        <CollectionsChart points={monthly} label={t('insights.collAria')} />
      </Card>

      <Card>
        <SectionTitle>{t('insights.healthTitle')}</SectionTitle>
        <Muted>{t('insights.healthSub')}</Muted>
        {perChit.map((c) => {
          const rate = c.dueToDate > 0 ? Math.min(c.collected / c.dueToDate, 1) : 0;
          const nowIndex = Math.min(Math.max(currentMonthIndex(c.startMonth), 0), c.months);
          return (
            <View key={c.id} style={styles.listRow}>
              <Row style={{ justifyContent: 'space-between' }}>
                <Text style={styles.rowTitle} onPress={() => router.push(`/chits/${c.id}`)}>
                  {c.name}
                </Text>
                <Text style={{ color: c.profit < 0 ? colors.loss : colors.profit, fontWeight: font.semibold }}>
                  {formatSignedRupees(c.profit)}
                </Text>
              </Row>
              <Muted>
                {t('insights.monthOf', { n: nowIndex, total: c.months })} · {t('insights.colPayouts')} {c.payoutsDone}/{c.months}
              </Muted>
              <ProgressBar ratio={rate} label={t('insights.pctOfDue', { pct: formatPercent(rate) })} />
              <Row style={{ justifyContent: 'space-between' }}>
                <Muted>{t('insights.pctOfDue', { pct: formatPercent(c.dueToDate > 0 ? rate : null) })}</Muted>
                {c.overdue > 0 ? <Pill label={t('insights.overdueBadge', { amount: formatRupees(c.overdue) })} tone="loss" /> : null}
              </Row>
            </View>
          );
        })}
      </Card>

      <Card>
        <SectionTitle>{t('insights.duesTitle')}</SectionTitle>
        {pendingDues.length === 0 ? (
          <Muted>{t('insights.allPaid')}</Muted>
        ) : (
          <Muted>{tn('insights.duesCount', pendingDues.length)}</Muted>
        )}
        {pendingDues.slice(0, duesShown).map((d) => (
          <View key={`${d.chitId}-${d.memberId}-${d.month}`} style={styles.listRow}>
            <Row style={{ justifyContent: 'space-between' }}>
              <Text style={styles.rowTitle}>{d.memberName}</Text>
              <Text style={{ fontWeight: font.semibold, color: colors.text }}>{formatRupees(d.amount)}</Text>
            </Row>
            <Row style={{ justifyContent: 'space-between' }}>
              <Muted>
                {d.chitName} · {calendarLabel(d.calendarMonth)}
              </Muted>
              {d.overdue ? (
                <Pill label={t('insights.daysOverdue', { n: d.daysOverdue })} tone="loss" />
              ) : (
                <Pill label={t('insights.dueThisMonth')} tone="warning" />
              )}
            </Row>
          </View>
        ))}
        {pendingDues.length > duesShown ? (
          <Button
            variant="ghost"
            label={t('insights.showMore', { n: pendingDues.length - duesShown })}
            onPress={() => setDuesShown((n) => n + DUES_PAGE)}
          />
        ) : null}
      </Card>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  content: { padding: space.lg, gap: space.lg, paddingBottom: space.xxl * 2 },
  hero: { fontSize: 34, fontWeight: font.bold },
  tiles: { flexDirection: 'row', flexWrap: 'wrap', gap: space.md },
  listRow: { borderTopWidth: 1, borderTopColor: colors.border, paddingTop: space.sm, gap: space.xs },
  rowTitle: { flex: 1, fontSize: font.md, fontWeight: font.semibold, color: colors.text },
});
