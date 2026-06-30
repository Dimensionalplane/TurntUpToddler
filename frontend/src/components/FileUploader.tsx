"use client";

import React, { useState, useRef, useEffect } from 'react';
import { Upload, Play, CheckCircle, Download, Info } from 'lucide-react';
import axios from 'axios';
import { useSettings } from '@/context/SettingsContext';
import InteractiveReviewModal from './InteractiveReviewModal';

export default function FileUploader() {
  const { generateVocals, normalizeAudio, useAdvancedVideo, kidsMode, stylePrompt, interactiveMode, remakePriority } = useSettings();
  const [file, setFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [isScraping, setIsScraping] = useState(false);
  const [progress, setProgress] = useState(0);
  const [statusMsg, setStatusMsg] = useState("");
  const [isComplete, setIsComplete] = useState(false);
  const [reviewRequest, setReviewRequest] = useState<any>(null);
  const [activeWs, setActiveWs] = useState<WebSocket | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    let ws: WebSocket;
    if (isUploading || isScraping) {
      // Connect to WebSocket for progress updates
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      // Convert http:// to ws://
      const wsUrl = apiUrl.replace(/^http/, 'ws') + "/api/v1/ws";
      ws = new WebSocket(wsUrl);
      setActiveWs(ws);

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);

          if (data.type === "interactive_review_request") {
             setReviewRequest(data);
             setStatusMsg("Paused for interactive review...");
          } else {
              if (data.progress !== undefined) {
                setProgress(data.progress);
              }
              if (data.message) {
                setStatusMsg(data.message);
              }
              if (data.progress === 100) {
                setIsComplete(true);
                setIsUploading(false);
                setIsScraping(false);
              }
          }
        } catch (e) {
          console.error("Failed to parse websocket message", e);
        }
      };

      ws.onerror = (e) => console.error("WebSocket error", e);
    }

    return () => {
      if (ws) {
          ws.close();
          setActiveWs(null);
      }
    };
  }, [isUploading, isScraping]);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setIsComplete(false);
      setProgress(0);
      setStatusMsg("");
    }
  };

  const handleScrape = async () => {
    setIsScraping(true);
    setProgress(5);
    setStatusMsg("Scraping BitMidi for nursery rhymes...");

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      await axios.post(`${apiUrl}/api/v1/kids/scrape`);
      setStatusMsg("Scraping requested successfully. Pipeline will start automatically.");
    } catch (err) {
      console.error(err);
      setStatusMsg("Scraping failed.");
      setIsScraping(false);
    }
  };

  const handleUpload = async () => {
    if (!file) return;

    setIsUploading(true);
    setProgress(5);
    setStatusMsg("Uploading file...");

    const formData = new FormData();
    formData.append("file", file);
    formData.append("style", stylePrompt);
    formData.append("generate_vocals", generateVocals ? "true" : "false");
    formData.append("normalize_audio", normalizeAudio ? "true" : "false");
    formData.append("use_advanced_video", useAdvancedVideo ? "true" : "false");
    formData.append("kids_mode", kidsMode ? "true" : "false");
    formData.append("interactive_mode", interactiveMode ? "true" : "false");
    formData.append("remake_priority", remakePriority);

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      await axios.post(`${apiUrl}/api/v1/generate`, formData, {
        headers: {
          "Content-Type": "multipart/form-data"
        }
      });
      setStatusMsg("Pipeline started. Waiting for backend generation...");
    } catch (err) {
      console.error(err);
      setStatusMsg("Upload failed.");
      setIsUploading(false);
    }
  };

  return (
    <>
      <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
        <h2 className="text-xl font-bold mb-4">Start Pipeline</h2>

        <div
          className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition ${file ? 'border-blue-500 bg-blue-50' : 'border-gray-300 hover:border-gray-400'}`}
          onClick={() => fileInputRef.current?.click()}
        >
          <input
            type="file"
            ref={fileInputRef}
            className="hidden"
            accept=".mid,.midi,.mxl,.xml"
            onChange={handleFileChange}
          />

          <Upload className={`w-10 h-10 mx-auto mb-3 ${file ? 'text-blue-500' : 'text-gray-400'}`} />

          {file ? (
            <div>
              <p className="font-semibold text-blue-700">{file.name}</p>
              <p className="text-sm text-blue-500 mt-1">{(file.size / 1024).toFixed(2)} KB</p>
            </div>
          ) : (
            <div>
              <p className="font-medium text-gray-700">Click to upload MIDI or MusicXML file</p>
              <p className="text-sm text-gray-500 mt-1">Drag and drop is supported</p>
            </div>
          )}
        </div>

        <div className="mt-6 flex flex-col sm:flex-row gap-3">
          <button
            onClick={handleUpload}
            disabled={!file || isUploading || isScraping}
            className={`flex-1 py-3 rounded-lg flex items-center justify-center gap-2 font-medium transition ${!file || isUploading || isScraping ? 'bg-gray-200 text-gray-500 cursor-not-allowed' : 'bg-blue-600 text-white hover:bg-blue-700'}`}
          >
            {isUploading ? (
              <span>Processing...</span>
            ) : (
              <>
                <Play className="w-5 h-5" />
                Generate Hymn <span title="Starts the automated pipeline for the uploaded file using current sidebar settings."><Info className="w-4 h-4 text-white opacity-70 cursor-help" /></span>
              </>
            )}
          </button>

          {kidsMode && !file && (
            <button
              onClick={handleScrape}
              disabled={isUploading || isScraping}
              className={`flex-1 py-3 rounded-lg flex items-center justify-center gap-2 font-medium transition ${isUploading || isScraping ? 'bg-green-200 text-green-500 cursor-not-allowed' : 'bg-green-600 text-white hover:bg-green-700'}`}
            >
              {isScraping ? (
                <span>Scraping...</span>
              ) : (
                <>
                  <Download className="w-5 h-5" />
                  Auto-Scrape BitMidi <span title="Dynamically searches BitMidi for public domain nursery rhymes and automatically queues them for generation (only visible when Kids Mode is active)."><Info className="w-4 h-4 text-white opacity-70 cursor-help" /></span>
                </>
              )}
            </button>
          )}
        </div>

        {(isUploading || isScraping || isComplete || statusMsg) && (
          <div className="mt-6 p-4 bg-gray-50 rounded-lg">
            <div className="flex justify-between text-sm mb-2">
              <span className="font-medium text-gray-700">Status: {statusMsg}</span>
              <span className="text-gray-500">{progress}%</span>
            </div>

            <div className="w-full bg-gray-200 rounded-full h-2.5">
              <div className="bg-blue-600 h-2.5 rounded-full transition-all duration-500" style={{ width: `${progress}%` }}></div>
            </div>

            {isComplete && (
              <div className="mt-4 flex items-center gap-2 text-green-600 font-medium">
                <CheckCircle className="w-5 h-5" />
                Generation Complete!
              </div>
            )}
          </div>
        )}
      </div>

      {reviewRequest && (
        <InteractiveReviewModal
          ws={activeWs}
          requestData={reviewRequest}
          onClose={() => setReviewRequest(null)}
        />
      )}
    </>
  );
}
