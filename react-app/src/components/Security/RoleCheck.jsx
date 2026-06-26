import React, { createContext, useState, useEffect, useContext, useCallback } from 'react';
import { Navigate } from 'react-router-dom';
import { apiFetch, isAuthenticated } from '../../api/client';

const AuthContext = createContext(null);

//? Verifies the session against the backend (which validates the JWT) and exposes
//? the authenticated user via context. Always renders children once resolved.
export function RoleCheck({ children }) {
    const [user, setUser] = useState(null);
    const [loading, setLoading] = useState(true);

    // Re-fetch the profile so consumers reflect changes made elsewhere (e.g. a
    // username/email update). Returns the latest profile.
    const refreshUser = useCallback(async () => {
        if (!isAuthenticated()) {
            setUser(null);
            return null;
        }
        const data = await apiFetch('/api/v1/auth/getProfile');
        setUser(data);
        return data;
    }, []);

    useEffect(() => {
        refreshUser()
            .catch(() => setUser(null))
            .finally(() => setLoading(false));
    }, [refreshUser]);

    if (loading) {
        return <div className="loading-screen">Verifying session…</div>;
    }

    return (
        <AuthContext.Provider value={{ user, refreshUser }}>
            {children}
        </AuthContext.Provider>
    );
}

// Returns the authenticated user's profile (or null). Components read this for
// display only; the backend re-validates the session on every request.
export const useAuth = () => useContext(AuthContext)?.user ?? null;

// Returns a function that re-fetches the profile into context after a change.
export const useRefreshAuth = () => useContext(AuthContext)?.refreshUser;

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
