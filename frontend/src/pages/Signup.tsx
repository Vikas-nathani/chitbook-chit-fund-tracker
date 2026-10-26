import { useState, type FormEvent } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api';
import { useAuth } from '../auth';
import { AuthShell } from '../components/AuthShell';
import { useI18n } from '../i18n';
import { useToast } from '../toast';

export function Signup() {
  const { login } = useAuth();
  const { t, tError } = useI18n();
  const toast = useToast();
  const [form, setForm] = useState({ name: '', username: '', email: '', phone: '', password: '', confirm: '' });
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const set = (key: keyof typeof form) => (e: { target: { value: string } }) =>
    setForm((f) => ({ ...f, [key]: e.target.value }));

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError('');
    if (!form.name.trim() || !form.username.trim() || !form.email.trim() || !form.password) {
      return setError(t('signup.missing'));
    }
    if (form.password !== form.confirm) return setError(t('signup.mismatch'));
    const phoneDigits = form.phone.replace(/\D/g, '');
    if (phoneDigits && phoneDigits.length !== 10) return setError(t('signup.phoneInvalid'));
    setBusy(true);
    try {
      await api.signup({
        name: form.name.trim(),
        username: form.username.trim(),
        email: form.email.trim(),
        phone: phoneDigits ? Number(phoneDigits) : undefined,
        password: form.password,
      });
      await login(form.username, form.password);
      toast(t('signup.welcome'));
    } catch (err) {
      setError((err as Error).message);
      setBusy(false);
    }
  }

  return (
    <AuthShell title={t('signup.title')} subtitle={t('signup.subtitle')}>
      <form className="form" onSubmit={onSubmit} noValidate>
        <label className="field">
          <span>{t('signup.fullName')}</span>
          <input autoFocus name="name" value={form.name} onChange={set('name')} placeholder={t('signup.fullNamePh')} />
        </label>
        <div className="form-row">
          <label className="field">
            <span>{t('signup.username')}</span>
            <input
              name="username"
              autoComplete="username"
              value={form.username}
              onChange={set('username')}
              maxLength={15}
              placeholder={t('signup.usernamePh')}
            />
          </label>
          <label className="field">
            <span>
              {t('signup.phone')} <em className="optional">{t('common.optional')}</em>
            </span>
            <input name="phone" inputMode="numeric" value={form.phone} onChange={set('phone')} placeholder={t('signup.phonePh')} />
          </label>
        </div>
        <label className="field">
          <span>{t('signup.email')}</span>
          <input
            type="email"
            name="email"
            autoComplete="email"
            value={form.email}
            onChange={set('email')}
            placeholder={t('signup.emailPh')}
          />
        </label>
        <div className="form-row">
          <label className="field">
            <span>{t('signup.password')}</span>
            <input
              type="password"
              name="password"
              autoComplete="new-password"
              value={form.password}
              onChange={set('password')}
              placeholder={t('signup.passwordPh')}
            />
          </label>
          <label className="field">
            <span>{t('signup.confirm')}</span>
            <input
              type="password"
              name="confirm"
              autoComplete="new-password"
              value={form.confirm}
              onChange={set('confirm')}
              placeholder={t('signup.confirmPh')}
            />
          </label>
        </div>
        {error && <div className="alert alert-error">{tError(error)}</div>}
        <button type="submit" className="btn btn-primary btn-block" disabled={busy}>
          {busy ? t('signup.submitting') : t('signup.submit')}
        </button>
      </form>
      <p className="auth-switch">
        {t('signup.haveAccount')} <Link to="/login">{t('signup.login')}</Link>
      </p>
    </AuthShell>
  );
}
