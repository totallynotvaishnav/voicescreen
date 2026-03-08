import { NavLink, Outlet } from 'react-router-dom';
import { LayoutDashboard, Briefcase, Activity, LogOut, User } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export default function Layout({ children }) {
  const { user, logout } = useAuth();
  
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
        <div style={{ padding: 'var(--space-4) var(--space-5)', borderTop: '1px solid var(--border-subtle)', display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
          {user && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)', color: 'var(--text-muted)' }}>
              <div style={{ width: 32, height: 32, borderRadius: '50%', background: 'var(--surface-active)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <User size={16} />
              </div>
              <div style={{ flex: 1, overflow: 'hidden' }}>
                <p style={{ fontSize: 'var(--font-sm)', fontWeight: 500, color: 'var(--text)', whiteSpace: 'nowrap', textOverflow: 'ellipsis', overflow: 'hidden' }}>
                  {user.email.split('@')[0]}
                </p>
                <p style={{ fontSize: 'var(--font-xs)', whiteSpace: 'nowrap', textOverflow: 'ellipsis', overflow: 'hidden' }}>
                  Recruiter
                </p>
              </div>
            </div>
          )}
          
          <button 
            onClick={logout}
            style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)', background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', padding: 0, fontSize: 'var(--font-sm)', width: '100%', textAlign: 'left', transition: 'color 0.2s' }}
            onMouseOver={(e) => e.currentTarget.style.color = 'white'}
            onMouseOut={(e) => e.currentTarget.style.color = 'var(--text-muted)'}
          >
            <LogOut size={16} />
            Sign out
          </button>
          
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)', paddingTop: 'var(--space-2)' }}>
            <Activity size={16} style={{ color: 'var(--success)' }} />
            <span style={{ fontSize: 'var(--font-xs)', color: 'var(--text-muted)' }}>
              Powered by Bolna AI
            </span>
          </div>
        </div>
      </aside>
      <main className="main-content">
        {children || <Outlet />}
      </main>
    </div>
  );
}
