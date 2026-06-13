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

  const cell = { padding: '8px 10px', borderBottom: '1px solid #eee', textAlign: 'left' };

  return (
    <div className="App" style={{ maxWidth: '960px', margin: '0 auto', padding: '16px' }}>
      <h2>User Management</h2>

      {error && <p role="alert" style={{ color: '#c0392b' }}>{error}</p>}
      {notice && <p style={{ color: '#27ae60' }}>{notice}</p>}

      {tempPassword && (
        <div style={{ border: '1px solid #f0ad4e', background: '#fcf8e3', padding: '12px', margin: '12px 0' }}>
          <strong>One-time password for {tempPassword.username}:</strong>{' '}
          <code>{tempPassword.password}</code>
          <p style={{ margin: '6px 0 0', fontSize: '13px' }}>
            Copy it now and share over a secure channel — it will not be shown again.
          </p>
          <button onClick={() => setTempPassword(null)} style={{ marginTop: '6px' }}>Dismiss</button>
        </div>
      )}

      {/* Create user */}
      <form onSubmit={createUser} style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', margin: '16px 0' }}>
        <input
          type="email" placeholder="email" required value={newUser.email}
          onChange={(e) => setNewUser({ ...newUser, email: e.target.value })}
        />
        <input
          type="text" placeholder="username" required minLength={3} value={newUser.username}
          onChange={(e) => setNewUser({ ...newUser, username: e.target.value })}
        />
        <select value={newUser.role} onChange={(e) => setNewUser({ ...newUser, role: e.target.value })}>
          {ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
        </select>
        <button type="submit">Create user</button>
      </form>

      {loading ? (
        <p>Loading users…</p>
      ) : (
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr>
              <th style={cell}>Username</th>
              <th style={cell}>Email</th>
              <th style={cell}>Role</th>
              <th style={cell}>Status</th>
              <th style={cell}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.user_id}>
                <td style={cell}>{u.username}</td>
                <td style={cell}>{u.email}</td>
                <td style={cell}>
                  <select value={u.role} onChange={(e) => changeRole(u, e.target.value)}>
                    {ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
                  </select>
                </td>
                <td style={cell}>
                  <span style={{ color: u.is_active ? '#27ae60' : '#c0392b' }}>
                    {u.is_active ? 'Active' : 'Banned'}
                  </span>
                  {u.force_password_reset && (
                    <span style={{ marginLeft: 6, fontSize: 12, color: '#888' }}>(reset pending)</span>
                  )}
                </td>
                <td style={cell}>
                  <button onClick={() => toggleStatus(u)} style={{ marginRight: 6 }}>
                    {u.is_active ? 'Ban' : 'Activate'}
                  </button>
                  <button onClick={() => resetPassword(u)}>Reset password</button>
                </td>
              </tr>
            ))}
            {users.length === 0 && (
              <tr><td style={cell} colSpan={5}>No users found.</td></tr>
            )}
          </tbody>
        </table>
      )}
    </div>
  );
}
