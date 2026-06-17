import React, { useState, useEffect } from 'react';
import axios from 'axios';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

export default function GenerateForm({ onJobStarted }) {
  const [file, setFile] = useState(null);
  const [presets, setPresets] = useState({});
  const [style, setStyle] = useState('Auto');

  useEffect(() => {
    const fetchPresets = async () => {
      try {
        const response = await axios.get(`${API_BASE_URL}/config/presets`);
        setPresets(response.data.presets || {});
      } catch (err) {
        console.error('Failed to fetch style presets:', err);
      }
    };
    fetchPresets();
  }, []);
  const [generateVocals, setGenerateVocals] = useState(false);
  const [voiceId, setVoiceId] = useState('');
  const [model, setModel] = useState('eleven_multilingual_v2');
  const [videoFormat, setVideoFormat] = useState('Standard 16:9');
  const [resolution, setResolution] = useState('1080p');
  const [createShorts, setCreateShorts] = useState(false);
  const [enableVisualizer, setEnableVisualizer] = useState(false);
  const [visualizerMode, setVisualizerMode] = useState('cline');
  const [kidsMode, setKidsMode] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [interactiveMode, setInteractiveMode] = useState(false);
  const [arrangementStyle, setArrangementStyle] = useState('Original');
  const [remakePriority, setRemakePriority] = useState('suno');
  const [sunoSession, setSunoSession] = useState('');
  const [normalizeAudio, setNormalizeAudio] = useState(true);
  const [fadeInMs, setFadeInMs] = useState(0);
  const [fadeOutMs, setFadeOutMs] = useState(0);

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
    formData.append('resolution', resolution);
    formData.append('create_shorts', createShorts);
    formData.append('enable_visualizer', enableVisualizer);
    formData.append('visualizer_mode', visualizerMode);
    formData.append('kids_mode', kidsMode);
    formData.append('normalize_audio', normalizeAudio);
    formData.append('fade_in_ms', fadeInMs);
    formData.append('fade_out_ms', fadeOutMs);
    formData.append('arrangement_style', arrangementStyle);
    formData.append('interactive_mode', interactiveMode);
    formData.append('remake_priority', remakePriority);
    formData.append('suno_session', sunoSession);

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
          <label>Style Preset: </label>
          <select
            onChange={(e) => {
              if (e.target.value !== 'custom') {
                setStyle(presets[e.target.value]);
              }
            }}
            style={{ width: '100%', marginBottom: '0.5rem' }}
          >
            <option value="custom">-- Select a Preset (or type below) --</option>
            {Object.keys(presets).map(p => (
              <option key={p} value={p}>{p}</option>
            ))}
          </select>
          <label>Style Prompt: </label>
          <input type="text" value={style} onChange={(e) => setStyle(e.target.value)} style={{ width: '100%' }} />
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1rem' }}>
          <div>
            <label>Voice ID: </label>
            <input type="text" value={voiceId} onChange={(e) => setVoiceId(e.target.value)} style={{ width: '100%' }} />
          </div>
          <div>
            <label>TTS Model: </label>
            <select value={model} onChange={(e) => setModel(e.target.value)} style={{ width: '100%' }}>
              <option value="eleven_multilingual_v2">Multilingual v2</option>
              <option value="eleven_monolingual_v1">Monolingual v1</option>
              <option value="eleven_turbo_v2">Turbo v2</option>
            </select>
          </div>
          <div>
            <label>Remake Priority: </label>
            <select value={remakePriority} onChange={(e) => setRemakePriority(e.target.value)} style={{ width: '100%' }}>
              <option value="suno">Suno AI</option>
              <option value="replicate">Replicate</option>
            </select>
          </div>
          <div>
            <label>Video Format: </label>
            <select value={videoFormat} onChange={(e) => setVideoFormat(e.target.value)} style={{ width: '100%' }}>
              <option value="Standard 16:9">Standard 16:9</option>
              <option value="Vertical 9:16 (TikTok/Reels)">Vertical 9:16</option>
            </select>
          </div>
          <div>
            <label>Resolution: </label>
            <select value={resolution} onChange={(e) => setResolution(e.target.value)} style={{ width: '100%' }}>
              <option value="1080p">1080p (FHD)</option>
              <option value="4K">4K (UHD)</option>
            </select>
          </div>
          <div>
            <label>Arrangement (OMR): </label>
            <select value={arrangementStyle} onChange={(e) => setArrangementStyle(e.target.value)} style={{ width: '100%' }}>
              <option value="Original">Original</option>
              <option value="Swing">Swing</option>
              <option value="Lullaby">Lullaby / Soft</option>
            </select>
          </div>
        </div>

        <div style={{ marginBottom: '1rem' }}>
          <label>Suno Session Token: </label>
          <input type="password" value={sunoSession} onChange={(e) => setSunoSession(e.target.value)} style={{ width: '100%' }} />
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
          <div>
            <label><input type="checkbox" checked={normalizeAudio} onChange={(e) => setNormalizeAudio(e.target.checked)} /> Normalize Volume</label>
          </div>
          <div>
            <label><input type="checkbox" checked={interactiveMode} onChange={(e) => setInteractiveMode(e.target.checked)} /> <b>Interactive Review Mode</b></label>
          </div>
        </div>

        <div style={{ display: 'flex', gap: '1rem', marginTop: '1rem' }}>
          <div style={{ flex: 1 }}>
            <label style={{ fontSize: '0.8rem', display: 'block' }}>Fade In (ms)</label>
            <input type="number" value={fadeInMs} onChange={(e) => setFadeInMs(e.target.value)} style={{ width: '100%' }} />
          </div>
          <div style={{ flex: 1 }}>
            <label style={{ fontSize: '0.8rem', display: 'block' }}>Fade Out (ms)</label>
            <input type="number" value={fadeOutMs} onChange={(e) => setFadeOutMs(e.target.value)} style={{ width: '100%' }} />
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
