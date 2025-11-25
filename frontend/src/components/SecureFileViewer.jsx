import React, { useState, useEffect, useRef } from 'react'
import client from '../api/client'

// SecureFileViewer: UI-only access to file metadata, previews and streamed downloads.
// Never exposes filesystem paths or direct download URLs.
export default function SecureFileViewer({ fileId }){
  const [meta, setMeta] = useState(null)
  const [preview, setPreview] = useState(null)
  const [loading, setLoading] = useState(false)

  // Download state
  const [downloading, setDownloading] = useState(false)
  const [downloadedBytes, setDownloadedBytes] = useState(0)
  const [totalBytes, setTotalBytes] = useState(null)
  const [error, setError] = useState(null)
  const chunksRef = useRef([])
  const controllerRef = useRef(null)

  useEffect(()=>{
    if(!fileId) return
    client.get(`/secure/files/${fileId}/meta`).then(r=>setMeta(r.data)).catch(()=>setMeta(null))
  },[fileId])

  const loadPreview = async ()=>{
    setLoading(true)
    try{
      const r = await client.get(`/secure/files/${fileId}/preview`)
      setPreview(r.data.preview)
    }catch(e){
      setPreview('Failed to load preview')
    }finally{setLoading(false)}
  }

  // Start or resume a streamed download. Supports Range-resume by passing
  // the current `downloadedBytes` to the server via `Range` header.
  const startDownload = async ()=>{
    setError(null)
    setDownloading(true)
    controllerRef.current = new AbortController()
    const headers = {}
    if(downloadedBytes > 0){
      headers['Range'] = `bytes=${downloadedBytes}-`
    }

    try{
      const resp = await fetch(`/api/secure/files/${fileId}/download`, { headers, signal: controllerRef.current.signal })
      if(!resp.ok && resp.status !== 206){
        throw new Error(`Download failed: ${resp.status}`)
      }

      // Set totalBytes if provided by server
      const contentRange = resp.headers.get('Content-Range')
      if(contentRange){
        // e.g. Content-Range: bytes 0-999/12345
        const m = contentRange.match(/\/(\d+)$/)
        if(m) setTotalBytes(parseInt(m[1],10))
      } else {
        const cl = resp.headers.get('Content-Length')
        if(cl) setTotalBytes((downloadedBytes || 0) + parseInt(cl,10))
      }

      const reader = resp.body.getReader()
      chunksRef.current = chunksRef.current || []
      while(true){
        const { done, value } = await reader.read()
        if(done) break
        chunksRef.current.push(value)
        setDownloadedBytes(prev => prev + value.length)
      }

      // Assemble final blob and trigger download
      const blob = new Blob(chunksRef.current)
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = meta?.name || `${fileId}.bin`
      document.body.appendChild(a)
      a.click()
      a.remove()
      URL.revokeObjectURL(url)
    }catch(e){
      if(e.name === 'AbortError'){
        // paused by user
      }else{
        console.error(e)
        setError(e.message)
      }
    }finally{
      setDownloading(false)
    }
  }

  const pauseDownload = ()=>{
    if(controllerRef.current){
      controllerRef.current.abort()
      controllerRef.current = null
      setDownloading(false)
    }
  }

  const resetDownload = ()=>{
    pauseDownload()
    chunksRef.current = []
    setDownloadedBytes(0)
    setTotalBytes(null)
    setError(null)
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

      <div style={{marginTop:12}}>
        {!downloading && (
          <button className="btn primary" onClick={startDownload}>Download</button>
        )}
        {downloading && (
          <button className="btn" onClick={pauseDownload}>Pause</button>
        )}
        <button className="btn" onClick={resetDownload} style={{marginLeft:8}}>Reset</button>
      </div>

      <div style={{marginTop:8}}>
        <div className="muted">Downloaded: {downloadedBytes} {totalBytes ? `/ ${totalBytes}` : ''} bytes</div>
        {error && <div style={{color:'crimson',marginTop:6}}>Error: {error}</div>}
      </div>

      <div style={{marginTop:8}} className="muted">Note: This UI never exposes underlying filesystem paths or direct download links.</div>
    </div>
  )
}
