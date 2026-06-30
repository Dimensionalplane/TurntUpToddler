"use client";

import React, { useState, useRef } from 'react';
import { Upload, Play, FileMusic, Loader2, FileJson, Server, Info } from 'lucide-react';
import axios from 'axios';
import Player from '@/components/Player';

export default function EditorPage() {
  const [file, setFile] = useState<File | null>(null);
  const [isPreviewing, setIsPreviewing] = useState(false);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [isExtracting, setIsExtracting] = useState(false);
  const [metadataResult, setMetadataResult] = useState<any>(null);
  const [isQueueing, setIsQueueing] = useState(false);
  const [clusterResult, setClusterResult] = useState<any>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setPreviewUrl(null);
      setMetadataResult(null);
      setClusterResult(null);
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


  const handleExtractMetadata = async () => {
    if (!file) return;

    setIsExtracting(true);
    const formData = new FormData();
    formData.append("file", file);

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const res = await axios.post(`${apiUrl}/api/v1/editor/metadata`, formData, {
        headers: { "Content-Type": "multipart/form-data" }
      });
      setMetadataResult(res.data.metadata);
    } catch (err: any) {
      console.error(err);
      alert(err.response?.data?.message || "Failed to extract metadata");
    } finally {
      setIsExtracting(false);
    }
  };

  const handleQueueCluster = async () => {
    if (!file) return;

    setIsQueueing(true);
    const formData = new FormData();
    formData.append("file", file);

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const res = await axios.post(`${apiUrl}/api/v1/editor/cluster`, formData, {
        headers: { "Content-Type": "multipart/form-data" }
      });
      setClusterResult(res.data);
    } catch (err: any) {
      console.error(err);
      alert(err.response?.data?.message || "Failed to queue job");
    } finally {
      setIsQueueing(false);
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
            <span title="Load a .mid, .midi, .mxl, or .xml file to experiment with raw rendering tools without running the full automated pipeline."><Info className="w-5 h-5 text-blue-500 cursor-help" /></span>
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
          <h2 className="text-xl font-bold mb-4 flex items-center gap-2">2. Native Audio Preview <span title="Uses the custom C++ Pybind11 FluidSynth engine to perform a fast, offline rendering of the loaded file into a WAV format for immediate playback."><Info className="w-5 h-5 text-blue-500 cursor-help" /></span></h2>
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

                {/* Metadata Extraction */}
        <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
          <h2 className="text-xl font-bold mb-4 flex items-center gap-2">
            3. Metadata Extraction
            <span title="This feature allows you to extract precise note-by-note synchronization timestamps, titles, and composer information directly from .mxl and .xml files without generating audio."><Info className="w-5 h-5 text-blue-500 cursor-help" /></span>
          </h2>
          <p className="text-gray-600 mb-4 flex items-center gap-2">
            <FileJson className="w-4 h-4 text-gray-400" />
            Extract precise note-by-note synchronization from MusicXML files. Upload an .mxl file to see detailed timestamp metadata.
          </p>

          <button
            onClick={handleExtractMetadata}
            disabled={!file || isExtracting}
            className={`px-6 py-3 rounded-lg flex items-center gap-2 font-medium transition ${!file || isExtracting ? 'bg-gray-200 text-gray-500 cursor-not-allowed' : 'bg-blue-600 text-white hover:bg-blue-700'}`}
          >
            {isExtracting ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                Extracting...
              </>
            ) : (
              <>
                <FileJson className="w-5 h-5" />
                Extract Metadata
              </>
            )}
          </button>

          {metadataResult && (
            <div className="mt-4 p-4 bg-gray-50 rounded-lg overflow-auto max-h-64 text-sm border border-gray-200">
              <pre className="text-gray-800">{JSON.stringify(metadataResult, null, 2)}</pre>
            </div>
          )}
        </div>

                {/* Cluster Rendering */}
        <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
          <h2 className="text-xl font-bold mb-4 flex items-center gap-2">
            4. Cluster Rendering (RabbitMQ)
            <span title="Submits a headless rendering job to a RabbitMQ queue, allowing multiple worker nodes to pick up and process heavy tasks in parallel asynchronously."><Info className="w-5 h-5 text-purple-500 cursor-help" /></span>
          </h2>
          <p className="text-gray-600 mb-4 flex items-center gap-2">
            <Server className="w-4 h-4 text-gray-400" />
            Submit generation jobs to a RabbitMQ render cluster. Ideal for heavy workloads and parallel processing.
          </p>

          <button
            onClick={handleQueueCluster}
            disabled={!file || isQueueing}
            className={`px-6 py-3 rounded-lg flex items-center gap-2 font-medium transition ${!file || isQueueing ? 'bg-gray-200 text-gray-500 cursor-not-allowed' : 'bg-purple-600 text-white hover:bg-purple-700'}`}
          >
            {isQueueing ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                Queueing...
              </>
            ) : (
              <>
                <Server className="w-5 h-5" />
                Queue Job
              </>
            )}
          </button>

          {clusterResult && (
            <div className="mt-4 p-4 bg-green-50 rounded-lg border border-green-200 text-green-800 flex flex-col gap-1">
              <p className="font-semibold">{clusterResult.message}</p>
              <p className="text-sm font-mono break-all text-gray-600">Job ID: {clusterResult.job_id}</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
