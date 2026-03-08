import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export default function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);
    
    try {
      await login(email, password);
      navigate('/');
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to login');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'var(--bg-primary)', padding: 'var(--space-4)' }}>
      <div className="card" style={{ maxWidth: 440, width: '100%', padding: 'var(--space-8)' }}>
        <div style={{ textAlign: 'center', marginBottom: 'var(--space-8)' }}>
          <h1 style={{ fontSize: 'var(--font-3xl)', fontWeight: 700, background: 'var(--accent-gradient)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', marginBottom: 'var(--space-2)' }}>
            VoiceScreen
          </h1>
          <p style={{ color: 'var(--text-secondary)' }}>Sign in to your recruiter account</p>
        </div>

        {error && (
          <div style={{ padding: 'var(--space-3)', marginBottom: 'var(--space-6)', display: 'flex', alignItems: 'center', fontSize: 'var(--font-sm)', fontWeight: 500, background: 'var(--danger-bg)', color: 'var(--danger)', borderRadius: 'var(--radius-md)', border: '1px solid rgba(239, 68, 68, 0.2)' }}>
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-5)' }}>
          <div className="form-group" style={{ marginBottom: 0 }}>
            <label>Email Address</label>
            <input
              type="email"
              required
              className="form-input"
              placeholder="recruiter@company.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </div>
          <div className="form-group" style={{ marginBottom: 0 }}>
            <label>Password</label>
            <input
              type="password"
              required
              className="form-input"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>
          <button
            type="submit"
            disabled={isLoading}
            className="btn btn-primary"
            style={{ width: '100%', justifyContent: 'center', padding: 'var(--space-3)' }}
          >
            {isLoading ? 'Signing in...' : 'Sign In'}
          </button>
        </form>

        <p style={{ marginTop: 'var(--space-6)', textAlign: 'center', fontSize: 'var(--font-sm)', color: 'var(--text-muted)' }}>
          Don't have an account?{' '}
          <Link to="/register" style={{ color: 'var(--accent-primary-hover)', textDecoration: 'none', transition: 'var(--transition)' }}>
            Sign up
          </Link>
        </p>
      </div>
    </div>
  );
}
