import React from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../../components/Security/RoleCheck';

function initialOf(user) {
  const source = user?.username || user?.email || '?';
  return source.charAt(0).toUpperCase();
}

export default function AdminAccount() {
  const user = useAuth();

  return (
    <div className="page">
      <div className="container" style={{ maxWidth: '720px' }}>
        <div className="page-header">
          <span className="eyebrow">Admin</span>
          <h1>Admin account</h1>
          <p className="subtitle">Your administrator profile and access details.</p>
        </div>

        <div className="card">
          <div className="card__body">
            <div style={{ display: 'flex', alignItems: 'center', gap: '16px', marginBottom: '20px' }}>
              <span className="avatar">{initialOf(user)}</span>
              <div>
                <h3 style={{ margin: 0 }}>{user?.username || '—'}</h3>
                <span className="badge badge--neutral" style={{ marginTop: '4px' }}>
                  {user?.role || 'admin'}
                </span>
              </div>
            </div>

            <dl className="profile-grid">
              <dt>Username</dt>
              <dd>{user?.username || '—'}</dd>
              <dt>Email</dt>
              <dd>{user?.email || '—'}</dd>
              <dt>Role</dt>
              <dd>{user?.role || '—'}</dd>
            </dl>

            <div className="row-actions" style={{ marginTop: '24px' }}>
              <Link to="/admin/dashboard" className="btn btn--primary">Go to dashboard</Link>
              <Link to="/admin/users" className="btn btn--secondary">Manage users</Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
