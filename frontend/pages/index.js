import React, { useState, useEffect } from 'react';
import axios from 'axios';
import GenerateForm from '../components/GenerateForm';
import HymnEditor from '../components/HymnEditor';
import RadioControls from '../components/RadioControls';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

export default function Home() {
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeJobs, setActiveJobs] = useState([]);

  const pollJobStatus = async (jobId) => {
    try {
      const response = await axios.get(`${API_BASE_URL}/jobs/${jobId}`);
      const status = response.data.status;

      setActiveJobs(prev => prev.map(job =>
        job.id === jobId ? { ...job, status } : job
      ));

      if (status === 'completed' || status === 'failed') {
        fetchHistory();
        return true; // Stop polling
      }
      return false;
    } catch (err) {
      console.error(`Failed to poll job ${jobId}:`, err);
      return true; // Stop polling on error
    }
  };

  useEffect(() => {
    const pollingIntervals = {};

    activeJobs.forEach(job => {
      if (job.status !== 'completed' && job.status !== 'failed' && !pollingIntervals[job.id]) {
        pollingIntervals[job.id] = setInterval(async () => {
          const shouldStop = await pollJobStatus(job.id);
          if (shouldStop) clearInterval(pollingIntervals[job.id]);
        }, 3000);
      }
    });

    return () => {
      Object.values(pollingIntervals).forEach(clearInterval);
    };
  }, [activeJobs]);

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
          <h2>Background Tasks</h2>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            {activeJobs.map(job => (
              <div key={job.id} style={{
                background: job.status === 'completed' ? '#f6fff6' : (job.status === 'failed' ? '#fff6f6' : '#f0f7ff'),
                padding: '1rem',
                borderRadius: '8px',
                border: '1px solid #eee',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center'
              }}>
                <div>
                  <strong>Job ID:</strong> <code style={{ fontSize: '0.8rem' }}>{job.id}</code>
                </div>
                <div style={{
                  textTransform: 'uppercase',
                  fontSize: '0.75rem',
                  fontWeight: 'bold',
                  padding: '0.2rem 0.6rem',
                  borderRadius: '10px',
                  background: job.status === 'completed' ? '#d4edda' : (job.status === 'failed' ? '#f8d7da' : '#cce5ff'),
                  color: job.status === 'completed' ? '#155724' : (job.status === 'failed' ? '#721c24' : '#004085')
                }}>
                  {job.status}
                </div>
              </div>
            ))}
          </div>
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
