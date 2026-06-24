import React, { useState, useEffect } from 'react';
import axios from 'axios';
import GenerateForm from '../components/GenerateForm';
import HymnEditor from '../components/HymnEditor';
import RadioControls from '../components/RadioControls';
import ReviewModal from '../components/ReviewModal';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

export default function Home() {
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeJobs, setActiveJobs] = useState([]);
  const [reviewJob, setReviewJob] = useState(null);

  const pollJobStatus = async (jobId) => {
    try {
      const response = await axios.get(`${API_BASE_URL}/jobs/${jobId}`);
      const { status, progress, message } = response.data;

      setActiveJobs(prev => prev.map(job =>
        job.id === jobId ? { ...job, status, progress, lastMessage: message } : job
      ));

      if (status === 'awaiting_review') {
        // Trigger review UI
        const reviewResponse = await axios.get(`${API_BASE_URL}/jobs/${jobId}/review`);
        setReviewJob({ id: jobId, data: reviewResponse.data });
      }

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

  const handleRetry = async (jobId) => {
    try {
      const response = await axios.post(`${API_BASE_URL}/jobs/${jobId}/retry`);
      if (response.data.new_job_id) {
        setActiveJobs(prev => [...prev, { id: response.data.new_job_id, status: 'queued' }]);
      }
    } catch (err) {
      console.error('Failed to retry job:', err);
      alert('Failed to retry job.');
    }
  };

  return (
    <div style={{ padding: '2rem', fontFamily: 'sans-serif', maxWidth: '1200px', margin: '0 auto' }}>
      <h1>🎵 Hymn Remaker Dashboard</h1>
      <p>Modernizing hymns with AI.</p>

      <GenerateForm onJobStarted={handleJobStarted} />

      <RadioControls />

      <HymnEditor />

      {reviewJob && (
        <ReviewModal
          jobId={reviewJob.id}
          initialData={reviewJob.data}
          onApproved={() => {
            setReviewJob(null);
            pollJobStatus(reviewJob.id);
          }}
          onCancel={() => setReviewJob(null)}
        />
      )}

      {activeJobs.length > 0 && (
        <section style={{ marginBottom: '2rem' }}>
          <h2>Background Tasks</h2>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            {activeJobs.map(job => (
              <div key={job.id} style={{
                background: job.status === 'completed' ? '#f6fff6' : (job.status === 'failed' ? '#fff6f6' : '#f0f7ff'),
                padding: '1rem',
                borderRadius: '8px',
                border: '1px solid #eee'
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                  <strong>Job ID:</strong> <code style={{ fontSize: '0.8rem' }}>{job.id}</code>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    {job.status === 'failed' && (
                      <button
                        onClick={() => handleRetry(job.id)}
                        style={{ fontSize: '0.7rem', padding: '0.2rem 0.4rem', cursor: 'pointer', background: '#fff', border: '1px solid #721c24', color: '#721c24', borderRadius: '4px' }}
                      >
                        Retry 🔄
                      </button>
                    )}
                    <div style={{
                      textTransform: 'uppercase',
                      fontSize: '0.75rem',
                      fontWeight: 'bold',
                      padding: '0.2rem 0.6rem',
                      borderRadius: '10px',
                      background: job.status === 'completed' ? '#d4edda' : (job.status === 'failed' ? '#f8d7da' : (job.status === 'awaiting_review' ? '#fff3cd' : '#cce5ff')),
                      color: job.status === 'completed' ? '#155724' : (job.status === 'failed' ? '#721c24' : (job.status === 'awaiting_review' ? '#856404' : '#004085'))
                    }}>
                      {job.status.replace('_', ' ')}
                    </div>
                  </div>
                </div>
                {job.status !== 'completed' && job.status !== 'failed' && (
                  <div style={{ marginBottom: '0.5rem' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <small style={{ fontWeight: 'bold', color: '#004085' }}>{job.lastMessage || 'Queued...'}</small>
                      <small style={{ color: '#004085' }}>{job.progress || 0}%</small>
                    </div>
                    <div style={{ width: '100%', height: '8px', background: '#ddd', borderRadius: '4px', overflow: 'hidden', marginTop: '0.3rem' }}>
                      <div style={{ width: `${job.progress || 0}%`, height: '100%', background: job.status === 'awaiting_review' ? '#ffc107' : '#0070f3', transition: 'width 0.3s ease' }}></div>
                    </div>
                  </div>
                )}
                {job.status === 'failed' && (
                  <small style={{ color: '#721c24', marginTop: '0.3rem', display: 'block' }}>{job.lastMessage || 'Failed'}</small>
                )}
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
              <h3 style={{ marginTop: 0 }}>{item.hymn_name || 'Untitled Hymn'}</h3>
              <p style={{ color: '#666', fontSize: '0.9rem' }}>{item.style}</p>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '1rem' }}>
                <small style={{ color: '#999' }}>{new Date(item.date_created).toLocaleString()}</small>
                <div style={{ display: 'flex', gap: '0.5rem' }}>
                  {item.remote_video_url ? (
                      <a href={item.remote_video_url} target="_blank" rel="noreferrer" style={{ color: '#0070f3', textDecoration: 'none', fontWeight: 'bold' }}>S3 🎥</a>
                  ) : item.video_path && (
                      <a href={`${API_BASE_URL.replace('/api/v1', '')}/output/${item.video_path.split('/').pop()}`} target="_blank" rel="noreferrer" style={{ color: '#0070f3', textDecoration: 'none', fontWeight: 'bold' }}>Local 🎥</a>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
