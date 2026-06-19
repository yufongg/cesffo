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

// NOTE: this is convenience only — the server is the source of truth.
function clientPasswordIssues(pw) {
  const issues = [];
  if (pw.length < 8) issues.push('at least 8 characters');
  return issues;
}

// FastAPI returns `detail` as a string (HTTPException) or an array (422 validation).
function extractError(data) {
  if (!data || !data.detail) return 'Registration failed. Please try again.';
  if (typeof data.detail === 'string') return data.detail;
  if (Array.isArray(data.detail) && data.detail.length) {
    return data.detail[0].msg || 'Invalid input.';
  }
  return 'Registration failed. Please try again.';
}

export default function Register() {
  const [form, setForm] = useState({
    email: '',
    username: '',
    password: '',
    password_confirm: '',
  });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  function update(field) {
    return e => setForm({ ...form, [field]: e.target.value });
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError('');

    if (form.password !== form.password_confirm) {
      setError('Passwords do not match.');
      return;
    }
    const issues = clientPasswordIssues(form.password);
    if (issues.length) {
      setError('Password must contain ' + issues.join(', ') + '.');
      return;
    }

    setLoading(true);
    try {
      const response = await fetch('/api/v1/auth/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form),
      });
      const data = await response.json();

      if (!response.ok) {
        setError(extractError(data));
        return;
      }

      localStorage.setItem('access_token', data.access_token);
      localStorage.setItem('user_role', data.user_role);
      localStorage.setItem('user_id', data.user_id);
      navigate('/courses');
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

        <h1 className="auth__headline">Start your financial literacy journey.</h1>
        <p className="auth__sub">
          Create a free account and get instant access to courses, tools, and
          resources designed to make money simple.
        </p>

        <div className="auth__seam" aria-hidden="true" />

        <ul className="auth__points">
          <li><CheckIcon /> Free to join, no card required</li>
          <li><CheckIcon /> Beginner-friendly, expert-built lessons</li>
          <li><CheckIcon /> Track progress across every course</li>
        </ul>
      </aside>

      <main className="auth__main">
        <div className="auth__form">
          <h2 className="auth__title">Create your account</h2>
          <p className="auth__lead">Join Cesffo in under a minute.</p>

          <form onSubmit={handleSubmit} noValidate>
            <div className="field">
              <label htmlFor="email" className="label">Email</label>
              <input id="email" type="email" className="input" value={form.email}
                onChange={update('email')} placeholder="you@example.com" required
                autoComplete="email" autoFocus />
            </div>

            <div className="field">
              <label htmlFor="username" className="label">Username</label>
              <input id="username" type="text" className="input" value={form.username}
                onChange={update('username')} placeholder="Choose a username" required
                minLength={3} autoComplete="username" />
            </div>

            <div className="field">
              <label htmlFor="password" className="label">Password</label>
              <input id="password" type="password" className="input" value={form.password}
                onChange={update('password')} placeholder="At least 8 characters" required
                autoComplete="new-password" />
              <small className="field__hint">
                At least 8 characters. Avoid common or easily guessed passwords.
              </small>
            </div>

            <div className="field">
              <label htmlFor="password_confirm" className="label">Confirm password</label>
              <input id="password_confirm" type="password" className="input"
                value={form.password_confirm} onChange={update('password_confirm')}
                placeholder="Re-enter your password" required autoComplete="new-password" />
            </div>

            {error && <p role="alert" className="alert alert--error">{error}</p>}

            <button type="submit" disabled={loading} className="btn btn--primary btn--block">
              {loading ? 'Creating account…' : 'Create account'}
            </button>
          </form>

          <p className="auth__alt">
            Already have an account? <Link to="/">Sign in</Link>
          </p>
        </div>
      </main>
    </div>
  );
}
