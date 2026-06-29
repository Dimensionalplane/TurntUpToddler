"use client";

import React, { useState, useRef } from 'react';
import { Upload, Play, FileMusic, Loader2 } from 'lucide-react';
import axios from 'axios';
import Player from '@/components/Player';

export default function EditorPage() {
  const [file, setFile] = useState<File | null>(null);
  const [isPreviewing, setIsPreviewing] = useState(false);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setPreviewUrl(null);
    }
  };

  const handleRenderPreview = async () => {
    if (!file) return;

    setIsPreviewing(true);
    const formData = new FormData();
    formData.append("file", file);

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const res = await axios.post(`${apiUrl}/api/v1/editor/preview`, formData, {
        headers: { "Content-Type": "multipart/form-data" }
      });
      setPreviewUrl(`${apiUrl}${res.data.preview_url}`);
    } catch (err) {
      console.error(err);
      alert("Failed to render preview");
    } finally {
      setIsPreviewing(false);
    }
  };

  return (
    <div className="p-8 max-w-5xl mx-auto">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Hymn Editor (Beta)</h1>
        <p className="text-gray-600">Raw backend rendering tools for manual experimentation without running the full generative pipeline.</p>
      </div>

      <div className="grid grid-cols-1 gap-8">
        {/* File Operations */}
        <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
          <h2 className="text-xl font-bold mb-4 flex items-center gap-2">
            <FileMusic className="w-6 h-6 text-blue-600" />
            1. File Operations
          </h2>
          <p className="text-gray-600 mb-4">Load MIDI or MusicXML file for editing</p>

          <div className="flex items-center gap-4">
            <button
              onClick={() => fileInputRef.current?.click()}
              className="px-4 py-2 border border-gray-300 rounded-md hover:bg-gray-50 flex items-center gap-2"
            >
              <Upload className="w-4 h-4" />
              Choose File
            </button>
            <span className="text-gray-700 font-medium">
              {file ? file.name : "No file chosen"}
            </span>
            <input
              type="file"
              ref={fileInputRef}
              className="hidden"
              accept=".mid,.midi,.mxl,.xml"
              onChange={handleFileChange}
            />
          </div>
        </div>

        {/* Native Audio Preview */}
        <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
          <h2 className="text-xl font-bold mb-4">2. Native Audio Preview</h2>
          <p className="text-gray-600 mb-4">Use the native C++ engine to render a fast audio preview of the raw file.</p>

          <button
            onClick={handleRenderPreview}
            disabled={!file || isPreviewing}
            className={`px-6 py-3 rounded-lg flex items-center gap-2 font-medium transition ${!file || isPreviewing ? 'bg-gray-200 text-gray-500 cursor-not-allowed' : 'bg-green-600 text-white hover:bg-green-700'}`}
          >
            {isPreviewing ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                Rendering audio via C++ engine...
              </>
            ) : (
              <>
                <Play className="w-5 h-5" />
                Render Preview 🔊
              </>
            )}
          </button>

          {previewUrl && (
            <Player url={previewUrl} type="audio" title="Preview Audio" />
          )}
        </div>

        {/* Placeholder for Metadata Extraction (Phase 2) */}
        <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200 opacity-60">
          <h2 className="text-xl font-bold mb-4">3. Metadata Extraction (Coming Soon)</h2>
          <p className="text-gray-600 mb-4">Extract precise note-by-note synchronization from MusicXML files.</p>
        </div>

        {/* Cluster Rendering */}
        <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200 opacity-60">
          <h2 className="text-xl font-bold mb-4">4. Cluster Rendering (RabbitMQ)</h2>
          <p className="text-gray-600 mb-4">Submit generation jobs to a RabbitMQ render cluster.</p>
        </div>
      </div>
    </div>
  );
}
