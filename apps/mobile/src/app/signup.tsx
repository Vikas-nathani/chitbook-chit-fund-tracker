import { useState } from 'react';

import { useAuth } from '@/auth/AuthProvider';
import { useToast } from '@/components/Toast';
import { Button, Card, ErrorBanner, Field, Muted, Screen } from '@/components/ui';
import { useI18n } from '@/i18n';

// Same rules as the API (apps/api/src/chitbook_api/modules/users/schemas.py, core/security.py)
const USERNAME = /^[A-Za-z0-9._-]{3,30}$/;
const PHONE = /^\+?[0-9]{10,15}$/;
const strongEnough = (p: string) => p.length >= 8 && /[A-Za-z]/.test(p) && /[0-9]/.test(p);

export default function SignupScreen() {
  const { signUp } = useAuth();
  const toast = useToast();
  const { t, tError } = useI18n();
  const [form, setForm] = useState({ name: '', username: '', phone: '', email: '', password: '', confirm: '' });
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const set = (key: keyof typeof form) => (value: string) => setForm((f) => ({ ...f, [key]: value }));

  async function submit() {
    setError('');
    const { name, username, phone, email, password, confirm } = form;
    if (!name.trim() || !username.trim() || !email.trim() || !password) return setError(t('signup.missing'));
    if (!USERNAME.test(username.trim())) return setError(t('signup.usernameInvalid'));
    if (phone.trim() && !PHONE.test(phone.trim())) return setError(t('signup.phoneInvalid'));
    if (!strongEnough(password)) return setError(t('signup.passwordWeak'));
    if (password !== confirm) return setError(t('signup.mismatch'));
    setBusy(true);
    try {
      await signUp({
        name: name.trim(),
        username: username.trim(),
        email: email.trim(),
        phone: phone.trim() || undefined,
        password,
      });
      toast(t('signup.welcome'));
    } catch (err) {
      setError(tError(err));
      setBusy(false);
    }
  }

  return (
    <Screen>
      <Card>
        <Muted>{t('signup.subtitle')}</Muted>
        <ErrorBanner message={error} />
        <Field label={t('signup.fullName')} placeholder={t('signup.fullNamePh')} value={form.name} onChangeText={set('name')} autoComplete="name" />
        <Field
          label={t('signup.username')}
          placeholder={t('signup.usernamePh')}
          value={form.username}
          onChangeText={set('username')}
          autoCapitalize="none"
          autoCorrect={false}
          autoComplete="username-new"
        />
        <Field
          label={t('signup.phone')}
          hint={t('common.optional')}
          placeholder={t('signup.phonePh')}
          value={form.phone}
          onChangeText={set('phone')}
          keyboardType="phone-pad"
          autoComplete="tel"
        />
        <Field
          label={t('signup.email')}
          placeholder={t('signup.emailPh')}
          value={form.email}
          onChangeText={set('email')}
          keyboardType="email-address"
          autoCapitalize="none"
          autoComplete="email"
        />
        <Field
          label={t('signup.password')}
          placeholder={t('signup.passwordPh')}
          value={form.password}
          onChangeText={set('password')}
          secureTextEntry
          autoComplete="new-password"
          textContentType="newPassword"
        />
        <Field
          label={t('signup.confirm')}
          placeholder={t('signup.confirmPh')}
          value={form.confirm}
          onChangeText={set('confirm')}
          secureTextEntry
          autoComplete="new-password"
          onSubmitEditing={submit}
        />
        <Button label={busy ? t('signup.submitting') : t('signup.submit')} onPress={submit} busy={busy} />
      </Card>
    </Screen>
  );
}
