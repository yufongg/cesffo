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

export default function Home() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  // Login is two-phase: 'credentials' collects email+password, then 'otp'
  // collects the 6-digit code the backend emails after the password checks out.
  const [step, setStep] = useState('credentials');
  const [code, setCode] = useState('');
  const [notice, setNotice] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [resending, setResending] = useState(false);
  const navigate = useNavigate();
  const refreshUser = useRefreshAuth();

  // Establish the session from a successful /login/verify response and route on.
  async function completeLogin(data) {
    // The session itself is the httpOnly cookie the backend just set; we only
    // keep role/id as UI hints.
    setSession(data);
    // Populate auth context so the destination greets the user by name.
    if (refreshUser) await refreshUser();

    if (data.user_role === 'admin') {
      navigate('/admin/dashboard');
    } else {
      navigate('/courses');
    }
  }

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

      // Password verified: the backend has emailed a 6-digit code and issued NO
      // session yet. Move to the code-entry step.
      if (data.otp_required) {
        setStep('otp');
        setNotice(data.detail || 'We emailed you a 6-digit sign-in code.');
        return;
      }
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
      const response = await fetch('/api/v1/auth/login/verify', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include', // receive the httpOnly session cookie on success
        body: JSON.stringify({ email, code }),
      });

      const data = await response.json();

      if (!response.ok) {
        setError('Invalid or expired code. Please try again.');
        return;
      }

      await completeLogin(data);
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
      const response = await fetch('/api/v1/auth/login/resend', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email }),
      });
      const data = await response.json();
      setNotice(data.detail || 'If your login is still pending, a new code has been sent.');
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
          {step === 'credentials' ? (
            <>
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
                <Link to="/forgot-password">Forgot your password?</Link>
              </p>

              <p className="auth__alt">
                New to Cesffo? <Link to="/register">Create an account</Link>
              </p>
            </>
          ) : (
            <>
              <h2 className="auth__title">Enter your code</h2>
              <p className="auth__lead">
                We sent a 6-digit code to <strong>{email}</strong>. Enter it below to
                finish signing in.
              </p>

              <form onSubmit={handleVerify} noValidate>
                <div className="field">
                  <label htmlFor="code" className="label">Sign-in code</label>
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
                  {loading ? 'Verifying…' : 'Verify and sign in'}
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
                  onClick={() => { setStep('credentials'); setCode(''); setError(''); setNotice(''); }}
                >
                  Use a different account
                </button>
              </p>
            </>
          )}
        </div>
      </main>
    </div>
  );
}
