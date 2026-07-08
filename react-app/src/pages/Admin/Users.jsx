import React, { useState, useEffect, useCallback } from 'react';
import { apiFetch } from '../../api/client';

const ROLES = ['student', 'instructor', 'admin'];

//? All user-supplied values below are rendered as JSX text/inputs, which React
//? escapes automatically — there is no dangerouslySetInnerHTML anywhere, so no XSS.
export default function AdminUsers() {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [tempPassword, setTempPassword] = useState(null); // { username, password }
  const [newUser, setNewUser] = useState({ email: '', username: '', role: 'student' });

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const data = await apiFetch('/api/v1/admin/users');
      setUsers(data || []);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  function flash(msg) {
    setNotice(msg);
    setError('');
  }

  async function run(action) {
    setError('');
    try {
      await action();
    } catch (e) {
      setError(e.message);
    }
  }

  async function toggleStatus(user) {
    await run(async () => {
      const updated = await apiFetch(`/api/v1/admin/users/${user.user_id}/status`, {
        method: 'PATCH',
        body: { is_active: !user.is_active },
      });
      flash(`${updated.username} is now ${updated.is_active ? 'active' : 'banned'}.`);
      load();
    });
  }

  async function changeRole(user, role) {
    if (role === user.role) return;
    await run(async () => {
      const updated = await apiFetch(`/api/v1/admin/users/${user.user_id}/role`, {
        method: 'PATCH',
        body: { role },
      });
      flash(`${updated.username}'s role is now ${updated.role}.`);
      load();
    });
  }

  async function resetPassword(user) {
    await run(async () => {
      const res = await apiFetch(`/api/v1/admin/users/${user.user_id}/reset-password`, {
        method: 'POST',
      });
      setTempPassword({ username: user.username, password: res.temp_password });
      flash(`Password reset for ${user.username}.`);
      load();
    });
  }

  async function createUser(e) {
    e.preventDefault();
    await run(async () => {
      const res = await apiFetch('/api/v1/admin/users', {
        method: 'POST',
        body: newUser,
      });
      setTempPassword({ username: newUser.username, password: res.temp_password });
      flash(`Created user ${newUser.username}.`);
      setNewUser({ email: '', username: '', role: 'student' });
      load();
    });
  }

  return (
    <div className="page">
      <div className="container">
        <div className="page-header">
          <span className="eyebrow">Admin</span>
          <h1>User management</h1>
          <p className="subtitle">Create accounts, assign roles, and manage access.</p>
        </div>

        {error && <p role="alert" className="alert alert--error">{error}</p>}
        {notice && <p className="alert alert--success">{notice}</p>}

        {tempPassword && (
          <div className="callout">
            <strong>One-time password for {tempPassword.username}:</strong>
            <code>{tempPassword.password}</code>
            <span style={{ flexBasis: '100%', fontSize: '13px' }}>
              Copy it now and share over a secure channel — it will not be shown again.
            </span>
            <button onClick={() => setTempPassword(null)} className="btn btn--secondary btn--sm">
              Dismiss
            </button>
          </div>
        )}

        {/* Create user */}
        <form onSubmit={createUser} className="toolbar">
          <div className="field" style={{ flex: '1 1 200px' }}>
            <label className="label" htmlFor="nu-email">Email</label>
            <input id="nu-email" className="input" type="email" placeholder="email" required
              value={newUser.email}
              onChange={(e) => setNewUser({ ...newUser, email: e.target.value })} />
          </div>
          <div className="field" style={{ flex: '1 1 160px' }}>
            <label className="label" htmlFor="nu-username">Username</label>
            <input id="nu-username" className="input" type="text" placeholder="username" required
              minLength={3} value={newUser.username}
              onChange={(e) => setNewUser({ ...newUser, username: e.target.value })} />
          </div>
          <div className="field" style={{ flex: '0 1 150px' }}>
            <label className="label" htmlFor="nu-role">Role</label>
            <select id="nu-role" className="select" value={newUser.role}
              onChange={(e) => setNewUser({ ...newUser, role: e.target.value })}>
              {ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
            </select>
          </div>
          <button type="submit" className="btn btn--primary">Create user</button>
        </form>

        {loading ? (
          <div className="card"><div className="card__body"><p style={{ margin: 0, color: 'var(--color-muted)' }}>Loading users…</p></div></div>
        ) : (
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>Username</th>
                  <th>Email</th>
                  <th>Role</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {users.map((u) => (
                  <tr key={u.user_id}>
                    <td className="table__user">{u.username}</td>
                    <td>{u.email}</td>
                    <td>
                      <select className="select" value={u.role}
                        onChange={(e) => changeRole(u, e.target.value)}
                        style={{ width: 'auto', minWidth: '130px' }}>
                        {ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
                      </select>
                    </td>
                    <td>
                      <span className={`badge ${u.is_active ? 'badge--active' : 'badge--banned'}`}>
                        {u.is_active ? 'Active' : 'Banned'}
                      </span>
                      {u.force_password_reset && (
                        <span className="badge badge--note" style={{ marginLeft: 6 }}>reset pending</span>
                      )}
                    </td>
                    <td>
                      <div className="row-actions">
                        <button onClick={() => toggleStatus(u)}
                          className={`btn btn--sm ${u.is_active ? 'btn--danger' : 'btn--secondary'}`}>
                          {u.is_active ? 'Ban' : 'Activate'}
                        </button>
                        <button onClick={() => resetPassword(u)} className="btn btn--secondary btn--sm">
                          Reset password
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
                {users.length === 0 && (
                  <tr><td className="table__empty" colSpan={5}>No users found.</td></tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
