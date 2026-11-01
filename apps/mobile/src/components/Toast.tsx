/** Short confirmation messages ("Saved 3 changes") shown at the bottom of the screen. */
import { createContext, useCallback, useContext, useRef, useState, type ReactNode } from 'react';
import { StyleSheet, Text, View } from 'react-native';

import { colors, font, radius, space } from '@/theme';

type Tone = 'success' | 'error' | 'info';
type ToastFn = (message: string, tone?: Tone) => void;

const ToastContext = createContext<ToastFn>(() => {});

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toast, setToast] = useState<{ message: string; tone: Tone } | null>(null);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const show = useCallback<ToastFn>((message, tone = 'success') => {
    if (timer.current) clearTimeout(timer.current);
    setToast({ message, tone });
    timer.current = setTimeout(() => setToast(null), 3000);
  }, []);

  return (
    <ToastContext.Provider value={show}>
      {children}
      {toast ? (
        <View pointerEvents="none" style={styles.wrap}>
          <View
            accessibilityLiveRegion="polite"
            accessibilityRole="alert"
            style={[styles.toast, { backgroundColor: { success: colors.text, error: colors.loss, info: colors.primary }[toast.tone] }]}
          >
            <Text style={styles.text}>{toast.message}</Text>
          </View>
        </View>
      ) : null}
    </ToastContext.Provider>
  );
}

export const useToast = () => useContext(ToastContext);

const styles = StyleSheet.create({
  wrap: { position: 'absolute', left: 0, right: 0, bottom: space.xxl * 2, alignItems: 'center' },
  toast: { borderRadius: radius.pill, paddingHorizontal: space.xl, paddingVertical: space.md, maxWidth: '90%' },
  text: { color: '#fff', fontSize: font.md, fontWeight: font.medium },
});
