import React, { useState, useEffect } from 'react';
import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000/api/v1';

export default function Home() {
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchHistory = async () => {
      try {
        const response = await axios.get(`${API_BASE_URL}/history`);
        setHistory(response.data.data);
      } catch (err) {
        setError('Failed to fetch generation history.');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchHistory();
  }, []);

  return (
    <div style={{ padding: '2rem', fontFamily: 'sans-serif' }}>
      <h1>🎵 Hymn Remaker Dashboard</h1>
      <p>Modernizing hymns with AI.</p>

      <section>
        <h2>Generation History</h2>
        {loading && <p>Loading history...</p>}
        {error && <p style={{ color: 'red' }}>{error}</p>}
        {!loading && history.length === 0 && <p>No hymns generated yet.</p>}

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '1rem' }}>
          {history.map((item, index) => (
            <div key={index} style={{ border: '1px solid #ddd', padding: '1rem', borderRadius: '8px' }}>
              <h3>{item.title || 'Untitled Hymn'}</h3>
              <p>{item.description}</p>
              <small>Generated on: {new Date(item.timestamp).toLocaleString()}</small>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
