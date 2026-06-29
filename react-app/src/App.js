import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import './App.css';

import Navbar from './components/Navbar';
import Footer from './components/Footer';
import Home from './pages/Home';
import Register from './pages/Register';
import ChangePassword from './pages/ChangePassword';
import ForgotPassword from './pages/ForgotPassword';
import HelpSupport from './pages/HelpSupport';
import Courses from './pages/Courses';
import Marketplace from './pages/Marketplace';
import Cart from './pages/Cart';
import CoursePreview from './pages/CoursePreview';
import CourseLearn from './pages/CourseLearn';
import Forum from './pages/Forum';
import ModuleQuiz from './pages/ModuleQuiz';
import UpdateProfile from './pages/UpdateProfile';
import AdminAccount from './pages/Admin/AdminAccount';
import AdminDashboard from './pages/Admin/AdminDashboard';
import AdminUsers from './pages/Admin/Users';
import InstructorDashboard from './pages/InstructorDashboard';
import NotFound from './pages/NotFound';

// Security Imports
import { RoleCheck, ProtectedRoute } from './components/Security/RoleCheck';

export default function App() {
    return (
        <BrowserRouter>
            <RoleCheck>
                <div className="app-shell">
                <Navbar />
                <main className="app-main">
                <Routes>
                  <Route path="/" element={<Home />} />
                  {/* /login is an alias for the home login form */}
                  <Route path="/login" element={<Home />} />
                  <Route path="/register" element={<Register />} />
                  {/* Self-service "forgot password" — request a reset link by email. */}
                  <Route path="/forgot-password" element={<ForgotPassword />} />
                  {/* Forced password change — self-guards via the reset token. */}
                  <Route path="/change-password" element={<ChangePassword />} />
                  {/* Reset via emailed one-time link — token comes from the URL. */}
                  <Route path="/reset-password" element={<ChangePassword />} />

                  {/* Public help & support — reachable even when signed out. */}
                  <Route path="/help" element={<HelpSupport />} />

                  {/* Default landing for any authenticated user. */}
                  <Route
                    path="/courses"
                    element={
                      <ProtectedRoute>
                        <Courses />
                      </ProtectedRoute>
                    }
                  />

                  <Route
                    path="/marketplace"
                    element={
                      <ProtectedRoute>
                        <Marketplace />
                      </ProtectedRoute>
                    }
                  />

                  <Route
                    path="/cart"
                    element={
                      <ProtectedRoute>
                        <Cart />
                      </ProtectedRoute>
                    }
                  />

                  {/* Read-only syllabus for non-enrolled students; gateway to enrolling. */}
                  <Route
                    path="/courses/:courseId/preview"
                    element={
                      <ProtectedRoute>
                        <CoursePreview />
                      </ProtectedRoute>
                    }
                  />

                  <Route
                    path="/courses/:courseId/learn"
                    element={
                      <ProtectedRoute>
                        <CourseLearn />
                      </ProtectedRoute>
                    }
                  />

                  <Route
                    path="/courses/:courseId/modules/:moduleId/quiz"
                    element={
                      <ProtectedRoute>
                        <ModuleQuiz />
                      </ProtectedRoute>
                    }
                  />

                  <Route
                    path="/forums"
                    element={
                      <ProtectedRoute>
                        <Forum />
                      </ProtectedRoute>
                    }
                  />

                  <Route
                    path="/updateProfile"
                    element={
                      <ProtectedRoute>
                        <UpdateProfile />
                      </ProtectedRoute>
                    }
                  />

                  <Route
                    path="/instructor"
                    element={
                      <ProtectedRoute instructorOnly={true}>
                        <InstructorDashboard />
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

                  {/* ANY new valid route should be placed above this, this is the default route*/}
                  <Route
                    path="*"
                    element={
                      <ProtectedRoute >
                        <NotFound />
                      </ProtectedRoute>
                    }
                  />
                </Routes>
                </main>
                <Footer />
                </div>
            </RoleCheck>
        </BrowserRouter>
    );
}
