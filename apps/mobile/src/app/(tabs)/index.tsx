import { router } from 'expo-router';
import { Pressable, RefreshControl, ScrollView, StyleSheet, Text, View } from 'react-native';

import type { ChitSummary } from '@/api/types';
import { useAuth } from '@/auth/AuthProvider';
import { Button, EmptyState, ErrorBanner, Eyebrow, Loading, Muted, Pill, ProgressBar, Row, StatTile, Title } from '@/components/ui';
import { useChits } from '@/features/chits/hooks';
import { useI18n } from '@/i18n';
import { currentMonthIndex, formatRupees, formatSignedRupees, periodLabel, round2 } from '@/lib/format';
import { colors, font, radius, shadow, space } from '@/theme';

export default function DashboardScreen() {
  const { user } = useAuth();
  const { t, tError } = useI18n();
  const { data: chits, error, isLoading, refetch, isRefetching } = useChits();

  const firstName = (user?.name || user?.username || '').split(' ')[0] ?? '';
  const hour = new Date().getHours();
  const greetingKey = hour < 12 ? 'dashboard.morning' : hour < 17 ? 'dashboard.afternoon' : 'dashboard.evening';
  const sum = (f: (c: ChitSummary) => number) => round2(chits?.reduce((total, c) => total + f(c), 0) ?? 0);
  const totalOverdue = sum((c) => c.overdue);
  const totalProfit = sum((c) => c.profit);

  return (
    <ScrollView
      contentContainerStyle={styles.content}
      refreshControl={<RefreshControl refreshing={isRefetching} onRefresh={() => void refetch()} />}
    >
      <View>
        <Eyebrow>{t(greetingKey, { name: firstName })}</Eyebrow>
        <Title>{t('dashboard.title')}</Title>
      </View>
      <Button label={`+ ${t('dashboard.newChit')}`} onPress={() => router.push('/chits/new')} />

      <View style={styles.tiles}>
        <StatTile label={t('dashboard.activeChits')} value={String(chits?.length ?? '–')} tone="indigo" />
        <StatTile label={t('dashboard.collected')} value={formatRupees(sum((c) => c.collected))} tone="violet" />
        <StatTile
          label={t('dashboard.pendingDues')}
          value={formatRupees(sum((c) => c.pending))}
          sub={totalOverdue > 0 ? t('dashboard.overdueSub', { amount: formatRupees(totalOverdue) }) : undefined}
          tone="amber"
        />
        <StatTile
          label={t('dashboard.profit')}
          value={formatSignedRupees(totalProfit)}
          sub={t('dashboard.seeInsights')}
          tone={totalProfit < 0 ? 'rose' : 'emerald'}
          onPress={() => router.push('/insights')}
        />
      </View>

      {error ? <ErrorBanner message={tError(error)} /> : null}
      {isLoading ? <Loading /> : null}

      {chits?.length === 0 ? (
        <EmptyState
          title={t('dashboard.emptyTitle')}
          text={t('dashboard.emptyText')}
          action={<Button label={t('dashboard.emptyCta')} onPress={() => router.push('/chits/new')} />}
        />
      ) : null}

      {chits?.map((chit, i) => <ChitCard key={chit.id} chit={chit} accent={colors.accents[i % colors.accents.length]!} />)}
    </ScrollView>
  );
}

function ChitCard({ chit, accent }: { chit: ChitSummary; accent: string }) {
  const { t } = useI18n();
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
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={chit.name}
      onPress={() => router.push(`/chits/${chit.id}`)}
      style={({ pressed }) => [styles.card, { borderLeftColor: accent }, pressed && { opacity: 0.9 }]}
    >
      <Row style={{ justifyContent: 'space-between' }}>
        <Text style={styles.cardTitle} numberOfLines={1}>
          {chit.name}
        </Text>
        <Pill label={status} />
      </Row>
      <Text style={styles.amount}>{formatRupees(chit.totalAmount)}</Text>
      <Muted>
        👥 {t('dashboard.members', { n: chit.memberCount })} · 🗓 {t('dashboard.months', { n: chit.months })}
      </Muted>
      <Row style={{ justifyContent: 'space-between' }}>
        <Text style={{ color: colors.text }}>
          {t('dashboard.collectedAmount')} <Text style={{ fontWeight: font.bold }}>{formatRupees(chit.collected)}</Text>
        </Text>
        <Muted>{chit.dueToDate > 0 ? t('dashboard.pctOfDue', { pct }) : t('dashboard.nothingDue')}</Muted>
      </Row>
      <ProgressBar ratio={rate} label={t('dashboard.progressAria', { pct })} />
      <Row style={{ justifyContent: 'space-between' }}>
        <Muted>{periodLabel(chit.startMonth, chit.months)}</Muted>
        <Text style={{ color: chit.profit < 0 ? colors.loss : chit.profit > 0 ? colors.profit : colors.textMuted }}>
          {t('dashboard.pl')} <Text style={{ fontWeight: font.bold }}>{formatSignedRupees(chit.profit)}</Text>
        </Text>
      </Row>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  content: { padding: space.lg, gap: space.lg, paddingBottom: space.xxl * 2 },
  tiles: { flexDirection: 'row', flexWrap: 'wrap', gap: space.md },
  card: {
    backgroundColor: colors.surface,
    borderRadius: radius.lg,
    padding: space.lg,
    gap: space.sm,
    borderLeftWidth: 5,
    ...shadow,
  },
  cardTitle: { flex: 1, fontSize: font.lg, fontWeight: font.semibold, color: colors.text },
  amount: { fontSize: font.xl, fontWeight: font.bold, color: colors.text },
});
