import React from 'react';
import { Link } from 'react-router-dom';

export default function AdminDashboard() {
  return (
    <div className="App">
      <div className="App-header">
        <h2>Admin Dashboard</h2>
      </div>
      <div className="App-intro">
        <p>Welcome to the control center. Here you can manage your application metrics.</p>
        
        {/* Mock dashboard UI layout */}
        <div style={{ display: 'flex', gap: '20px', justifyContent: 'center', margin: '20px 0' }}>
          <div style={{ border: '1px solid #ccc', padding: '20px', borderRadius: '8px' }}>
            <h3>Total Users</h3>
            <p style={{ fontSize: '24px', fontWeight: 'bold' }}>1,245</p>
          </div>
          <div style={{ border: '1px solid #ccc', padding: '20px', borderRadius: '8px' }}>
            <h3>Active Sessions</h3>
            <p style={{ fontSize: '24px', fontWeight: 'bold' }}>84</p>
          </div>
        </div>

        <p>
          <Link to="/adminAccount">View Admin Account Profile</Link>
        </p>
      </div>
    </div>
  );
}