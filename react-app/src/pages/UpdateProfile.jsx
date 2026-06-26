import React, { useEffect, useState } from 'react';
import { apiFetch } from '../api/client';
import { useAuth, useRefreshAuth } from '../components/Security/RoleCheck';

export default function UpdateProfile() {
  const user = useAuth();
  const refreshUser = useRefreshAuth();

  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [saving, setSaving] = useState(false);

  // Password change is a separate concern with its own state and submit.
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [pwError, setPwError] = useState('');
  const [pwSuccess, setPwSuccess] = useState('');
  const [pwSaving, setPwSaving] = useState(false);

  // Seed the form once the profile loads (it arrives asynchronously).
  useEffect(() => {
    if (user) {
      setUsername(user.username || '');
      setEmail(user.email || '');
    }
  }, [user]);

  async function handleSubmit(e) {
    e.preventDefault();
    setError('');
    setSuccess('');

    // Only send fields that actually changed; the backend requires at least one.
    const payload = {};
    const trimmedName = username.trim();
    const trimmedEmail = email.trim();
    if (user && trimmedName !== (user.username || '')) payload.username = trimmedName;
    if (user && trimmedEmail.toLowerCase() !== (user.email || '').toLowerCase()) {
      payload.email = trimmedEmail;
    }

    if (Object.keys(payload).length === 0) {
      setError('Nothing to update — change your username or email first.');
      return;
    }

    setSaving(true);
    try {
      await apiFetch('/api/v1/auth/profile', { method: 'PATCH', body: payload });
      // Re-fetch the cached profile so the nav greeting and other views that
      // read `useAuth()` reflect the new username/email immediately.
      if (refreshUser) await refreshUser();
      setSuccess('Your profile has been updated.');
    } catch (err) {
      setError(err.message || 'Could not update your profile.');
    } finally {
      setSaving(false);
    }
  }

  async function handlePasswordSubmit(e) {
    e.preventDefault();
    setPwError('');
    setPwSuccess('');

    if (newPassword !== confirmPassword) {
      setPwError('New passwords do not match.');
      return;
    }

    setPwSaving(true);
    try {
      await apiFetch('/api/v1/auth/change-my-password', {
        method: 'POST',
        body: {
          current_password: currentPassword,
          new_password: newPassword,
          new_password_confirm: confirmPassword,
        },
      });
      setPwSuccess('Your password has been changed.');
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
    } catch (err) {
      setPwError(err.message || 'Could not change your password.');
    } finally {
      setPwSaving(false);
    }
  }

  return (
    <div className="page">
      <div className="container" style={{ maxWidth: '720px' }}>
        <div className="page-header">
          <span className="eyebrow">Account</span>
          <h1>Profile settings</h1>
          <p className="subtitle">Update your personal details and how others see you.</p>
        </div>

        <div className="card">
          <div className="card__body">
            <form onSubmit={handleSubmit} noValidate>
              <div className="field">
                <label htmlFor="name" className="label">Update Username</label>
                <input id="name" name="name" type="text" className="input"
                  placeholder="Enter your name"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  minLength={3} maxLength={150} autoComplete="username" />
              </div>

              <div className="field">
                <label htmlFor="email" className="label">Update Email</label>
                <input id="email" name="email" type="email" className="input"
                  placeholder="you@example.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  autoComplete="email" />
                <small className="field__hint">
                  This is also your sign-in address — you&apos;ll use the new email to
                  log in next time. We&apos;ll use it for account and course notifications.
                </small>
              </div>

              {error && <p role="alert" className="alert alert--error">{error}</p>}
              {success && <p role="status" className="alert alert--success">{success}</p>}

              <div className="row-actions" style={{ marginTop: '8px' }}>
                <button type="submit" disabled={saving} className="btn btn--primary">
                  {saving ? 'Saving…' : 'Save changes'}
                </button>
                <button
                  type="button"
                  className="btn btn--secondary"
                  onClick={() => {
                    setUsername(user?.username || '');
                    setEmail(user?.email || '');
                    setError('');
                    setSuccess('');
                  }}
                >
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>

        <div className="card" style={{ marginTop: '24px' }}>
          <div className="card__body">
            <form onSubmit={handlePasswordSubmit} noValidate>
              <div className="field">
                <strong className="field__hint">Password Reset</strong>
              </div>

              <div className="field">
                <label htmlFor="opass" className="label">Old Password</label>
                <input id="opass" name="opass" type="password" className="input"
                  placeholder="Enter your current password"
                  value={currentPassword}
                  onChange={(e) => setCurrentPassword(e.target.value)}
                  autoComplete="current-password" required />
              </div>

              <div className="field">
                <label htmlFor="npass" className="label">New Password</label>
                <input id="npass" name="npass" type="password" className="input"
                  placeholder="Enter new password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  autoComplete="new-password" required minLength={10} />
                <small className="field__hint">
                  At least 10 characters with an uppercase, lowercase, number and
                  special character. Avoid your username or email.
                </small>
              </div>

              <div className="field">
                <label htmlFor="r_npass" className="label">Retype Password</label>
                <input id="r_npass" name="r_npass" type="password" className="input"
                  placeholder="Retype new password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  autoComplete="new-password" required />
              </div>

              {pwError && <p role="alert" className="alert alert--error">{pwError}</p>}
              {pwSuccess && <p role="status" className="alert alert--success">{pwSuccess}</p>}

              <div className="row-actions" style={{ marginTop: '8px' }}>
                <button type="submit" disabled={pwSaving} className="btn btn--primary">
                  {pwSaving ? 'Updating…' : 'Change password'}
                </button>
              </div>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}
