import { useRef, useState } from 'react';
import { UploadCloud, FileSpreadsheet, Sparkles, AlertCircle, Database } from 'lucide-react';

interface FileSelectorProps {
  onFileSelected: (file: File) => void;
  onLoadSample: (sampleName: string) => void;
  isLoading: boolean;
  disabled?: boolean;
}

export function FileSelector({
  onFileSelected,
  onLoadSample,
  isLoading,
  disabled = false,
}: FileSelectorProps) {
  const [isDragOver, setIsDragOver] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFile = (file: File) => {
    setErrorMsg(null);
    if (!file.name.toLowerCase().endsWith('.csv')) {
      setErrorMsg('Please select a valid .csv file. Other file types can be exported to CSV.');
      return;
    }
    if (file.size > 100 * 1024 * 1024) {
      setErrorMsg('File exceeds 100 MB local safety threshold.');
      return;
    }
    onFileSelected(file);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    if (disabled || isLoading) return;
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFile(e.dataTransfer.files[0]);
    }
  };

  return (
    <div className="space-y-4">
      {/* Drag & Drop Zone */}
      <div
        onDragOver={(e) => {
          e.preventDefault();
          if (!disabled && !isLoading) setIsDragOver(true);
        }}
        onDragLeave={() => setIsDragOver(false)}
        onDrop={handleDrop}
        onClick={() => {
          if (!disabled && !isLoading && fileInputRef.current) {
            fileInputRef.current.click();
          }
        }}
        className={`border-2 border-dashed rounded-2xl p-8 text-center cursor-pointer transition-all duration-200 ${
          isDragOver
            ? 'border-cyan-400 bg-cyan-950/20 shadow-lg shadow-cyan-500/10'
            : 'border-slate-800 hover:border-slate-700 bg-slate-900/40 hover:bg-slate-900/60'
        } ${disabled || isLoading ? 'opacity-50 cursor-not-allowed' : ''}`}
      >
        <input
          type="file"
          ref={fileInputRef}
          onChange={(e) => {
            if (e.target.files && e.target.files[0]) {
              handleFile(e.target.files[0]);
            }
          }}
          accept=".csv"
          className="hidden"
          disabled={disabled || isLoading}
        />

        <div className="flex flex-col items-center justify-center space-y-3">
          <div className="w-14 h-14 rounded-2xl bg-gradient-to-tr from-cyan-500/20 to-indigo-500/20 border border-cyan-500/30 flex items-center justify-center text-cyan-400 group-hover:scale-105 transition-transform">
            {isLoading ? (
              <div className="w-6 h-6 border-2 border-cyan-400 border-t-transparent rounded-full animate-spin" />
            ) : (
              <UploadCloud className="w-7 h-7" />
            )}
          </div>

          <div>
            <h3 className="text-base font-semibold text-slate-100">
              {isLoading ? 'Sending to local Python service...' : 'Choose or drop a CSV dataset'}
            </h3>
            <p className="text-xs text-slate-400 mt-1">
              Supports CSV with UTF-8 / auto-detected encoding &bull; Up to 100 MB &bull; Processed strictly in local RAM
            </p>
          </div>

          <div className="pt-2">
            <span className="inline-flex items-center px-3.5 py-1.5 rounded-lg text-xs font-medium bg-slate-800 text-slate-200 hover:bg-slate-700 border border-slate-700 transition-colors">
              Browse Local Files
            </span>
          </div>
        </div>
      </div>

      {errorMsg && (
        <div className="flex items-center space-x-2 p-3 bg-rose-950/40 border border-rose-800/60 rounded-xl text-rose-300 text-xs">
          <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* Quick Sample Datasets */}
      <div className="bg-slate-900/50 border border-slate-800/80 rounded-xl p-4">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center space-x-2">
            <Sparkles className="w-4 h-4 text-cyan-400" />
            <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-300">
              Instant Sample Datasets
            </h4>
          </div>
          <span className="text-[11px] text-slate-500">
            Pre-loaded from project dataset directory
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
          <button
            onClick={() => onLoadSample('users')}
            disabled={disabled || isLoading}
            className="flex items-start space-x-2.5 p-2.5 rounded-lg bg-slate-950/50 hover:bg-slate-800/60 border border-slate-800 text-left transition-all group hover:border-slate-700"
          >
            <Database className="w-4 h-4 text-cyan-400 mt-0.5 shrink-0 group-hover:scale-110 transition-transform" />
            <div>
              <div className="text-xs font-medium text-slate-200">Users Dataset</div>
              <div className="text-[11px] text-slate-500">Demographics, roles, signup dates</div>
            </div>
          </button>

          <button
            onClick={() => onLoadSample('messages')}
            disabled={disabled || isLoading}
            className="flex items-start space-x-2.5 p-2.5 rounded-lg bg-slate-950/50 hover:bg-slate-800/60 border border-slate-800 text-left transition-all group hover:border-slate-700"
          >
            <Database className="w-4 h-4 text-indigo-400 mt-0.5 shrink-0 group-hover:scale-110 transition-transform" />
            <div>
              <div className="text-xs font-medium text-slate-200">Messages Dataset</div>
              <div className="text-[11px] text-slate-500">Notifications, media, priority labels</div>
            </div>
          </button>

          <button
            onClick={() => onLoadSample('synthetic')}
            disabled={disabled || isLoading}
            className="flex items-start space-x-2.5 p-2.5 rounded-lg bg-slate-950/50 hover:bg-slate-800/60 border border-slate-800 text-left transition-all group hover:border-slate-700"
          >
            <FileSpreadsheet className="w-4 h-4 text-emerald-400 mt-0.5 shrink-0 group-hover:scale-110 transition-transform" />
            <div>
              <div className="text-xs font-medium text-slate-200">Synthetic Sales</div>
              <div className="text-[11px] text-slate-500">Known answers verification data</div>
            </div>
          </button>
        </div>
      </div>
    </div>
  );
}
