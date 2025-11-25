import React from 'react'
import { createRoot } from 'react-dom/client'
import App from './App'
import './index.css'

const container = document.getElementById('root') || document.body.appendChild(document.createElement('div'))
container.id = 'root'
createRoot(container).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
)
