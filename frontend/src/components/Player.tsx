import React from 'react';

interface PlayerProps {
  url: string;
  type: 'audio' | 'video';
  title?: string;
}

export default function Player({ url, type, title }: PlayerProps) {
  return (
    <div className="mt-4 p-4 bg-gray-50 rounded-lg border border-gray-200">
      {title && <p className="text-sm font-medium text-gray-700 mb-3">{title}</p>}

      {type === 'audio' ? (
        <audio controls className="w-full focus:outline-none" src={url}>
          Your browser does not support the audio element.
        </audio>
      ) : (
        <video controls className="w-full rounded-md shadow-sm bg-black aspect-video object-cover" src={url}>
          Your browser does not support the video element.
        </video>
      )}
    </div>
  );
}
