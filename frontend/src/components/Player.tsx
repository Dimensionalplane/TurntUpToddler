import React, { useRef, useState, useEffect } from 'react';
import { Play, Pause, Volume2, SkipBack, SkipForward } from 'lucide-react';

interface PlayerProps {
  src: string;
}

export default function Player({ src }: PlayerProps) {
  const audioRef = useRef<HTMLAudioElement>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    setIsPlaying(false);
    setProgress(0);
  }, [src]);

  const togglePlay = () => {
    if (audioRef.current) {
      if (isPlaying) {
        audioRef.current.pause();
      } else {
        audioRef.current.play();
      }
      setIsPlaying(!isPlaying);
    }
  };

  const handleTimeUpdate = () => {
    if (audioRef.current) {
      const current = audioRef.current.currentTime;
      const duration = audioRef.current.duration;
      setProgress((current / duration) * 100 || 0);
    }
  };

  const handleSeek = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (audioRef.current) {
      const seekTo = (Number(e.target.value) / 100) * audioRef.current.duration;
      audioRef.current.currentTime = seekTo;
      setProgress(Number(e.target.value));
    }
  };

  return (
    <div className="bg-gray-900 text-white p-4 rounded-lg flex flex-col gap-3">
      <audio
        ref={audioRef}
        src={src}
        onTimeUpdate={handleTimeUpdate}
        onEnded={() => setIsPlaying(false)}
      />

      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <button className="text-gray-400 hover:text-white transition">
            <SkipBack className="w-5 h-5" />
          </button>

          <button
            onClick={togglePlay}
            className="w-10 h-10 bg-blue-500 rounded-full flex items-center justify-center hover:bg-blue-600 transition text-white shadow-lg"
          >
            {isPlaying ? <Pause className="w-5 h-5" /> : <Play className="w-5 h-5 ml-1" />}
          </button>

          <button className="text-gray-400 hover:text-white transition">
            <SkipForward className="w-5 h-5" />
          </button>
        </div>

        <div className="flex items-center gap-2 text-gray-400">
          <Volume2 className="w-4 h-4" />
          <div className="w-16 h-1 bg-gray-700 rounded-full overflow-hidden">
            <div className="h-full bg-blue-500 w-3/4"></div>
          </div>
        </div>
      </div>

      <div className="flex items-center gap-3 text-xs text-gray-400 font-mono">
        <span>0:00</span>
        <input
          type="range"
          min="0" max="100"
          value={progress}
          onChange={handleSeek}
          className="flex-1 h-1 bg-gray-700 rounded-lg appearance-none cursor-pointer"
        />
        <span>-:-</span>
      </div>
    </div>
  );
}
