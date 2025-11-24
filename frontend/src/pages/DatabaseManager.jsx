import React, { useState, useEffect } from 'react'
import client from '../api/client'
import SecureFileViewer from '../components/SecureFileViewer'

export default function DatabaseManager(){
  const [files, setFiles] = useState([])
  const [selected, setSelected] = useState(null)

  useEffect(()=>{
    // list files via secure API (server must enforce permissions)
    client.get('/secure/files').then(r=>setFiles(r.data)).catch(()=>setFiles([]))
  },[])

  return (
    <div style={{display:'grid',gridTemplateColumns:'360px 1fr',gap:16}}>
      <div className="card">
        <h3>Database Files</h3>
        <ul className="file-list">
          {files.length===0 && <li className="muted">No files detected (UI-only demo)</li>}
          {files.map(f=> (
            <li key={f.id} className="file-item">
              <div>
                <div style={{fontWeight:600}}>{f.name}</div>
                <div className="muted">{f.type} • {f.size_human}</div>
              </div>
              <div>
                <button className="btn" onClick={()=>setSelected(f.id)}>View</button>
              </div>
            </li>
          ))}
        </ul>
      </div>
      <div>
        <SecureFileViewer fileId={selected} />
      </div>
    </div>
  )
}
