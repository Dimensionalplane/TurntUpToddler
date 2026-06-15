import React, { useState, useEffect } from 'react';
import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000/api/v1';

export default function RadioControls() {
  const [streamUrl, setStreamUrl] = useState('');
  const [status, setStatus] = useState({ is_streaming: false, current_track: null });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchStatus = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/radio/status`);
      setStatus(response.data);
    } catch (err) {
      console.error('Failed to fetch radio status:', err);
    }
  };

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleStart = async () => {
    if (!streamUrl) { setError('RTMP URL required.'); return; }
    setLoading(true); setError(null);
    try {
      const formData = new FormData();
      formData.append('stream_url', streamUrl);
      await axios.post(`${API_BASE_URL}/radio/start`, formData);
      fetchStatus();
    } catch (err) { setError('Failed to start radio.'); }
    finally { setLoading(false); }
  };

  const handleStop = async () => {
    setLoading(true);
    try {
      await axios.post(`${API_BASE_URL}/radio/stop`);
      fetchStatus();
    } catch (err) { setError('Failed to stop radio.'); }
    finally { setLoading(false); }
  };

  const handleSkip = async () => {
    try {
      await axios.post(`${API_BASE_URL}/radio/skip`);
      fetchStatus();
    } catch (err) { setError('Failed to skip track.'); }
  };

  return (
    <div style={{ border: '1px solid #ccc', padding: '1.5rem', borderRadius: '8px', marginTop: '2rem' }}>
      <h2>📻 Live DJ Radio Stream</h2>

      {!status.is_streaming ? (
        <div>
          <input
            type="text"
            placeholder="RTMP URL (e.g., YouTube Live)"
            value={streamUrl}
            onChange={(e) => setStreamUrl(e.target.value)}
            style={{ width: '100%', marginBottom: '1rem' }}
          />
          <button onClick={handleStart} disabled={loading} style={{ background: '#28a745', color: 'white', border: 'none', padding: '0.5rem 1rem', borderRadius: '4px' }}>
            Start Broadcast 📻
          </button>
        </div>
      ) : (
        <div style={{ background: '#e9f5ff', padding: '1rem', borderRadius: '4px' }}>
          <p>🟢 <strong>Status:</strong> Live Streaming</p>
          <p>🎵 <strong>Now Playing:</strong> {status.current_track || 'Waiting for track...'}</p>
          <div style={{ display: 'flex', gap: '1rem' }}>
            <button onClick={handleSkip} style={{ background: '#ffc107', border: 'none', padding: '0.5rem 1rem', borderRadius: '4px' }}>Skip Track ⏭️</button>
            <button onClick={handleStop} disabled={loading} style={{ background: '#dc3545', color: 'white', border: 'none', padding: '0.5rem 1rem', borderRadius: '4px' }}>Stop Radio ⏹️</button>
          </div>
        </div>
      )}

      {error && <p style={{ color: 'red', marginTop: '1rem' }}>{error}</p>}
    </div>
  );
}
