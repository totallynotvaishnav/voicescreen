import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import ProtectedRoute from './components/ProtectedRoute';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import Jobs from './pages/Jobs';
import JobDetail from './pages/JobDetail';
import CandidateDetail from './pages/CandidateDetail';
import Login from './pages/Login';
import Register from './pages/Register';

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          
          <Route path="/" element={
            <ProtectedRoute>
              <Layout>
                <Dashboard />
              </Layout>
            </ProtectedRoute>
          } />
          
          <Route path="/jobs" element={
            <ProtectedRoute>
              <Layout>
                <Jobs />
              </Layout>
            </ProtectedRoute>
          } />
          
          <Route path="/jobs/:id" element={
            <ProtectedRoute>
              <Layout>
                <JobDetail />
              </Layout>
            </ProtectedRoute>
          } />
          
          <Route path="/candidates/:id" element={
            <ProtectedRoute>
              <Layout>
                <CandidateDetail />
              </Layout>
            </ProtectedRoute>
          } />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;
