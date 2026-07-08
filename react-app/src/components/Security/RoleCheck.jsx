import React, { createContext, useState, useEffect, useContext } from 'react';
import { Navigate } from 'react-router-dom';
import { apiFetch, isAuthenticated } from '../../api/client';

const AuthContext = createContext(null);

//? Verifies the session against the backend (which validates the JWT) and exposes
//? the authenticated user via context. Always renders children once resolved.
export function RoleCheck({ children }) {
    const [user, setUser] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (!isAuthenticated()) {
            setUser(null);
            setLoading(false);
            return;
        }
    apiFetch('/api/v1/auth/getProfile')
        .then((data) => setUser(data))
        .catch(() => setUser(null)) 
        .finally(() => setLoading(false));
    }, []);

    if (loading) {
        return <div className="loading-screen">Verifying session…</div>;
    }

    return <AuthContext.Provider value={user}>{children}</AuthContext.Provider>;
}

export const useAuth = () => useContext(AuthContext);

export function ProtectedRoute({ children, adminOnly = false, instructorOnly = false }) {
    // These are UI hints only; the backend re-validates the cookie on every
    // request, so a tampered role just yields 401/403 from the API.
    const role = localStorage.getItem('user_role');

    if (!role) {
        return <Navigate to="/" replace />;
    }

    if (adminOnly && role !== 'admin') {
        return <Navigate to="/NotFound" replace />;
    }

    // Course-authoring routes: mirror the backend `require_instructor` gate,
    // which also lets admins through so staff can manage any course.
    if (instructorOnly && role !== 'instructor' && role !== 'admin') {
        return <Navigate to="/NotFound" replace />;
    }

    return children;
}
