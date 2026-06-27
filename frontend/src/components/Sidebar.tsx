import React from 'react';
import { Home, Music, Settings, Radio } from 'lucide-react';
import Link from 'next/link';

export default function Sidebar() {
  return (
    <div className="w-64 h-screen bg-gray-900 text-white flex flex-col p-4">
      <div className="mb-8">
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Music className="w-6 h-6" />
          Hymn Remaker
        </h1>
        <p className="text-sm text-gray-400 mt-2">v5.38.0</p>
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

      <div className="mt-auto border-t border-gray-800 pt-4">
        <h2 className="text-sm font-semibold text-gray-400 mb-2 uppercase tracking-wider">Quick Settings</h2>

        <div className="space-y-3">
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" className="rounded bg-gray-800 border-gray-700" />
            Generate Vocals
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" className="rounded bg-gray-800 border-gray-700" defaultChecked />
            Normalize Audio
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" className="rounded bg-gray-800 border-gray-700" />
            Kids Mode 👶
          </label>
        </div>
      </div>
    </div>
  );
}
