import { Tabs } from 'expo-router/js-tabs';
import { Text, type ColorValue } from 'react-native';

import { useI18n } from '@/i18n';
import { colors } from '@/theme';

function TabGlyph({ glyph, color }: { glyph: string; color: ColorValue }) {
  return <Text style={{ color, fontSize: 18 }}>{glyph}</Text>;
}

const icon = (glyph: string) =>
  function TabIcon({ color }: { color: ColorValue }) {
    return <TabGlyph glyph={glyph} color={color} />;
  };

export default function TabsLayout() {
  const { t } = useI18n();
  return (
    <Tabs
      screenOptions={{
        tabBarActiveTintColor: colors.primary,
        tabBarInactiveTintColor: colors.textMuted,
        headerStyle: { backgroundColor: colors.bg },
        headerShadowVisible: false,
        headerTitleStyle: { color: colors.text },
        sceneStyle: { backgroundColor: colors.bg },
      }}
    >
      <Tabs.Screen name="index" options={{ title: t('nav.chits'), tabBarIcon: icon('₹') }} />
      <Tabs.Screen name="insights" options={{ title: t('nav.insights'), tabBarIcon: icon('📈') }} />
      <Tabs.Screen name="settings" options={{ title: t('nav.settings'), tabBarIcon: icon('⚙') }} />
    </Tabs>
  );
}
