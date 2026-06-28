"use client";

import React, { useState, useEffect } from 'react';
import { Radio, Play, Square, SkipForward, AlertCircle } from 'lucide-react';
import axios from 'axios';

export default function RadioPage() {
  const [rtmpUrl, setRtmpUrl] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [currentTrack, setCurrentTrack] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState("");

  const fetchStatus = async () => {
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const res = await axios.get(`${apiUrl}/api/v1/radio/status`);
      return res.data;
    } catch (err) {
      console.error("Failed to fetch radio status", err);
      return null;
    }
  };

  useEffect(() => {
    let isMounted = true;
    const updateStatus = async () => {
      const data = await fetchStatus();
      if (isMounted && data) {
        setIsStreaming(data.status === "streaming");
        setCurrentTrack(data.current_track);
      }
    };

    updateStatus();
    const interval = setInterval(updateStatus, 5000);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, []);

  const handleStart = async () => {
    if (!rtmpUrl) {
      setErrorMsg("RTMP URL is required");
      return;
    }
    setErrorMsg("");

    const formData = new FormData();
    formData.append("rtmp_url", rtmpUrl);

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      await axios.post(`${apiUrl}/api/v1/radio/start`, formData);
      setIsStreaming(true);
      // Wait a moment then fetch the new track playing status
      setTimeout(async () => {
        const data = await fetchStatus();
        if (data) setCurrentTrack(data.current_track);
      }, 1000);
    } catch (err: unknown) {
      if (axios.isAxiosError(err)) {
        setErrorMsg(err.response?.data?.message || "Failed to start radio stream");
      } else {
        setErrorMsg("Failed to start radio stream");
      }
    }
  };

  const handleStop = async () => {
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      await axios.post(`${apiUrl}/api/v1/radio/stop`);
      setIsStreaming(false);
      setCurrentTrack(null);
    } catch (err) {
      console.error(err);
    }
  };

  const handleSkip = async () => {
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      await axios.post(`${apiUrl}/api/v1/radio/skip`);
      // Status polling will catch the update shortly
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div className="p-8 max-w-4xl mx-auto">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2 flex items-center gap-3">
          <Radio className="w-8 h-8 text-red-500" />
          Live DJ Radio Stream
        </h1>
        <p className="text-gray-600">Broadcast your generated remakes as a 24/7 internet radio station.</p>
      </div>

      <div className="bg-white p-8 rounded-xl shadow-sm border border-gray-200">

        {/* Status Banner */}
        <div className={`p-4 rounded-lg mb-8 flex items-center gap-3 font-medium ${isStreaming ? 'bg-red-50 text-red-700 border border-red-200' : 'bg-gray-100 text-gray-700'}`}>
          <div className={`w-3 h-3 rounded-full ${isStreaming ? 'bg-red-500 animate-pulse' : 'bg-gray-400'}`}></div>
          {isStreaming ? (
            <span>LIVE: Broadcasting to remote server</span>
          ) : (
            <span>OFF AIR</span>
          )}
        </div>

        {/* Current Track Display */}
        {isStreaming && (
          <div className="mb-8 p-6 bg-gray-900 text-white rounded-lg flex flex-col items-center justify-center min-h-[150px] relative overflow-hidden">
            <div className="absolute inset-0 bg-blue-900/20 blur-xl"></div>
            <p className="text-gray-400 uppercase tracking-widest text-sm mb-2 font-semibold relative z-10">Now Playing</p>
            <p className="text-2xl font-bold text-center relative z-10">
              {currentTrack ? currentTrack : "Waiting for tracks..."}
            </p>
          </div>
        )}

        {/* Controls */}
        <div className="space-y-6">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              RTMP URL (e.g., YouTube Live)
            </label>
            <input
              type="text"
              value={rtmpUrl}
              onChange={(e) => setRtmpUrl(e.target.value)}
              disabled={isStreaming}
              placeholder="rtmp://a.rtmp.youtube.com/live2/XXXX-XXXX-XXXX-XXXX"
              className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition disabled:bg-gray-100 disabled:text-gray-500"
            />
          </div>

          {errorMsg && (
            <div className="p-3 bg-red-50 text-red-700 rounded-md text-sm flex items-center gap-2">
              <AlertCircle className="w-4 h-4" />
              {errorMsg}
            </div>
          )}

          <div className="flex gap-4 pt-4 border-t border-gray-100">
            {!isStreaming ? (
              <button
                onClick={handleStart}
                className="flex-1 py-3 bg-red-600 hover:bg-red-700 text-white rounded-lg font-medium flex items-center justify-center gap-2 transition"
              >
                <Play className="w-5 h-5" />
                Start Broadcast
              </button>
            ) : (
              <>
                <button
                  onClick={handleStop}
                  className="flex-1 py-3 bg-gray-800 hover:bg-gray-900 text-white rounded-lg font-medium flex items-center justify-center gap-2 transition"
                >
                  <Square className="w-5 h-5" />
                  Kill Stream
                </button>
                <button
                  onClick={handleSkip}
                  className="flex-1 py-3 border-2 border-gray-300 hover:bg-gray-50 text-gray-800 rounded-lg font-medium flex items-center justify-center gap-2 transition"
                >
                  <SkipForward className="w-5 h-5" />
                  Skip Track
                </button>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
