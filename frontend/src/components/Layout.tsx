import { Link, NavLink, Outlet } from 'react-router-dom';
import { useAuth } from '../auth';
import { avatarColor, initials } from '../format';
import { useI18n } from '../i18n';
import { LangSwitch } from './LangSwitch';

export function Brand() {
  return (
    <span className="brand">
      <span className="brand-mark">₹</span>
      <span className="brand-name">ChitBook</span>
    </span>
  );
}

export function Layout() {
  const { session, logout } = useAuth();
  const { t } = useI18n();
  const user = session!.user;

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="topbar-inner">
          <div className="topbar-left">
            <Link to="/" className="brand-link">
              <Brand />
            </Link>
            <nav className="topnav">
              <NavLink to="/" end className={({ isActive }) => (isActive ? 'is-active' : '')}>
                {t('nav.chits')}
              </NavLink>
              <NavLink to="/insights" className={({ isActive }) => (isActive ? 'is-active' : '')}>
                {t('nav.insights')}
              </NavLink>
            </nav>
          </div>
          <div className="topbar-right">
            <LangSwitch tone="dark" />
            <div className="user-chip" title={user.email}>
              <span className="avatar avatar-sm" style={{ background: avatarColor(user.name || user.username) }}>
                {initials(user.name || user.username)}
              </span>
              <span className="user-chip-text">
                <span className="user-chip-name">{user.name || user.username}</span>
                {user.role === 'ADMIN' && <span className="role-badge">{t('common.admin')}</span>}
              </span>
            </div>
            <button className="btn btn-ghost-light btn-logout" onClick={logout} title={t('common.logout')} aria-label={t('common.logout')}>
              <span className="logout-text">{t('common.logout')}</span>
              <span className="logout-icon" aria-hidden>
                ⏻
              </span>
            </button>
          </div>
        </div>
      </header>
      <main className="page">
        <Outlet />
      </main>
    </div>
  );
}
