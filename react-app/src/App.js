import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import './App.css';

import Navbar from './components/Navbar';
import Footer from './components/Footer';
import Home from './pages/Home';
import Register from './pages/Register';
import UpdateProfile from './pages/UpdateProfile';
import AdminAccount from './pages/Admin/AdminAccount';
import AdminDashboard from './pages/Admin/AdminDashboard';
import AdminUsers from './pages/Admin/Users';

// Security Imports
import { RoleCheck, ProtectedRoute } from './pages/Security/RoleCheck';

export default function App() {
  return (
    <BrowserRouter>
      <RoleCheck>
        <Navbar />
        <Routes>
          <Route path="/" element={<Home />} />
          {/* /login is an alias for the home login form */}
          <Route path="/login" element={<Home />} />
          <Route path="/register" element={<Register />} />

          <Route
            path="/updateProfile"
            element={
              <ProtectedRoute>
                <UpdateProfile />
              </ProtectedRoute>
            }
          />

          {/* The routes with adminOnly are only allowed for administrators. */}
          <Route
            path="/adminAccount"
            element={
              <ProtectedRoute adminOnly={true}>
                <AdminAccount />
              </ProtectedRoute>
            }
          />

          <Route
            path="/admin/dashboard"
            element={
              <ProtectedRoute adminOnly={true}>
                <AdminDashboard />
              </ProtectedRoute>
            }
          />

          <Route
            path="/admin/users"
            element={
              <ProtectedRoute adminOnly={true}>
                <AdminUsers />
              </ProtectedRoute>
            }
          />
        </Routes>
        <Footer />
      </RoleCheck>
    </BrowserRouter>
  );
}
