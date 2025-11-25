import React from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import TopNav from './components/TopNav'
import Sidebar from './components/Sidebar'
import Dashboard from './pages/Dashboard'
import DatabaseManager from './pages/DatabaseManager'
import EnvironmentManager from './pages/EnvironmentManager'
import AuthRoles from './pages/AuthRoles'
import Backup from './pages/Backup'
import Modules from './pages/Modules'
import MessageBus from './pages/MessageBus'

export default function App() {
  return (
    <BrowserRouter>
      <div className="app-root">
        <TopNav />
        <div className="app-body">
          <Sidebar />
          <main className="app-main">
            <Routes>
              <Route path="/" element={<Navigate to="/dashboard" replace />} />
              <Route path="/dashboard" element={<Dashboard />} />
              <Route path="/database" element={<DatabaseManager />} />
              <Route path="/environment" element={<EnvironmentManager />} />
              <Route path="/auth" element={<AuthRoles />} />
              <Route path="/backup" element={<Backup />} />
              <Route path="/modules" element={<Modules />} />
              <Route path="/messages" element={<MessageBus />} />
            </Routes>
          </main>
        </div>
      </div>
    </BrowserRouter>
  )
}

