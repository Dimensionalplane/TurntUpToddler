import React, { useState } from 'react';
import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000/api/v1';

export default function HymnEditor() {
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [extractedMetadata, setExtractedMetadata] = useState(null);
  const [clusterStatus, setClusterStatus] = useState(null);
  const [error, setError] = useState(null);

  const handlePreview = async () => {
    if (!file) { setError('Select a file.'); return; }
    setLoading(true); setPreviewUrl(null); setError(null);
    const formData = new FormData(); formData.append('file', file);
    try {
      const response = await axios.post(`${API_BASE_URL}/editor/preview`, formData, { responseType: 'blob' });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      setPreviewUrl(url);
    } catch (err) { setError('Preview failed.'); }
    finally { setLoading(false); }
  };

  const handleExtract = async () => {
    if (!file) { setError('Select a MusicXML file.'); return; }
    setLoading(true); setExtractedMetadata(null); setError(null);
    const formData = new FormData(); formData.append('file', file);
    try {
      const response = await axios.post(`${API_BASE_URL}/editor/extract`, formData);
      setExtractedMetadata(response.data.metadata);
    } catch (err) { setError('Extraction failed. Ensure file is MusicXML.'); }
    finally { setLoading(false); }
  };

  const handleClusterSubmit = async () => {
    setLoading(true); setClusterStatus(null); setError(null);
    try {
      const response = await axios.post(`${API_BASE_URL}/editor/cluster/submit`);
      setClusterStatus(response.data.job_id);
    } catch (err) { setError('Cluster submission failed.'); }
    finally { setLoading(false); }
  };

  return (
    <div style={{ border: '1px solid #ccc', padding: '1.5rem', borderRadius: '8px', marginTop: '2rem' }}>
      <h2>🎹 Hymn Editor Toolbar</h2>
      <input type="file" onChange={(e) => setFile(e.target.files[0])} style={{ marginBottom: '1rem' }} />

      <div style={{ display: 'flex', gap: '1rem', marginBottom: '1rem' }}>
        <button onClick={handlePreview} disabled={loading}>Render Preview 🔊</button>
        <button onClick={handleExtract} disabled={loading}>Extract Metadata 📄</button>
        <button onClick={handleClusterSubmit} disabled={loading} style={{ background: '#ff4b4b', color: 'white', border: 'none', borderRadius: '4px' }}>Submit to Cluster 🐇</button>
      </div>

      {loading && <p>Processing...</p>}
      {error && <p style={{ color: 'red' }}>{error}</p>}

      {previewUrl && (
        <div>
          <h3>Audio Preview</h3>
          <audio src={previewUrl} controls />
        </div>
      )}

      {extractedMetadata && (
        <div style={{ background: '#f9f9f9', padding: '1rem', borderRadius: '4px' }}>
          <h3>Extracted Metadata</h3>
          <p><strong>Title:</strong> {extractedMetadata.title}</p>
          <p><strong>Composer:</strong> {extractedMetadata.composer}</p>
          {extractedMetadata.lyrics && <pre style={{ maxHeight: '200px', overflow: 'auto' }}>{JSON.stringify(extractedMetadata.lyrics, null, 2)}</pre>}
        </div>
      )}

      {clusterStatus && <p style={{ color: 'green' }}>Successfully queued to cluster! Job ID: {clusterStatus}</p>}
    </div>
  );
}
