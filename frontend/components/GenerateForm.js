import React, { useState } from 'react';
import axios from 'axios';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

export default function GenerateForm({ onJobStarted }) {
  const [file, setFile] = useState(null);
  const [style, setStyle] = useState('Deep House, high quality, electronic');
  const [generateVocals, setGenerateVocals] = useState(false);
  const [voiceId, setVoiceId] = useState('');
  const [model, setModel] = useState('eleven_multilingual_v2');
  const [videoFormat, setVideoFormat] = useState('Standard 16:9');
  const [createShorts, setCreateShorts] = useState(false);
  const [enableVisualizer, setEnableVisualizer] = useState(false);
  const [visualizerMode, setVisualizerMode] = useState('cline');
  const [kidsMode, setKidsMode] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!file) {
      setError('Please select a MIDI file.');
      return;
    }

    setLoading(true);
    setError(null);

    const formData = new FormData();
    formData.append('file', file);
    formData.append('style', style);
    formData.append('generate_vocals', generateVocals);
    formData.append('voice_id', voiceId);
    formData.append('model', model);
    formData.append('video_format', videoFormat);
    formData.append('create_shorts', createShorts);
    formData.append('enable_visualizer', enableVisualizer);
    formData.append('visualizer_mode', visualizerMode);
    formData.append('kids_mode', kidsMode);

    try {
      const response = await axios.post(`${API_BASE_URL}/generate`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      if (onJobStarted) {
        // We'd ideally return a job_id from the API, but for now we'll signal success
        onJobStarted(response.data);
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to start generation.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ border: '1px solid #ccc', padding: '1.5rem', borderRadius: '8px', marginBottom: '2rem' }}>
      <h3>🚀 Start New Generation</h3>
      <form onSubmit={handleSubmit}>
        <div style={{ marginBottom: '1rem' }}>
          <label>MIDI/MusicXML File: </label>
          <input type="file" onChange={(e) => setFile(e.target.files[0])} accept=".mid,.midi,.mxl,.xml" />
        </div>

        <div style={{ marginBottom: '1rem' }}>
          <label>Style: </label>
          <input type="text" value={style} onChange={(e) => setStyle(e.target.value)} style={{ width: '100%' }} />
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
          <div>
            <label><input type="checkbox" checked={generateVocals} onChange={(e) => setGenerateVocals(e.target.checked)} /> Generate Vocals</label>
          </div>
          <div>
            <label><input type="checkbox" checked={kidsMode} onChange={(e) => setKidsMode(e.target.checked)} /> Kids Mode 👶</label>
          </div>
          <div>
            <label><input type="checkbox" checked={createShorts} onChange={(e) => setCreateShorts(e.target.checked)} /> Create 15s Shorts</label>
          </div>
          <div>
            <label><input type="checkbox" checked={enableVisualizer} onChange={(e) => setEnableVisualizer(e.target.checked)} /> Enable Visualizer</label>
          </div>
        </div>

        <div style={{ marginTop: '1rem' }}>
          <button type="submit" disabled={loading} style={{ padding: '0.5rem 1rem', background: '#0070f3', color: '#fff', border: 'none', borderRadius: '4px', cursor: 'pointer' }}>
            {loading ? 'Processing...' : 'Start Pipeline'}
          </button>
        </div>
      </form>
      {error && <p style={{ color: 'red', marginTop: '1rem' }}>{error}</p>}
    </div>
  );
}
