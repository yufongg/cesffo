import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { setSession } from '../api/client';
import { useRefreshAuth } from '../components/Security/RoleCheck';

function CheckIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor"
      strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <polyline points="20 6 9 17 4 12" />
    </svg>
  );
}

// NOTE: this is convenience only — the server is the source of truth (SR-01).
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
  // Signup is two-phase: 'details' collects the account fields (and emails a
  // code — no account yet), then 'otp' confirms the code, which creates the
  // account and logs the user in.
  const [step, setStep] = useState('details');
  const [code, setCode] = useState('');
  const [notice, setNotice] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [resending, setResending] = useState(false);
  const navigate = useNavigate();
  const refreshUser = useRefreshAuth();

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

      // No account exists yet: the backend emailed a 6-digit code. Move to the
      // code-entry step, which creates the account on success.
      setStep('otp');
      setNotice(data.detail || 'We emailed you a 6-digit verification code.');
    } catch {
      setError('Network error. Please try again.');
    } finally {
      setLoading(false);
    }
  }

  async function handleVerify(e) {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const response = await fetch('/api/v1/auth/register/verify', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include', // receive the httpOnly session cookie on success
        body: JSON.stringify({ email: form.email, code }),
      });
      const data = await response.json();

      if (!response.ok) {
        setError(extractError(data));
        return;
      }

      // Verification created the account and set the session cookie; keep
      // role/id as UI hints, then greet the new user by name on /courses.
      setSession(data);
      if (refreshUser) await refreshUser();
      navigate('/courses');
    } catch {
      setError('Network error. Please try again.');
    } finally {
      setLoading(false);
    }
  }

  async function handleResend() {
    setError('');
    setNotice('');
    setResending(true);
    try {
      const response = await fetch('/api/v1/auth/register/resend', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: form.email }),
      });
      const data = await response.json();
      setNotice(data.detail || 'If your signup is still pending, a new code has been sent.');
    } catch {
      setError('Network error. Please try again.');
    } finally {
      setResending(false);
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
          {step === 'details' ? (
            <>
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
                    At least 8 characters. Avoid common passwords or your own username or email.
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
                  {loading ? 'Sending code…' : 'Create account'}
                </button>
              </form>

              <p className="auth__alt">
                Already have an account? <Link to="/">Sign in</Link>
              </p>
            </>
          ) : (
            <>
              <h2 className="auth__title">Verify your email</h2>
              <p className="auth__lead">
                We sent a 6-digit code to <strong>{form.email}</strong>. Enter it below
                to finish creating your account.
              </p>

              <form onSubmit={handleVerify} noValidate>
                <div className="field">
                  <label htmlFor="code" className="label">Verification code</label>
                  <input
                    id="code"
                    type="text"
                    className="input"
                    value={code}
                    onChange={e => setCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                    placeholder="123456"
                    inputMode="numeric"
                    autoComplete="one-time-code"
                    pattern="\d{6}"
                    maxLength={6}
                    required
                    autoFocus
                  />
                </div>

                {notice && <p role="status" className="alert alert--success">{notice}</p>}
                {error && <p role="alert" className="alert alert--error">{error}</p>}

                <button
                  type="submit"
                  disabled={loading || code.length !== 6}
                  className="btn btn--primary btn--block"
                >
                  {loading ? 'Verifying…' : 'Verify and continue'}
                </button>
              </form>

              <p className="auth__alt">
                Didn't get a code?{' '}
                <button
                  type="button"
                  className="btn-link"
                  onClick={handleResend}
                  disabled={resending}
                >
                  {resending ? 'Sending…' : 'Resend code'}
                </button>
              </p>

              <p className="auth__alt">
                <button
                  type="button"
                  className="btn-link"
                  onClick={() => { setStep('details'); setCode(''); setError(''); setNotice(''); }}
                >
                  Back to sign up
                </button>
              </p>
            </>
          )}
        </div>
      </main>
    </div>
  );
}
