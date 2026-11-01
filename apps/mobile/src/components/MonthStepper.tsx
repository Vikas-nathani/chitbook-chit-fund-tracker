/** ◀ Nov 2026 ▶ picker for a calendar month (yyyy-MM), with optional bounds. */
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { intlLocale } from '@/i18n';
import { TOUCH, colors, font, radius } from '@/theme';

export function shiftMonth(yearMonth: string, delta: number): string {
  const [y, m] = yearMonth.split('-').map(Number) as [number, number];
  const d = new Date(y, m - 1 + delta, 1);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
}

function label(yearMonth: string) {
  const [y, m] = yearMonth.split('-').map(Number) as [number, number];
  return new Date(y, m - 1, 1).toLocaleString(intlLocale(), { month: 'long', year: 'numeric' });
}

export function MonthStepper({
  value,
  onChange,
  min,
  max,
  accessibilityLabel,
}: {
  value: string;
  onChange: (next: string) => void;
  min?: string;
  max?: string;
  accessibilityLabel: string;
}) {
  const canPrev = !min || value > min;
  const canNext = !max || value < max;
  return (
    <View style={styles.wrap} accessibilityLabel={accessibilityLabel}>
      <Pressable
        accessibilityRole="button"
        accessibilityLabel={`${accessibilityLabel}: previous month`}
        disabled={!canPrev}
        onPress={() => onChange(shiftMonth(value, -1))}
        style={[styles.step, !canPrev && { opacity: 0.3 }]}
      >
        <Text style={styles.arrow}>◀</Text>
      </Pressable>
      <Text style={styles.value}>{label(value)}</Text>
      <Pressable
        accessibilityRole="button"
        accessibilityLabel={`${accessibilityLabel}: next month`}
        disabled={!canNext}
        onPress={() => onChange(shiftMonth(value, 1))}
        style={[styles.step, !canNext && { opacity: 0.3 }]}
      >
        <Text style={styles.arrow}>▶</Text>
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    flexDirection: 'row',
    alignItems: 'center',
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.md,
    backgroundColor: colors.surface,
  },
  step: { width: TOUCH, height: TOUCH, alignItems: 'center', justifyContent: 'center' },
  arrow: { color: colors.primary, fontSize: font.md },
  value: { flex: 1, textAlign: 'center', fontSize: font.md, fontWeight: font.semibold, color: colors.text },
});
