import React, { useState, useEffect } from 'react';
import axios from 'axios';
import GenerateForm from '../components/GenerateForm';
import HymnEditor from '../components/HymnEditor';
import RadioControls from '../components/RadioControls';

const API_BASE_URL = 'http://localhost:8000/api/v1';

export default function Home() {
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeJobs, setActiveJobs] = useState([]);

  const fetchHistory = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/history`);
      setHistory(response.data.data);
    } catch (err) {
      console.error('Failed to fetch history:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHistory();
    const interval = setInterval(fetchHistory, 10000); // Poll history every 10s
    return () => clearInterval(interval);
  }, []);

  const handleJobStarted = (data) => {
    if (data.job_id) {
      setActiveJobs(prev => [...prev, { id: data.job_id, status: 'queued' }]);
    }
    fetchHistory();
  };

  return (
    <div style={{ padding: '2rem', fontFamily: 'sans-serif', maxWidth: '1200px', margin: '0 auto' }}>
      <h1>🎵 Hymn Remaker Dashboard</h1>
      <p>Modernizing hymns with AI.</p>

      <GenerateForm onJobStarted={handleJobStarted} />

      <RadioControls />

      <HymnEditor />

      {activeJobs.length > 0 && (
        <section style={{ marginBottom: '2rem' }}>
          <h2>Active Jobs</h2>
          {activeJobs.map(job => (
            <div key={job.id} style={{ background: '#f0f7ff', padding: '1rem', borderRadius: '8px', marginBottom: '0.5rem' }}>
              <strong>Job ID:</strong> {job.id} | <strong>Status:</strong> {job.status}
            </div>
          ))}
        </section>
      )}

      <section>
        <h2>Generation History</h2>
        {loading && <p>Loading history...</p>}
        {error && <p style={{ color: 'red' }}>{error}</p>}
        {!loading && history.length === 0 && <p>No hymns generated yet.</p>}

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(350px, 1fr))', gap: '1.5rem' }}>
          {history.map((item, index) => (
            <div key={index} style={{ border: '1px solid #ddd', padding: '1rem', borderRadius: '8px', boxShadow: '0 2px 4px rgba(0,0,0,0.05)' }}>
              <h3 style={{ marginTop: 0 }}>{item.title || 'Untitled Hymn'}</h3>
              <p style={{ color: '#666', fontSize: '0.9rem' }}>{item.description}</p>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <small style={{ color: '#999' }}>{new Date(item.timestamp).toLocaleString()}</small>
                {item.video_url && (
                    <a href={item.video_url} target="_blank" rel="noreferrer" style={{ color: '#0070f3', textDecoration: 'none', fontWeight: 'bold' }}>View Video 🎥</a>
                )}
              </div>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
