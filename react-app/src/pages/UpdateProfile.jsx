import React from 'react';
import { Link } from 'react-router-dom';

export default function UpdateProfile() {
  return (
    <div className="App">
      <div className="App-header">
        <h2>Update Profile</h2>
      </div>
      <div className="App-intro">
        <p>This is the React route for the update profile page.</p>
        <form>
          <div>
            <label htmlFor="name">Name</label>
            <input id="name" name="name" type="text" placeholder="Enter your name" />
          </div>
          <div>
            <label htmlFor="email">Email</label>
            <input id="email" name="email" type="email" placeholder="Enter your email" />
          </div>
          <button type="button">Save</button>
        </form>
        <p>
          <Link to="/adminAccount">Go to Admin Account</Link>
        </p>
      </div>
    </div>
  );
}