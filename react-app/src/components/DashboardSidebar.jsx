import React from 'react';
import { NavLink } from 'react-router-dom';

// Left-hand dashboard navigation, inspired by the OffSec console layout.
//? These are presentational entry points only — the destinations (cart,
//? achievements, etc.) are placeholders for now. Routes that don't exist yet
//? fall through to the catch-all <NotFound/> in App.js, so nothing breaks.

function BrowseIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
      strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <circle cx="12" cy="12" r="10" />
      <polygon points="16.24 7.76 14.12 14.12 7.76 16.24 9.88 9.88 16.24 7.76" />
    </svg>
  );
}

function CartIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
      strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <circle cx="9" cy="21" r="1" />
      <circle cx="20" cy="21" r="1" />
      <path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6" />
    </svg>
  );
}

function TrophyIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
      strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M8 21h8M12 17v4M7 4h10v5a5 5 0 0 1-10 0V4z" />
      <path d="M5 9a3 3 0 0 1-3-3V5h3M19 9a3 3 0 0 0 3-3V5h-3" />
    </svg>
  );
}

function LeaderboardIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
      strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <line x1="18" y1="20" x2="18" y2="10" />
      <line x1="12" y1="20" x2="12" y2="4" />
      <line x1="6" y1="20" x2="6" y2="14" />
    </svg>
  );
}

function ForumIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
      strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z" />
    </svg>
  );
}

function SupportIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
      strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <circle cx="12" cy="12" r="10" />
      <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3" />
      <line x1="12" y1="17" x2="12.01" y2="17" />
    </svg>
  );
}

// Destination, label and icon for each item. `end` keeps the active state from
// bleeding into child routes.
const ITEMS = [
  { to: '/marketplace', label: 'Browse courses', Icon: BrowseIcon },
  { to: '/cart', label: 'Cart', Icon: CartIcon },
  { to: '/achievements', label: 'Achievements', Icon: TrophyIcon },
  { to: '/leaderboard', label: 'Leaderboard', Icon: LeaderboardIcon },
  { to: '/forums', label: 'Forums', Icon: ForumIcon },
  { to: '/support', label: 'Help & support', Icon: SupportIcon },
];

export default function DashboardSidebar() {
  const linkClass = ({ isActive }) =>
    isActive ? 'side-nav__link side-nav__link--active' : 'side-nav__link';

  return (
    <aside className="side-nav" aria-label="Dashboard">
      <p className="side-nav__heading">Learn</p>
      <nav className="side-nav__group">
        {ITEMS.map(({ to, label, Icon }) => (
          <NavLink key={to} to={to} className={linkClass}>
            <span className="side-nav__icon"><Icon /></span>
            {label}
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}
