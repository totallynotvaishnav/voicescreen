import { createContext, useContext, useState, useEffect } from 'react';
import apiClient from '../api/client';

const AuthContext = createContext();

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const checkAuthStatus = async () => {
      const token = localStorage.getItem('token');
      if (token) {
        try {
          const res = await apiClient.get('/auth/me');
          setUser(res.data);
        } catch (error) {
          localStorage.removeItem('token');
          setUser(null);
        }
      }
      setLoading(false);
    };

    checkAuthStatus();

    // Listen for unauthorized events from axios interceptor
    const handleUnauthorized = () => {
      setUser(null);
    };
    window.addEventListener('auth:unauthorized', handleUnauthorized);
    return () => window.removeEventListener('auth:unauthorized', handleUnauthorized);
  }, []);

  const login = async (email, password) => {
    const params = new URLSearchParams();
    params.append('username', email); // OAuth2 expects 'username'
    params.append('password', password);

    const res = await apiClient.post('/auth/login', params, {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded'
      }
    });
    localStorage.setItem('token', res.data.access_token);
    
    // Fetch user details immediately after login
    const userRes = await apiClient.get('/auth/me');
    setUser(userRes.data);
  };

  const register = async (email, password) => {
    await apiClient.post('/auth/register', { email, password });
    await login(email, password); // Auto login after register
  };

  const logout = () => {
    localStorage.removeItem('token');
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout }}>
      {!loading && children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
