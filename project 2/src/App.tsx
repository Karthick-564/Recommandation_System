import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import LandingPage from './components/LandingPage';
import StudentSignup from './components/StudentSignup';
import NGOSignup from './components/NGOSignup';
import StudentDashboard from './components/StudentDashboard';
import NGODashboard from './components/NGODashboard';
import ApplicationFlow from './components/ApplicationFlow';
import { DataProvider } from './context/DataContext';

function App() {
  return (
    <DataProvider>
      <Router>
        <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50">
          <Routes>
            <Route path="/" element={<LandingPage />} />
            <Route path="/student/signup" element={<StudentSignup />} />
            <Route path="/ngo/signup" element={<NGOSignup />} />
            <Route path="/student/dashboard" element={<StudentDashboard />} />
            <Route path="/ngo/dashboard" element={<NGODashboard />} />
            <Route path="/apply/:opportunityId" element={<ApplicationFlow />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </div>
      </Router>
    </DataProvider>
  );
}

export default App;