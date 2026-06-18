import React from 'react';
import { Link, NavLink, useNavigate, useLocation } from 'react-router-dom';
import ThemeToggle from './ThemeToggle';

export default function Navbar() {
  // useLocation causes a re-render on every route change,
  // ensuring localStorage is re-read after login/logout navigation.
  useLocation();

  const token = localStorage.getItem('access_token');
  const role = localStorage.getItem('user_role');
  const navigate = useNavigate();

  function handleLogout() {
    localStorage.removeItem('access_token');
    localStorage.removeItem('user_role');
    localStorage.removeItem('user_id');
    navigate('/');
  }

  const navClass = ({ isActive }) =>
    isActive ? 'navlink navlink--active' : 'navlink';

  return (
    <header className="navbar">
      <div className="container navbar__inner">
        <Link to="/courses" className="brand" aria-label="Cesffo home">
          <span className="brand__mark">C</span>
          Cesffo
        </Link>

        <nav className="navbar__links" aria-label="Primary">
          {!token ? (
            <>
              <NavLink to="/" end className={navClass}>Login</NavLink>
              <Link to="/register" className="btn btn--primary btn--sm">Get started</Link>
            </>
          ) : (
            <>
              <NavLink to="/courses" className={navClass}>My Learning</NavLink>
              <NavLink to="/marketplace" className={navClass}>Marketplace</NavLink>
              <NavLink to="/forums" className={navClass}>Forums</NavLink>
              <NavLink to="/updateProfile" className={navClass}>My Profile</NavLink>
              {(role === 'instructor') && (
                <>
                  <span className="navbar__divider" aria-hidden="true" />
                  <NavLink to="/instructor" className={navClass}>Instructor</NavLink>
                </>
              )}
              {role === 'admin' && (
                <>
                  <span className="navbar__divider" aria-hidden="true" />
                  <NavLink to="/admin/dashboard" className={navClass}>Dashboard</NavLink>
                  <NavLink to="/admin/users" className={navClass}>Users</NavLink>
                </>
              )}
              <span className="navbar__divider" aria-hidden="true" />
              <button onClick={handleLogout} className="btn btn--ghost btn--sm">
                Log out
              </button>
            </>
          )}
          <ThemeToggle />
        </nav>
      </div>
    </header>
  );
}
