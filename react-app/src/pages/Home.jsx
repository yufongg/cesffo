import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';

function CheckIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor"
      strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <polyline points="20 6 9 17 4 12" />
    </svg>
  );
}

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

      // The session itself is the httpOnly cookie the backend just set; we only
      // keep role/id as UI hints.
      localStorage.setItem('user_role', data.user_role);
      localStorage.setItem('user_id', data.user_id);

      if (data.user_role === 'admin') {
        navigate('/admin/dashboard');
      } else {
        navigate('/courses');
      }
    } catch {
      setError('Network error. Please try again.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="auth">
      <aside className="auth__aside">
        <span className="auth__aside-brand">
          <span className="brand__mark">C</span>
          Cesffo
        </span>

        <h1 className="auth__headline">Build real financial confidence.</h1>
        <p className="auth__sub">
          Sign in to continue your courses, track your progress, and put practical
          money skills to work.
        </p>

        <div className="auth__seam" aria-hidden="true" />

        <ul className="auth__points">
          <li><CheckIcon /> Structured lessons on budgeting, saving &amp; investing</li>
          <li><CheckIcon /> Interactive tools and real-world scenarios</li>
          <li><CheckIcon /> Learn at your own pace, on any device</li>
        </ul>
      </aside>

      <main className="auth__main">
        <div className="auth__form">
          <h2 className="auth__title">Welcome back</h2>
          <p className="auth__lead">Sign in to your Cesffo account.</p>

          <form onSubmit={handleSubmit} noValidate>
            <div className="field">
              <label htmlFor="email" className="label">Email</label>
              <input
                id="email"
                type="email"
                className="input"
                value={email}
                onChange={e => setEmail(e.target.value)}
                placeholder="you@example.com"
                required
                autoComplete="email"
                autoFocus
              />
            </div>

            <div className="field">
              <label htmlFor="password" className="label">Password</label>
              <input
                id="password"
                type="password"
                className="input"
                value={password}
                onChange={e => setPassword(e.target.value)}
                placeholder="Enter your password"
                required
                autoComplete="current-password"
              />
            </div>

            {error && <p role="alert" className="alert alert--error">{error}</p>}

            <button type="submit" disabled={loading} className="btn btn--primary btn--block">
              {loading ? 'Signing in…' : 'Sign in'}
            </button>
          </form>

          <p className="auth__alt">
            New to Cesffo? <Link to="/register">Create an account</Link>
          </p>
        </div>
      </main>
    </div>
  );
}
