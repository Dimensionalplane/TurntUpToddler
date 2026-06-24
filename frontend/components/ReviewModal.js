import React, { useState } from 'react';
import axios from 'axios';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

export default function ReviewModal({ jobId, initialData, onApproved, onCancel }) {
  const [metadata, setMetadata] = useState(initialData.metadata || {});
  const [artPrompt, setArtPrompt] = useState(initialData.art_prompt || '');
  const [lyrics, setLyrics] = useState(initialData.lyrics || []);
  const [loading, setLoading] = useState(false);

  const handleApprove = async () => {
    setLoading(true);
    try {
      await axios.post(`${API_BASE_URL}/jobs/${jobId}/review`, {
        metadata,
        art_prompt: artPrompt,
        lyrics
      });
      onApproved();
    } catch (err) {
      alert('Failed to approve content.');
    } finally {
      setLoading(false);
    }
  };

  const updateLyric = (index, text) => {
    const newLyrics = [...lyrics];
    newLyrics[index].text = text;
    setLyrics(newLyrics);
  };

  return (
    <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(0,0,0,0.7)', display: 'flex', justifyContent: 'center', alignItems: 'center', zIndex: 1000, overflowY: 'auto', padding: '2rem' }}>
      <div style={{ background: 'white', padding: '2rem', borderRadius: '8px', width: '100%', maxWidth: '800px', maxHeight: '90vh', overflowY: 'auto' }}>
        <h2>📝 Review & Edit Content: {jobId}</h2>

        <div style={{ marginBottom: '1.5rem' }}>
          <h3>Metadata</h3>
          <label>Title:</label>
          <input type="text" value={metadata.title || ''} onChange={(e) => setMetadata({...metadata, title: e.target.value})} style={{ width: '100%', marginBottom: '1rem' }} />
          <label>Description:</label>
          <textarea value={metadata.description || ''} onChange={(e) => setMetadata({...metadata, description: e.target.value})} style={{ width: '100%', height: '100px' }} />
        </div>

        <div style={{ marginBottom: '1.5rem' }}>
          <h3>DALL-E Art Prompt</h3>
          <textarea value={artPrompt} onChange={(e) => setArtPrompt(e.target.value)} style={{ width: '100%', height: '80px' }} />
        </div>

        <div style={{ marginBottom: '1.5rem' }}>
          <h3>Lyrics (Syllable Timings)</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            {lyrics.map((l, idx) => (
              <div key={idx} style={{ display: 'flex', gap: '0.5rem' }}>
                <span style={{ width: '60px', fontSize: '0.8rem', color: '#999' }}>{l.start}s</span>
                <input type="text" value={l.text} onChange={(e) => updateLyric(idx, e.target.value)} style={{ flex: 1 }} />
              </div>
            ))}
          </div>
        </div>

        <div style={{ display: 'flex', gap: '1rem', justifyContent: 'flex-end', marginTop: '2rem' }}>
          <button onClick={onCancel} style={{ padding: '0.5rem 1rem' }}>Cancel</button>
          <button onClick={handleApprove} disabled={loading} style={{ padding: '0.5rem 1rem', background: '#28a745', color: 'white', border: 'none', borderRadius: '4px' }}>
            {loading ? 'Submitting...' : 'Approve & Resume Rendering ✅'}
          </button>
        </div>
      </div>
    </div>
  );
}
