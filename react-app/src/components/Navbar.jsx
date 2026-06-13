import React from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';

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

  if (!token) {
    return (
      <nav className="App-nav">
        <Link to="/">Login</Link>
        <Link to="/register">Register</Link>
      </nav>
    );
  }

  return (
    <nav className="App-nav">
      <Link to="/updateProfile">Update Profile</Link>
      {role === 'admin' && (
        <>
          <Link to="/adminAccount">Admin Account</Link>
          <Link to="/admin/dashboard">Admin Dashboard</Link>
          <Link to="/admin/users">Manage Users</Link>
        </>
      )}
      <button onClick={handleLogout} style={{ cursor: 'pointer' }}>
        Logout
      </button>
    </nav>
  );
}
