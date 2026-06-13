import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import RoleCheck from '../Security/RoleCheck';

export default function AdminAccount(user) {
  
  return (
    <div className="App">
      <div className="App-header">
        <h2>Admin Account</h2>
      </div>
      <div className="App-intro">
        <p>Username: {user?.username}</p>
        <p>Email: {user?.email}</p>
        <p>Role: {user?.role}</p>
        <p>
          <Link to="/admin/dashboard" style={{ marginRight: '10px' }}>Go to Admin Dashboard</Link>
          <Link to="/">Back to Home</Link>
        </p>
      </div>
    </div>
  );
}