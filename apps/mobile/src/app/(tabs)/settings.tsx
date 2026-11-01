import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Text, View } from 'react-native';

import { api } from '@/api/endpoints';
import { useAuth } from '@/auth/AuthProvider';
import { LangSwitch } from '@/components/LangSwitch';
import { useToast } from '@/components/Toast';
import { Button, Card, ErrorBanner, Loading, Muted, Pill, Row, Screen, SectionTitle } from '@/components/ui';
import { intlLocale, useI18n } from '@/i18n';
import { colors, font } from '@/theme';

const when = (iso: string | null | undefined) =>
  iso ? new Date(iso).toLocaleString(intlLocale(), { dateStyle: 'medium', timeStyle: 'short' }) : '–';

export default function SettingsScreen() {
  const { user, signOut } = useAuth();
  const { t, tError } = useI18n();
  const toast = useToast();
  const qc = useQueryClient();
  const sessions = useQuery({ queryKey: ['sessions'], queryFn: api.sessions });
  const revoke = useMutation({
    mutationFn: api.revokeSession,
    onSuccess: () => {
      toast(t('settings.deviceSignedOut'));
      void qc.invalidateQueries({ queryKey: ['sessions'] });
    },
    onError: (err) => toast(tError(err), 'error'),
  });

  return (
    <Screen>
      <Card>
        <SectionTitle>{t('settings.account')}</SectionTitle>
        <Text style={{ fontSize: font.lg, color: colors.text, fontWeight: font.semibold }}>{user?.name}</Text>
        <Muted>
          @{user?.username} · {user?.email}
        </Muted>
        {user?.role === 'ADMIN' ? <Pill label={t('common.admin')} tone="warning" /> : null}
      </Card>

      <Card>
        <SectionTitle>{t('common.language')}</SectionTitle>
        <LangSwitch />
      </Card>

      <Card>
        <SectionTitle>{t('settings.devices')}</SectionTitle>
        <Muted>{t('settings.devicesHelp')}</Muted>
        {sessions.isLoading ? <Loading /> : null}
        {sessions.error ? <ErrorBanner message={tError(sessions.error)} /> : null}
        {sessions.data?.map((s) => (
          <View key={s.id} style={{ paddingVertical: 8, borderTopWidth: 1, borderTopColor: colors.border, gap: 4 }}>
            <Row style={{ justifyContent: 'space-between' }}>
              <Text style={{ color: colors.text, fontWeight: font.semibold, flex: 1 }}>
                {s.deviceName ?? t('settings.unknownDevice')}
              </Text>
              {s.current ? (
                <Pill label={t('settings.thisDevice')} tone="profit" />
              ) : (
                <Button
                  label={t('settings.signOutDevice')}
                  variant="secondary"
                  onPress={() => revoke.mutate(s.id)}
                  busy={revoke.isPending && revoke.variables === s.id}
                />
              )}
            </Row>
            <Muted>
              {t('settings.lastUsed', { when: when(s.lastUsedAt) })}
              {s.ipAddress ? ` · ${s.ipAddress}` : ''}
            </Muted>
          </View>
        ))}
      </Card>

      <Button label={t('common.logout')} variant="danger" onPress={signOut} />
    </Screen>
  );
}
