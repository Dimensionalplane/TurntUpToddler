"use client";

import React from 'react';
import { Home, Music, Settings, Radio, Info } from 'lucide-react';
import Link from 'next/link';
import { useSettings } from '@/context/SettingsContext';

export default function Sidebar() {
  const {
    generateVocals, setGenerateVocals,
    normalizeAudio, setNormalizeAudio,
    kidsMode, setKidsMode,
    useAdvancedVideo, setUseAdvancedVideo,
    stylePrompt, setStylePrompt,
    interactiveMode, setInteractiveMode,
    remakePriority, setRemakePriority
  } = useSettings();

  return (
    <div className="w-64 h-screen bg-gray-900 text-white flex flex-col p-4">
      <div className="mb-8">
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Music className="w-6 h-6" />
          Hymn Remaker
        </h1>
        <p className="text-sm text-gray-400 mt-2">v5.39.0</p>
      </div>

      <nav className="flex-1 space-y-2">
        <Link href="/" className="flex items-center gap-3 p-3 rounded hover:bg-gray-800 transition">
          <Home className="w-5 h-5" />
          Pipeline
        </Link>
        <Link href="/editor" className="flex items-center gap-3 p-3 rounded hover:bg-gray-800 transition">
          <Music className="w-5 h-5" />
          Editor
        </Link>
        <Link href="/radio" className="flex items-center gap-3 p-3 rounded hover:bg-gray-800 transition">
          <Radio className="w-5 h-5" />
          Radio Streamer
        </Link>
      </nav>

      <div className="mt-auto border-t border-gray-800 pt-4 overflow-y-auto">
        <h2 className="text-sm font-semibold text-gray-400 mb-2 uppercase tracking-wider">Quick Settings</h2>

        <div className="space-y-3">
          <label className="flex flex-col gap-1 text-sm mb-4">
            <span className="text-gray-400 flex items-center gap-1">Style Prompt <span title="Describe the musical genre or mood for the generated song (e.g., 'Deep House, upbeat'). This is passed to MusicGen/Replicate."><Info className="w-3 h-3 text-gray-500 cursor-help" /></span></span>
            <textarea
              className="rounded bg-gray-800 border-gray-700 p-2 text-white outline-none focus:ring-1 focus:ring-blue-500 resize-none"
              rows={2}
              value={stylePrompt}
              onChange={(e) => setStylePrompt(e.target.value)}
              placeholder="e.g. Deep House, high quality..."
            />
          </label>
          <label className="flex flex-col gap-1 text-sm mb-4">
            <span className="text-gray-400 flex items-center gap-1">Remake AI Engine <span title="Select which AI model handles the musical generation."><Info className="w-3 h-3 text-gray-500 cursor-help" /></span></span>
            <select
              className="rounded bg-gray-800 border-gray-700 p-2 text-white outline-none focus:ring-1 focus:ring-blue-500"
              value={remakePriority}
              onChange={(e) => setRemakePriority(e.target.value as "suno" | "replicate")}
            >
              <option value="suno">Suno AI (v3)</option>
              <option value="replicate">Replicate (MusicGen)</option>
            </select>
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              className="rounded bg-gray-800 border-gray-700"
              checked={interactiveMode}
              onChange={(e) => setInteractiveMode(e.target.checked)}
            />
            Interactive Review Mode <span title="Pauses the generation pipeline after metadata extraction, allowing you to edit the generated title, style, and lyrics before rendering."><Info className="w-3 h-3 text-gray-500 cursor-help" /></span>
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              className="rounded bg-gray-800 border-gray-700"
              checked={generateVocals}
              onChange={(e) => setGenerateVocals(e.target.checked)}
            />
            Generate Vocals <span title="Uses ElevenLabs to generate a synthetic vocal track matching the lyrics, which is then time-stretched and mixed into the final instrumental."><Info className="w-3 h-3 text-gray-500 cursor-help" /></span>
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              className="rounded bg-gray-800 border-gray-700"
              checked={normalizeAudio}
              onChange={(e) => setNormalizeAudio(e.target.checked)}
            />
            Normalize Audio <span title="Applies dynamic range compression and volume normalization to the final audio output to ensure consistent loudness."><Info className="w-3 h-3 text-gray-500 cursor-help" /></span>
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              className="rounded bg-gray-800 border-gray-700"
              checked={kidsMode}
              onChange={(e) => setKidsMode(e.target.checked)}
            />
            Kids Mode 👶 <span title="Enforces child-safe metadata filtering, alters the styling prompt to be playful/nursery-rhyme focused, and enables COPPA-compliant YouTube uploads."><Info className="w-3 h-3 text-gray-500 cursor-help" /></span>
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              className="rounded bg-gray-800 border-gray-700"
              checked={useAdvancedVideo}
              onChange={(e) => setUseAdvancedVideo(e.target.checked)}
            />
            Advanced AI Video <span title="Uses advanced generative video AI (like Luma or Runway) for dynamic background videos instead of a static DALL-E cover art image."><Info className="w-3 h-3 text-gray-500 cursor-help" /></span>
          </label>
        </div>
      </div>
    </div>
  );
}
