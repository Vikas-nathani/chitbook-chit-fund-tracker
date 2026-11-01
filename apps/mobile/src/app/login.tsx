import { Link } from 'expo-router';
import { useState } from 'react';
import { Text } from 'react-native';

import { useAuth } from '@/auth/AuthProvider';
import { LangSwitch } from '@/components/LangSwitch';
import { Button, Card, ErrorBanner, Field, Muted, Row, Screen, Title } from '@/components/ui';
import { useI18n } from '@/i18n';
import { colors, font } from '@/theme';

export default function LoginScreen() {
  const { signIn } = useAuth();
  const { t, tError } = useI18n();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  async function submit() {
    setError('');
    if (!username.trim() || !password) return setError(t('login.missing'));
    setBusy(true);
    try {
      await signIn(username, password);
    } catch (err) {
      setError(tError(err));
      setBusy(false);
    }
  }

  return (
    <Screen>
      <Row style={{ justifyContent: 'flex-end' }}>
        <LangSwitch />
      </Row>
      <Text style={{ fontSize: font.xxl, fontWeight: font.bold, color: colors.primary }}>ChitBook</Text>
      <Muted>{t('auth.heroTitle')}</Muted>

      <Card>
        <Title>{t('login.title')}</Title>
        <Muted>{t('login.subtitle')}</Muted>
        <ErrorBanner message={error} />
        <Field
          label={t('login.username')}
          placeholder={t('login.usernamePh')}
          value={username}
          onChangeText={setUsername}
          autoCapitalize="none"
          autoCorrect={false}
          autoComplete="username"
          textContentType="username"
        />
        <Field
          label={t('login.password')}
          placeholder={t('login.passwordPh')}
          value={password}
          onChangeText={setPassword}
          secureTextEntry
          autoComplete="current-password"
          textContentType="password"
          onSubmitEditing={submit}
        />
        <Button label={busy ? t('login.submitting') : t('login.submit')} onPress={submit} busy={busy} />
        <Row style={{ justifyContent: 'center' }}>
          <Muted>{t('login.newHere')}</Muted>
          <Link href="/signup" style={{ color: colors.primary, fontWeight: font.semibold }}>
            {t('login.createAccount')}
          </Link>
        </Row>
      </Card>
    </Screen>
  );
}
