import React, { useState } from 'react';
import { useNavigate, Navigate } from 'react-router-dom';
import { setSession } from '../api/client';
import { useRefreshAuth } from '../components/Security/RoleCheck';


export default function ChangePassword() {
  const resetToken = sessionStorage.getItem('reset_token');
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const refreshUser = useRefreshAuth();

  // No reset token means the user didn't come through the forced-reset flow.
  if (!resetToken) {
    return <Navigate to="/" replace />;
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError('');

    if (password !== confirm) {
      setError('Passwords do not match.');
      return;
    }

    setLoading(true);
    try {
      const response = await fetch('/api/v1/auth/change-password', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${resetToken}`,
        },
        body: JSON.stringify({
          new_password: password,
          new_password_confirm: confirm,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        if (response.status === 401 || response.status === 403) {
          sessionStorage.removeItem('reset_token');
          setError('Your reset link expired. Please sign in again.');
          return;
        }
        const detail =
          typeof data?.detail === 'string'
            ? data.detail
            : data?.detail?.[0]?.msg;
        setError(detail || 'Could not update your password.');
        return;
      }

      sessionStorage.removeItem('reset_token');
      // Reset succeeded — the backend issued a real session cookie; keep hints.
      setSession(data);
      // Load the profile into context so the landing page greets by name.
      if (refreshUser) await refreshUser();

      navigate(data.user_role === 'admin' ? '/admin/dashboard' : '/courses');
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
          <h1>Choose a new password</h1>
          <p className="subtitle">
            Your account is using a temporary password. Set a new one to continue.
          </p>
        </div>

        <div className="card">
          <div className="card__body">
            <form onSubmit={handleSubmit} noValidate>
              <div className="field">
                <label htmlFor="new-password" className="label">New password</label>
                <input
                  id="new-password"
                  type="password"
                  className="input"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Enter a new password"
                  required
                  autoComplete="new-password"
                  autoFocus
                />
                <small className="field__hint">
                  At least 10 characters with an uppercase, lowercase, number and
                  special character. Avoid common passwords or your own name/email.
                </small>
              </div>

              <div className="field">
                <label htmlFor="confirm-password" className="label">Confirm new password</label>
                <input
                  id="confirm-password"
                  type="password"
                  className="input"
                  value={confirm}
                  onChange={(e) => setConfirm(e.target.value)}
                  placeholder="Re-enter the new password"
                  required
                  autoComplete="new-password"
                />
              </div>

              {error && <p role="alert" className="alert alert--error">{error}</p>}

              <button type="submit" disabled={loading} className="btn btn--primary btn--block">
                {loading ? 'Updating…' : 'Update password & continue'}
              </button>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}
