import React, { useState, useEffect } from 'react'
import client from '../api/client'

// SecureFileViewer: UI-only access to file metadata and previews.
// Never exposes filesystem paths or direct download URLs.
export default function SecureFileViewer({ fileId }){
  const [meta, setMeta] = useState(null)
  const [preview, setPreview] = useState(null)
  const [loading, setLoading] = useState(false)

  useEffect(()=>{
    if(!fileId) return
    client.get(`/secure/files/${fileId}/meta`).then(r=>setMeta(r.data)).catch(()=>setMeta(null))
  },[fileId])

  const loadPreview = async ()=>{
    setLoading(true)
    try{
      // server should return a safe preview (no paths, only sanitized content)
      const r = await client.get(`/secure/files/${fileId}/preview`)
      setPreview(r.data.preview)
    }catch(e){
      setPreview('Failed to load preview')
    }finally{setLoading(false)}
  }

  if(!fileId) return <div className="card">Select a file to view details</div>
  return (
    <div className="card">
      <h3>{meta?.name || 'Protected file'}</h3>
      <div className="muted">Type: {meta?.type || 'unknown'}</div>
      <div className="muted">Stored: {meta?.created_at || 'n/a'}</div>
      <div style={{marginTop:12}}>
        <button className="btn" onClick={loadPreview} disabled={loading}>Preview</button>
      </div>
      {preview && (
        <div style={{marginTop:12,whiteSpace:'pre-wrap',background:'#fafafa',padding:12,borderRadius:6}}>{preview}</div>
      )}
      <div style={{marginTop:8}} className="muted">Note: This UI never exposes underlying filesystem paths or direct download links.</div>
    </div>
  )
}
