"use client";

import React, { useState, useEffect } from 'react';
import { Clock, Play, Download, Video } from 'lucide-react';
import axios from 'axios';

interface HistoryItem {
  id: number;
  original_filename: string;
  generated_title: string;
  style_prompt: string;
  youtube_id: string;
  timestamp: string;
}

export default function HistoryList() {
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchHistory = async () => {
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const res = await axios.get(`${apiUrl}/api/v1/history`);
      return res.data;
    } catch (err) {
      console.error("Failed to fetch history:", err);
      return null;
    }
  };

  useEffect(() => {
    let isMounted = true;

    const updateHistory = async () => {
      if (!isMounted) return;
      const data = await fetchHistory();
      if (isMounted && data && data.status === "success") {
        setHistory(data.data);
        setLoading(false);
      } else if (isMounted) {
        setLoading(false);
      }
    };

    updateHistory();
    // Poll for updates
    const interval = setInterval(updateHistory, 15000);

    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, []);

  if (loading) {
    return <div className="text-sm text-gray-500 flex items-center gap-2"><Clock className="w-4 h-4 animate-spin" /> Loading history...</div>;
  }

  if (history.length === 0) {
    return <div className="text-sm text-gray-500">No recent generations found.</div>;
  }

  return (
    <div className="space-y-4 max-h-[500px] overflow-y-auto pr-2">
      {history.slice(0, 5).map((item) => (
        <div key={item.id} className="p-3 border border-gray-100 rounded-lg hover:bg-gray-50 transition group">
          <p className="font-semibold text-gray-800 text-sm truncate">{item.generated_title || item.original_filename}</p>
          <p className="text-xs text-gray-500 truncate mt-1">{item.style_prompt}</p>

          <div className="flex items-center gap-2 mt-3 opacity-0 group-hover:opacity-100 transition-opacity">
            {item.youtube_id && (
              <a
                href={`https://youtube.com/watch?v=${item.youtube_id}`}
                target="_blank"
                rel="noreferrer"
                className="text-xs flex items-center gap-1 bg-red-100 text-red-700 px-2 py-1 rounded hover:bg-red-200"
              >
                <Video className="w-3 h-3" /> YouTube
              </a>
            )}
            <button className="text-xs flex items-center gap-1 bg-blue-100 text-blue-700 px-2 py-1 rounded hover:bg-blue-200">
              <Download className="w-3 h-3" /> Files
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}
