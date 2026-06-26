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
      </div>
    </div>
  );
}
