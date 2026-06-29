import React, { useState } from 'react';
import { Link } from 'react-router-dom';

export default function ForgotPassword() {
  const [email, setEmail] = useState('');
  const [submitted, setSubmitted] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  async function handleSubmit(e) {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const response = await fetch('/api/v1/auth/forgot-password', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email }),
      });

      // The backend intentionally returns the SAME generic response whether or
      // not the email is registered (anti-enumeration), so we always show the
      // same confirmation on success — never "no such account".
      if (!response.ok) {
        // Only schema/rate-limit errors land here.
        if (response.status === 429) {
          setError('Too many requests. Please wait a minute and try again.');
        } else {
          setError('Please enter a valid email address.');
        }
        return;
      }

      setSubmitted(true);
    } catch {
      setError('Network error. Please try again.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="page">
      <div className="container" style={{ maxWidth: '460px' }}>
        <div className="page-header">
          <span className="eyebrow">Security</span>
          <h1>Reset your password</h1>
          <p className="subtitle">
            Enter the email for your account and we'll send you a one-time link to
            set a new password.
          </p>
        </div>

        <div className="card">
          <div className="card__body">
            {submitted ? (
              <>
                <p role="status" className="alert alert--success">
                  If an account exists for <strong>{email}</strong>, a password
                  reset link is on its way. The link expires in 30 minutes and can
                  only be used once. Check your spam folder if you don't see it.
                </p>
                <p className="auth__alt">
                  <Link to="/login">Back to sign in</Link>
                </p>
              </>
            ) : (
              <form onSubmit={handleSubmit} noValidate>
                <div className="field">
                  <label htmlFor="email" className="label">Email</label>
                  <input
                    id="email"
                    type="email"
                    className="input"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="you@example.com"
                    required
                    autoComplete="email"
                    autoFocus
                  />
                </div>

                {error && <p role="alert" className="alert alert--error">{error}</p>}

                <button type="submit" disabled={loading} className="btn btn--primary btn--block">
                  {loading ? 'Sending…' : 'Send reset link'}
                </button>

                <p className="auth__alt" style={{ marginTop: '1rem' }}>
                  Remembered it? <Link to="/login">Back to sign in</Link>
                </p>
              </form>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
