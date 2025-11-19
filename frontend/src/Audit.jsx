import React, {useEffect, useState} from 'react'
import axios from 'axios'

export default function Audit(){
  const [events, setEvents] = useState(null)
  const [loading, setLoading] = useState(false)
  const [token, setToken] = useState(() => localStorage.getItem('erp_admin_token') || '')
  const [tokenType, setTokenType] = useState(() => localStorage.getItem('erp_admin_token_type') || 'bearer')

  async function fetchEvents(){
    setLoading(true)
    try{
      const headers = {}
      if(token){
        if(tokenType === 'bearer') headers['Authorization'] = `Bearer ${token}`
        else headers['X-ADMIN-TOKEN'] = token
      }
      const r = await axios.get('/api/ops/audit', {headers})
      setEvents(r.data.events || [])
    }catch(e){
      setEvents([])
    }finally{
      setLoading(false)
    }
  }

  useEffect(()=>{ fetchEvents() }, [])

  function saveToken(){
    localStorage.setItem('erp_admin_token', token)
    localStorage.setItem('erp_admin_token_type', tokenType)
    fetchEvents()
  }

  return (
    <section style={{marginTop:20}}>
      <h2>Audit Events</h2>
      <div style={{marginBottom:8}}>
        <input placeholder="admin token or jwt" value={token} onChange={e=>setToken(e.target.value)} style={{width:300,marginRight:8}} />
        <select value={tokenType} onChange={e=>setTokenType(e.target.value)} style={{marginRight:8}}>
          <option value="bearer">Bearer (JWT)</option>
          <option value="legacy">X-ADMIN-TOKEN</option>
        </select>
        <button onClick={saveToken}>Save & Refresh</button>
        <button onClick={fetchEvents} disabled={loading} style={{marginLeft:8}}>{loading? 'Refreshing...':'Refresh'}</button>
      </div>
      {events === null ? <div>Loading...</div> : (
        <div style={{maxHeight:300,overflow:'auto',border:'1px solid #eee',padding:8}}>
          {events.length === 0 ? <div>No recent events</div> : (
            <table style={{width:'100%',borderCollapse:'collapse'}}>
              <thead><tr><th>Time</th><th>Action</th><th>Session</th><th>By</th><th>Raw</th></tr></thead>
              <tbody>
                {events.map((e,idx)=> (
                  <tr key={idx} style={{borderTop:'1px solid #f0f0f0'}}>
                    <td style={{padding:6}}>{e.timestamp || e.time || ''}</td>
                    <td style={{padding:6}}>{e.action || e.type || ''}</td>
                    <td style={{padding:6}}>{e.session_id || e.session || ''}</td>
                    <td style={{padding:6}}>{e.by || ''}</td>
                    <td style={{padding:6,fontFamily:'monospace',fontSize:12}}>{JSON.stringify(e)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </section>
  )
}
