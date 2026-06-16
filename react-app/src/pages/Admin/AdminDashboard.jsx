import React from 'react';
import { Link } from 'react-router-dom';

const STATS = [
  { label: 'Total users', value: '1,245', delta: '+4.2%', up: true, icon: 'users' },
  { label: 'Active sessions', value: '84', delta: '+12 today', up: true, icon: 'activity' },
  { label: 'Courses published', value: '37', delta: '+2 this week', up: true, icon: 'book' },
  { label: 'Revenue (MTD)', value: '$12.8k', delta: '-1.1%', up: false, icon: 'dollar' },
];

function StatIcon({ name }) {
  const paths = {
    users: <><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" /><circle cx="9" cy="7" r="4" /><path d="M23 21v-2a4 4 0 0 0-3-3.87" /><path d="M16 3.13a4 4 0 0 1 0 7.75" /></>,
    activity: <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />,
    book: <><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" /><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" /></>,
    dollar: <><line x1="12" y1="1" x2="12" y2="23" /><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" /></>,
  };
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor"
      strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      {paths[name]}
    </svg>
  );
}

export default function AdminDashboard() {
  return (
    <div className="page">
      <div className="container">
        <div className="page-header">
          <span className="eyebrow">Admin</span>
          <h1>Dashboard</h1>
          <p className="subtitle">An overview of platform activity and performance.</p>
        </div>

        <div className="stat-grid">
          {STATS.map((s) => (
            <div className="stat-card" key={s.label}>
              <div className="stat-card__label">
                <span className="stat-card__icon"><StatIcon name={s.icon} /></span>
                {s.label}
              </div>
              <div className="stat-card__value">{s.value}</div>
              <div className={`stat-card__delta ${s.up ? 'stat-card__delta--up' : 'stat-card__delta--down'}`}>
                {s.delta}
              </div>
            </div>
          ))}
        </div>

        <div className="card">
          <div className="card__body">
            <h3 style={{ marginBottom: '6px' }}>Quick actions</h3>
            <p className="subtitle" style={{ marginBottom: '18px' }}>
              Jump to the most common administrative tasks.
            </p>
            <div className="row-actions">
              <Link to="/admin/users" className="btn btn--primary">Manage users</Link>
              <Link to="/adminAccount" className="btn btn--secondary">Admin account</Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
