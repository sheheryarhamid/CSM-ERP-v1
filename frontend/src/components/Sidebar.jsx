import React from 'react'
import { Link } from 'react-router-dom'

export default function Sidebar(){
  return (
    <aside className="sidebar">
      <nav>
        <Link className="nav-link" to="/dashboard">Dashboard</Link>
        <Link className="nav-link" to="/database">Database Manager</Link>
        <Link className="nav-link" to="/environment">Environment Manager</Link>
        <Link className="nav-link" to="/auth">Auth & Roles</Link>
        <Link className="nav-link" to="/backup">Backup</Link>
        <Link className="nav-link" to="/modules">Modules</Link>
        <Link className="nav-link" to="/messages">Message Bus</Link>
      </nav>
    </aside>
  )
}
