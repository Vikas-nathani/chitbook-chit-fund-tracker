/** Small UI kit used by every screen. Keep styling here, not in screens. */
import type { ReactNode } from 'react';
import {
  ActivityIndicator,
  Modal,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
  type StyleProp,
  type TextInputProps,
  type TextStyle,
  type ViewStyle,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { avatarColor, initials } from '@/lib/format';
import { TOUCH, colors, font, radius, shadow, space } from '@/theme';

// ---------------------------------------------------------------- layout

export function Screen({ children, scroll = true }: { children: ReactNode; scroll?: boolean }) {
  return (
    <SafeAreaView style={styles.screen} edges={['left', 'right']}>
      {scroll ? (
        <ScrollView contentContainerStyle={styles.screenContent} keyboardShouldPersistTaps="handled">
          {children}
        </ScrollView>
      ) : (
        <View style={[styles.screenContent, { flex: 1 }]}>{children}</View>
      )}
    </SafeAreaView>
  );
}

export function Card({ children, style }: { children: ReactNode; style?: StyleProp<ViewStyle> }) {
  return <View style={[styles.card, style]}>{children}</View>;
}

export function Row({ children, style }: { children: ReactNode; style?: StyleProp<ViewStyle> }) {
  return <View style={[styles.row, style]}>{children}</View>;
}

// ---------------------------------------------------------------- text

export function Title({ children }: { children: ReactNode }) {
  return <Text style={styles.title}>{children}</Text>;
}

export function Eyebrow({ children }: { children: ReactNode }) {
  return <Text style={styles.eyebrow}>{children}</Text>;
}

export function Muted({ children, style }: { children: ReactNode; style?: StyleProp<TextStyle> }) {
  return <Text style={[styles.muted, style]}>{children}</Text>;
}

export function SectionTitle({ children }: { children: ReactNode }) {
  return <Text style={styles.sectionTitle}>{children}</Text>;
}

// ---------------------------------------------------------------- controls

type ButtonVariant = 'primary' | 'secondary' | 'danger' | 'ghost';

export function Button({
  label,
  onPress,
  variant = 'primary',
  disabled,
  busy,
  style,
  accessibilityLabel,
}: {
  label: string;
  onPress: () => void;
  variant?: ButtonVariant;
  disabled?: boolean;
  busy?: boolean;
  style?: StyleProp<ViewStyle>;
  accessibilityLabel?: string;
}) {
  const inactive = disabled || busy;
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={accessibilityLabel ?? label}
      accessibilityState={{ disabled: !!inactive, busy: !!busy }}
      onPress={onPress}
      disabled={inactive}
      style={({ pressed }) => [
        styles.button,
        buttonVariants[variant],
        pressed && { opacity: 0.85 },
        inactive && { opacity: 0.5 },
        style,
      ]}
    >
      {busy ? (
        <ActivityIndicator color={variant === 'primary' || variant === 'danger' ? colors.onPrimary : colors.primary} />
      ) : (
        <Text style={[styles.buttonText, buttonTextVariants[variant]]}>{label}</Text>
      )}
    </Pressable>
  );
}

export function Field({
  label,
  hint,
  error,
  style,
  ...input
}: TextInputProps & { label: string; hint?: string; error?: boolean; style?: StyleProp<ViewStyle> }) {
  return (
    <View style={[styles.field, style]}>
      <Text style={styles.fieldLabel}>
        {label}
        {hint ? <Text style={styles.muted}> · {hint}</Text> : null}
      </Text>
      <TextInput
        accessibilityLabel={label}
        placeholderTextColor={colors.pending}
        style={[styles.input, error && { borderColor: colors.loss }]}
        {...input}
      />
    </View>
  );
}

export function Toggle({ label, value, onChange }: { label: string; value: boolean; onChange: (v: boolean) => void }) {
  return (
    <Pressable
      accessibilityRole="switch"
      accessibilityState={{ checked: value }}
      onPress={() => onChange(!value)}
      style={styles.toggleRow}
    >
      <View style={[styles.toggleBox, value && { backgroundColor: colors.primary, borderColor: colors.primary }]}>
        {value ? <Text style={{ color: colors.onPrimary, fontWeight: font.bold }}>✓</Text> : null}
      </View>
      <Text style={{ flex: 1, color: colors.text, fontSize: font.md }}>{label}</Text>
    </Pressable>
  );
}

export function Chip({ label, active, onPress }: { label: string; active?: boolean; onPress: () => void }) {
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityState={{ selected: !!active }}
      onPress={onPress}
      style={[styles.chip, active && { backgroundColor: colors.primary, borderColor: colors.primary }]}
    >
      <Text style={{ color: active ? colors.onPrimary : colors.text, fontWeight: font.medium }}>{label}</Text>
    </Pressable>
  );
}

// ---------------------------------------------------------------- data display

export function StatTile({
  label,
  value,
  sub,
  tone = 'indigo',
  onPress,
}: {
  label: string;
  value: string;
  sub?: string;
  tone?: keyof typeof colors.tiles;
  onPress?: () => void;
}) {
  const body = (
    <View style={[styles.tile, { backgroundColor: colors.tiles[tone] }]}>
      <Text style={styles.tileLabel}>{label}</Text>
      <Text style={styles.tileValue} numberOfLines={1} adjustsFontSizeToFit>
        {value}
      </Text>
      {sub ? <Text style={styles.tileSub}>{sub}</Text> : null}
    </View>
  );
  return onPress ? (
    <Pressable accessibilityRole="button" onPress={onPress} style={styles.tileWrap}>
      {body}
    </Pressable>
  ) : (
    <View style={styles.tileWrap}>{body}</View>
  );
}

export function ProgressBar({ ratio, label }: { ratio: number; label?: string }) {
  const pct = Math.max(0, Math.min(ratio, 1)) * 100;
  return (
    <View
      style={styles.progress}
      accessibilityRole="progressbar"
      accessibilityLabel={label}
      accessibilityValue={{ min: 0, max: 100, now: Math.round(pct) }}
    >
      <View style={[styles.progressFill, { width: `${pct}%` }]} />
    </View>
  );
}

export function Avatar({ name, size = 36 }: { name: string; size?: number }) {
  return (
    <View
      style={{
        width: size,
        height: size,
        borderRadius: size / 2,
        backgroundColor: avatarColor(name),
        alignItems: 'center',
        justifyContent: 'center',
      }}
    >
      <Text style={{ color: '#fff', fontWeight: font.bold, fontSize: size * 0.38 }}>{initials(name)}</Text>
    </View>
  );
}

export function Pill({ label, tone = 'muted' }: { label: string; tone?: 'muted' | 'profit' | 'loss' | 'warning' }) {
  const bg = { muted: colors.surfaceMuted, profit: colors.profitSoft, loss: colors.lossSoft, warning: colors.warningSoft }[tone];
  const fg = { muted: colors.textMuted, profit: colors.profit, loss: colors.loss, warning: colors.warning }[tone];
  return (
    <View style={[styles.pill, { backgroundColor: bg }]}>
      <Text style={{ color: fg, fontSize: font.xs, fontWeight: font.semibold }}>{label}</Text>
    </View>
  );
}

export function ErrorBanner({ message }: { message: string }) {
  if (!message) return null;
  return (
    <View style={styles.errorBanner} accessibilityRole="alert">
      <Text style={{ color: colors.loss }}>{message}</Text>
    </View>
  );
}

export function EmptyState({ title, text, action }: { title: string; text: string; action?: ReactNode }) {
  return (
    <Card style={{ alignItems: 'center', gap: space.md, paddingVertical: space.xxl }}>
      <Text style={{ fontSize: 40 }}>₹</Text>
      <Text style={styles.sectionTitle}>{title}</Text>
      <Muted style={{ textAlign: 'center' }}>{text}</Muted>
      {action}
    </Card>
  );
}

export function Loading() {
  return (
    <View style={{ padding: space.xxl, alignItems: 'center' }}>
      <ActivityIndicator color={colors.primary} size="large" />
    </View>
  );
}

// ---------------------------------------------------------------- overlays

/** Bottom sheet dialog (works the same on phones and web). */
export function Sheet({
  visible,
  title,
  onClose,
  children,
}: {
  visible: boolean;
  title: string;
  onClose: () => void;
  children: ReactNode;
}) {
  return (
    <Modal visible={visible} transparent animationType="slide" onRequestClose={onClose}>
      <Pressable style={styles.overlay} onPress={onClose} accessibilityLabel="Close" />
      <View style={styles.sheet}>
        <Text style={styles.sectionTitle}>{title}</Text>
        <ScrollView keyboardShouldPersistTaps="handled" contentContainerStyle={{ gap: space.md }}>
          {children}
        </ScrollView>
      </View>
    </Modal>
  );
}

// ---------------------------------------------------------------- styles

const buttonVariants: Record<ButtonVariant, ViewStyle> = {
  primary: { backgroundColor: colors.primary },
  secondary: { backgroundColor: colors.primarySoft },
  danger: { backgroundColor: colors.loss },
  ghost: { backgroundColor: 'transparent' },
};
const buttonTextVariants: Record<ButtonVariant, TextStyle> = {
  primary: { color: colors.onPrimary },
  secondary: { color: colors.primary },
  danger: { color: colors.onPrimary },
  ghost: { color: colors.primary },
};

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.bg },
  screenContent: { padding: space.lg, gap: space.lg, paddingBottom: space.xxl * 2 },
  card: { backgroundColor: colors.surface, borderRadius: radius.lg, padding: space.lg, gap: space.sm, ...shadow },
  row: { flexDirection: 'row', alignItems: 'center', gap: space.sm },
  title: { fontSize: font.xxl, fontWeight: font.bold, color: colors.text },
  eyebrow: { fontSize: font.sm, color: colors.textMuted, fontWeight: font.medium },
  muted: { color: colors.textMuted, fontSize: font.sm },
  sectionTitle: { fontSize: font.lg, fontWeight: font.semibold, color: colors.text },
  button: {
    minHeight: TOUCH,
    borderRadius: radius.md,
    paddingHorizontal: space.lg,
    alignItems: 'center',
    justifyContent: 'center',
  },
  buttonText: { fontSize: font.md, fontWeight: font.semibold },
  field: { gap: space.xs },
  fieldLabel: { fontSize: font.sm, fontWeight: font.medium, color: colors.text },
  input: {
    minHeight: TOUCH,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.md,
    paddingHorizontal: space.md,
    fontSize: font.md,
    color: colors.text,
    backgroundColor: colors.surface,
  },
  toggleRow: { flexDirection: 'row', alignItems: 'center', gap: space.md, minHeight: TOUCH },
  toggleBox: {
    width: 26,
    height: 26,
    borderRadius: radius.sm,
    borderWidth: 2,
    borderColor: colors.border,
    alignItems: 'center',
    justifyContent: 'center',
  },
  chip: {
    minHeight: 36,
    paddingHorizontal: space.md,
    borderRadius: radius.pill,
    borderWidth: 1,
    borderColor: colors.border,
    justifyContent: 'center',
    backgroundColor: colors.surface,
  },
  tileWrap: { flexBasis: '47%', flexGrow: 1 },
  tile: { borderRadius: radius.lg, padding: space.lg, gap: space.xs, minHeight: 96 },
  tileLabel: { fontSize: font.sm, color: colors.textMuted, fontWeight: font.medium },
  tileValue: { fontSize: font.xl, fontWeight: font.bold, color: colors.text },
  tileSub: { fontSize: font.xs, color: colors.textMuted },
  progress: { height: 8, borderRadius: radius.pill, backgroundColor: colors.surfaceMuted, overflow: 'hidden' },
  progressFill: { height: '100%', backgroundColor: colors.primary, borderRadius: radius.pill },
  pill: { paddingHorizontal: space.sm, paddingVertical: 2, borderRadius: radius.pill, alignSelf: 'flex-start' },
  errorBanner: { backgroundColor: colors.lossSoft, borderRadius: radius.md, padding: space.md },
  overlay: { flex: 1, backgroundColor: colors.overlay },
  sheet: {
    backgroundColor: colors.surface,
    borderTopLeftRadius: radius.lg,
    borderTopRightRadius: radius.lg,
    padding: space.xl,
    gap: space.md,
    maxHeight: '85%',
  },
});
