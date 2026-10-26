import { useState, type FormEvent } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../auth';
import { AuthShell } from '../components/AuthShell';
import { useI18n } from '../i18n';

export function Login() {
  const { login } = useAuth();
  const { t, tError } = useI18n();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError('');
    if (!username.trim() || !password) return setError(t('login.missing'));
    setBusy(true);
    try {
      await login(username, password);
    } catch (err) {
      setError((err as Error).message);
      setBusy(false);
    }
  }

  return (
    <AuthShell title={t('login.title')} subtitle={t('login.subtitle')}>
      <form className="form" onSubmit={onSubmit} noValidate>
        <label className="field">
          <span>{t('login.username')}</span>
          <input
            autoFocus
            name="username"
            autoComplete="username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder={t('login.usernamePh')}
          />
        </label>
        <label className="field">
          <span>{t('login.password')}</span>
          <input
            type="password"
            name="password"
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder={t('login.passwordPh')}
          />
        </label>
        {error && <div className="alert alert-error">{tError(error)}</div>}
        <button type="submit" className="btn btn-primary btn-block" disabled={busy}>
          {busy ? t('login.submitting') : t('login.submit')}
        </button>
      </form>
      <p className="auth-switch">
        {t('login.newHere')} <Link to="/signup">{t('login.createAccount')}</Link>
      </p>
    </AuthShell>
  );
}
