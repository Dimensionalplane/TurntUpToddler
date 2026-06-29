import React, { useState, useEffect } from 'react';
import { X, Check } from 'lucide-react';

interface InteractiveReviewModalProps {
  ws: WebSocket | null;
  requestData: any;
  onClose: () => void;
}

export default function InteractiveReviewModal({ ws, requestData, onClose }: InteractiveReviewModalProps) {
  const [formData, setFormData] = useState<any>({});

  useEffect(() => {
    if (requestData && requestData.data) {
      setFormData(requestData.data);
    }
  }, [requestData]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    setFormData((prev: any) => ({
      ...prev,
      [name]: value
    }));
  };

  const handleApprove = () => {
    if (ws && ws.readyState === WebSocket.OPEN && requestData) {
      ws.send(JSON.stringify({
        type: 'interactive_review_response',
        job_id: requestData.job_id,
        data: formData
      }));
    }
    onClose();
  };

  if (!requestData) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-2xl max-h-[90vh] flex flex-col">
        <div className="p-4 border-b flex justify-between items-center bg-gray-50 rounded-t-lg">
          <h2 className="text-lg font-semibold text-gray-800">Interactive Review Mode</h2>
          <button onClick={onClose} className="text-gray-500 hover:text-gray-700">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-6 overflow-y-auto flex-1 space-y-4">
          <p className="text-sm text-gray-600 mb-4">
            The pipeline has paused. Review and edit the generated metadata before the generation process continues.
          </p>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Title</label>
            <input
              type="text"
              name="title"
              value={formData.title || ''}
              onChange={handleChange}
              className="w-full rounded border border-gray-300 p-2 focus:ring-2 focus:ring-blue-500 outline-none"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Author</label>
            <input
              type="text"
              name="author"
              value={formData.author || ''}
              onChange={handleChange}
              className="w-full rounded border border-gray-300 p-2 focus:ring-2 focus:ring-blue-500 outline-none"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Musical Style</label>
            <input
              type="text"
              name="style"
              value={formData.style || ''}
              onChange={handleChange}
              className="w-full rounded border border-gray-300 p-2 focus:ring-2 focus:ring-blue-500 outline-none"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Lyrics</label>
            <textarea
              name="lyrics"
              value={formData.lyrics || ''}
              onChange={handleChange}
              rows={8}
              className="w-full rounded border border-gray-300 p-2 focus:ring-2 focus:ring-blue-500 outline-none font-mono text-sm"
            />
          </div>
        </div>

        <div className="p-4 border-t bg-gray-50 rounded-b-lg flex justify-end gap-3">
          <button
            onClick={onClose}
            className="px-4 py-2 border border-gray-300 rounded text-gray-700 hover:bg-gray-100 font-medium transition"
          >
            Cancel
          </button>
          <button
            onClick={handleApprove}
            className="px-4 py-2 bg-blue-600 rounded text-white hover:bg-blue-700 font-medium flex items-center gap-2 transition"
          >
            <Check className="w-4 h-4" />
            Approve & Continue
          </button>
        </div>
      </div>
    </div>
  );
}
