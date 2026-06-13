import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';

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
      navigate('/updateProfile');
    } catch {
      setError('Network error. Please try again.');
    } finally {
      setLoading(false);
    }
  }

  const inputStyle = { width: '100%', padding: '8px', boxSizing: 'border-box' };

  return (
    <div className="App">
      <div className="App-header">
        <h2>Create Account</h2>
      </div>

      <div style={{ maxWidth: '360px', margin: '40px auto', padding: '0 16px' }}>
        <form onSubmit={handleSubmit} noValidate>
          <div style={{ marginBottom: '16px' }}>
            <label htmlFor="email" style={{ display: 'block', marginBottom: '4px' }}>Email</label>
            <input id="email" type="email" value={form.email} onChange={update('email')}
              placeholder="you@example.com" required autoComplete="email" style={inputStyle} />
          </div>

          <div style={{ marginBottom: '16px' }}>
            <label htmlFor="username" style={{ display: 'block', marginBottom: '4px' }}>Username</label>
            <input id="username" type="text" value={form.username} onChange={update('username')}
              placeholder="Choose a username" required minLength={3} autoComplete="username" style={inputStyle} />
          </div>

          <div style={{ marginBottom: '16px' }}>
            <label htmlFor="password" style={{ display: 'block', marginBottom: '4px' }}>Password</label>
            <input id="password" type="password" value={form.password} onChange={update('password')}
              placeholder="At least 8 characters" required autoComplete="new-password" style={inputStyle} />
            <small style={{ color: '#666' }}>
              At least 8 characters. Avoid common or easily guessed passwords.
            </small>
          </div>

          <div style={{ marginBottom: '16px' }}>
            <label htmlFor="password_confirm" style={{ display: 'block', marginBottom: '4px' }}>Confirm Password</label>
            <input id="password_confirm" type="password" value={form.password_confirm}
              onChange={update('password_confirm')} placeholder="Re-enter your password" required
              autoComplete="new-password" style={inputStyle} />
          </div>

          {error && (
            <p role="alert" style={{ color: '#c0392b', marginBottom: '12px' }}>{error}</p>
          )}

          <button type="submit" disabled={loading}
            style={{ width: '100%', padding: '10px', cursor: loading ? 'not-allowed' : 'pointer' }}>
            {loading ? 'Creating account…' : 'Create Account'}
          </button>
        </form>

        <p style={{ marginTop: '16px', textAlign: 'center' }}>
          Already have an account? <Link to="/">Sign in</Link>
        </p>
      </div>
    </div>
  );
}
