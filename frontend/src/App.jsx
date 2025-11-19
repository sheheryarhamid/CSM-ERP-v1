import React, {useEffect, useState} from 'react'
import axios from 'axios'
import Audit from './Audit'

export default function App(){
  const [health, setHealth] = useState(null)
  const [clients, setClients] = useState(null)

  useEffect(()=>{
    axios.get('/health').then(r=>setHealth(r.data)).catch(()=>setHealth(null))
    axios.get('/api/health/clients').then(r=>setClients(r.data)).catch(()=>setClients(null))
  },[])

  function terminate(sessionId){
    axios.post(`/api/clients/${sessionId}/terminate`).then(r=>{
      // refresh clients
      axios.get('/api/health/clients').then(r=>setClients(r.data)).catch(()=>setClients(null))
    }).catch(e=>alert('Terminate failed'))
  }

  return (
    <div style={{fontFamily:'sans-serif',padding:20}}>
      <h1>Central ERP Hub — Dev UI</h1>
      <section>
        <h2>Health</h2>
        <pre>{health ? JSON.stringify(health,null,2) : 'No response'}</pre>
      </section>
      <section>
        <h2>Connected Clients</h2>
        {clients ? (
          <div>
            <div>Total sessions: {clients.total_active_sessions} | Active users: {clients.total_active_users} | Last: {clients.last_refresh}</div>
            <table style={{width:'100%',marginTop:8,borderCollapse:'collapse'}}>
              <thead><tr><th>Session</th><th>User</th><th>Role</th><th>Device</th><th>Store</th><th>Module</th><th>Last Activity</th><th>Action</th></tr></thead>
              <tbody>
                {clients.sessions.map(s=>(
                  <tr key={s.session_id} style={{borderTop:'1px solid #ddd'}}>
                    <td style={{padding:6}}>{s.session_id}</td>
                    <td style={{padding:6}}>{s.user}</td>
                    <td style={{padding:6}}>{s.role}</td>
                    <td style={{padding:6}}>{s.device}</td>
                    <td style={{padding:6}}>{s.store}</td>
                    <td style={{padding:6}}>{s.module}</td>
                    <td style={{padding:6}}>{s.last_activity}</td>
                    <td style={{padding:6}}><button onClick={()=>terminate(s.session_id)}>Terminate</button></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <pre>No response</pre>
        )}
      </section>
      <Audit />
    </div>
  )
}
