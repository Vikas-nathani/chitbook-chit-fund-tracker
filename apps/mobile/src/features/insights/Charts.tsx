/**
 * Lightweight bar charts built from Views (no native chart dependency, same on phones and web).
 * Bars scroll horizontally; amounts use compact Indian units (₹12K, ₹2.5L).
 */
import { ScrollView, StyleSheet, Text, View } from 'react-native';

import { calendarLabel, formatCompactRupees } from '@/lib/format';
import { colors, font, space } from '@/theme';

const PLOT = 140;
const BAR = 18;

/** Profit/loss per month: green bars up, red bars down from a zero line. */
export function PnlChart({ points, label }: { points: { month: string; pnl: number; cumulative: number }[]; label: string }) {
  const max = Math.max(1, ...points.map((p) => Math.abs(p.pnl)));
  const half = PLOT / 2;
  return (
    <ScrollView horizontal showsHorizontalScrollIndicator={false} accessibilityLabel={label}>
      <View style={styles.chart}>
        {points.map((p) => {
          const h = Math.max(2, (Math.abs(p.pnl) / max) * (half - 14));
          const up = p.pnl >= 0;
          return (
            <View key={p.month} style={styles.col}>
              <View style={{ height: PLOT, justifyContent: 'center' }}>
                <View style={{ height: half, justifyContent: 'flex-end' }}>
                  {up ? <View style={[styles.bar, { height: h, backgroundColor: colors.profit }]} /> : null}
                </View>
                <View style={styles.zero} />
                <View style={{ height: half }}>
                  {!up ? <View style={[styles.bar, { height: h, backgroundColor: colors.loss }]} /> : null}
                </View>
              </View>
              <Text style={styles.value}>{p.pnl === 0 ? '–' : formatCompactRupees(p.pnl)}</Text>
              <Text style={styles.label}>{calendarLabel(p.month)}</Text>
              <Text style={[styles.value, { color: colors.primary }]}>{formatCompactRupees(p.cumulative)}</Text>
            </View>
          );
        })}
      </View>
    </ScrollView>
  );
}

/** Due vs collected per month: grey bar = due, purple overlay = collected. */
export function CollectionsChart({
  points,
  label,
}: {
  points: { month: string; due: number; collected: number }[];
  label: string;
}) {
  const max = Math.max(1, ...points.map((p) => Math.max(p.due, p.collected)));
  return (
    <ScrollView horizontal showsHorizontalScrollIndicator={false} accessibilityLabel={label}>
      <View style={styles.chart}>
        {points.map((p) => (
          <View key={p.month} style={styles.col}>
            <View style={{ height: PLOT, justifyContent: 'flex-end' }}>
              <View style={[styles.bar, { height: (p.due / max) * PLOT, backgroundColor: colors.surfaceMuted }]}>
                <View
                  style={{
                    position: 'absolute',
                    bottom: 0,
                    left: 0,
                    right: 0,
                    height: (Math.min(p.collected, p.due || p.collected) / max) * PLOT,
                    backgroundColor: colors.primary,
                    borderRadius: 4,
                  }}
                />
              </View>
            </View>
            <Text style={styles.value}>{formatCompactRupees(p.collected)}</Text>
            <Text style={styles.label}>{calendarLabel(p.month)}</Text>
          </View>
        ))}
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  chart: { flexDirection: 'row', gap: space.sm, paddingVertical: space.sm },
  col: { width: BAR + 34, alignItems: 'center', gap: 2 },
  bar: { width: BAR, borderRadius: 4, alignSelf: 'center' },
  zero: { height: 1, backgroundColor: colors.border, alignSelf: 'stretch' },
  value: { fontSize: 10, color: colors.textMuted, fontWeight: font.medium },
  label: { fontSize: font.xs, color: colors.text },
});
