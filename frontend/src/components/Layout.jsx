import { NavLink, Outlet } from 'react-router-dom';
import { LayoutDashboard, Briefcase, Activity } from 'lucide-react';

export default function Layout() {
  return (
    <div className="app-layout">
      <aside className="sidebar">
        <div className="sidebar-logo">
          <h1>VoiceScreen</h1>
          <span>AI-Powered HR Screening</span>
        </div>
        <nav className="sidebar-nav">
          <NavLink to="/" end className={({ isActive }) => `sidebar-link ${isActive ? 'active' : ''}`}>
            <LayoutDashboard />
            Dashboard
          </NavLink>
          <NavLink to="/jobs" className={({ isActive }) => `sidebar-link ${isActive ? 'active' : ''}`}>
            <Briefcase />
            Jobs
          </NavLink>
        </nav>
        <div style={{ padding: 'var(--space-4) var(--space-5)', borderTop: '1px solid var(--border-subtle)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)' }}>
            <Activity size={16} style={{ color: 'var(--success)' }} />
            <span style={{ fontSize: 'var(--font-xs)', color: 'var(--text-muted)' }}>
              Powered by Bolna AI
            </span>
          </div>
        </div>
      </aside>
      <main className="main-content">
        <Outlet />
      </main>
    </div>
  );
}
