import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';

export default function Home() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  async function handleSubmit(e) {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const response = await fetch('/api/v1/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      });

      const data = await response.json();

      if (!response.ok) {
        if (response.status === 423) {
          setError('Account locked after too many failed attempts. Please contact support.');
        } else {
          setError('Incorrect email or password.');
        }
        return;
      }
      // Account on a temporary password: the backend returns a scoped reset
      // token (no session yet). Stash it and route into the password-change flow.
      if (data.force_password_reset) {
        sessionStorage.setItem('reset_token', data.reset_token);
        navigate('/change-password');
        return;
      }

      localStorage.setItem('access_token', data.access_token);
      localStorage.setItem('user_role', data.user_role);
      localStorage.setItem('user_id', data.user_id);

      if (data.user_role === 'admin') {
        navigate('/admin/dashboard');
      } else {
        navigate('/updateProfile');
      }
    } catch {
      setError('Network error. Please try again.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="App">
      <div className="App-header">
        <h2>Sign In</h2>
      </div>

      <div style={{ maxWidth: '360px', margin: '40px auto', padding: '0 16px' }}>
        <form onSubmit={handleSubmit} noValidate>
          <div style={{ marginBottom: '16px' }}>
            <label htmlFor="email" style={{ display: 'block', marginBottom: '4px' }}>
              Email
            </label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={e => setEmail(e.target.value)}
              placeholder="you@example.com"
              required
              autoComplete="email"
              style={{ width: '100%', padding: '8px', boxSizing: 'border-box' }}
            />
          </div>

          <div style={{ marginBottom: '16px' }}>
            <label htmlFor="password" style={{ display: 'block', marginBottom: '4px' }}>
              Password
            </label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              placeholder="Enter your password"
              required
              autoComplete="current-password"
              style={{ width: '100%', padding: '8px', boxSizing: 'border-box' }}
            />
          </div>

          {error && (
            <p role="alert" style={{ color: '#c0392b', marginBottom: '12px' }}>
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={loading}
            style={{ width: '100%', padding: '10px', cursor: loading ? 'not-allowed' : 'pointer' }}
          >
            {loading ? 'Signing in…' : 'Sign In'}
          </button>
        </form>
      </div>
    </div>
  );
}
