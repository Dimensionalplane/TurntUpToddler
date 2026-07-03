import FileUploader from "@/components/FileUploader";
import HistoryList from "@/components/HistoryList";
import { Info } from "lucide-react";

export default function Home() {
  return (
    <div className="p-8 max-w-5xl mx-auto">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Automated Pipeline</h1>
        <p className="text-gray-600">Upload MIDI files to convert them into modern music videos using AI generation.</p>
        <p className="text-sm text-gray-500 mt-1">Check "Kids Mode 👶" in the sidebar to enforce child-friendly metadata and styling.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 space-y-6">
          <FileUploader />

          <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
            <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
              Pipeline Queue
              <span title="Monitors the real-time status of the Python backend orchestrator. Files dropped in the uploader above will appear here as they are processed through rendering, style transfer, TTS generation, and final video compilation."><Info className="w-4 h-4 text-gray-400 cursor-help" /></span>
            </h3>
            <div className="text-center py-8 text-gray-500">
              No jobs currently running. Upload a file above to begin.
            </div>
          </div>
        </div>

        <div className="space-y-6">
          <div className="bg-blue-50 p-5 rounded-lg border border-blue-100 flex gap-3 text-blue-800">
            <Info className="w-6 h-6 flex-shrink-0" />
            <div className="text-sm">
              <p className="font-semibold mb-1">How it works</p>
              <p>The pipeline automatically converts your MIDI into audio, applies AI style transfer via MusicGen, generates lyrics & metadata via OpenAI, creates a dynamic visualizer, and burns synchronized subtitles into a final MP4.</p>
            </div>
          </div>

          <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
            <h3 className="font-semibold text-gray-800 mb-4 flex items-center gap-2">
              Recent Generations
              <span title="A historical log of successfully processed tracks pulled from the SQLite tracking database. Clicking YouTube will open the uploaded video if publishing was enabled."><Info className="w-4 h-4 text-gray-400 cursor-help" /></span>
            </h3>
            <HistoryList />
          </div>
        </div>
      </div>
    </div>
  );
}
