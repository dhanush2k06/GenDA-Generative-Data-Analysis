import React, { useRef, useState } from 'react';
import { 
  FileUp, 
  FolderUp, 
  Trash2, 
  UploadCloud, 
  Layers, 
  FileText, 
  FileSpreadsheet, 
  Code2, 
  Sparkles
} from 'lucide-react';

interface DropZoneAndControlsProps {
  onFilesSelected: (files: FileList | File[]) => void;
  onClearFiles: () => void;
  fileCount: number;
  onLoadSamples?: () => void;
}

export const DropZoneAndControls: React.FC<DropZoneAndControlsProps> = ({
  onFilesSelected,
  onClearFiles,
  fileCount,
  onLoadSamples,
}) => {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const folderInputRef = useRef<HTMLInputElement>(null);
  const [isDragging, setIsDragging] = useState(false);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      onFilesSelected(e.target.files);
      // Reset input value so re-selecting same files triggers change event
      e.target.value = '';
    }
  };

  const handleFolderChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      onFilesSelected(e.target.files);
      e.target.value = '';
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      onFilesSelected(e.dataTransfer.files);
    }
  };

  return (
    <div className="w-full space-y-4">
      {/* Hidden File and Folder Inputs */}
      <input
        ref={fileInputRef}
        type="file"
        multiple
        accept=".csv,.xlsx,.xls,.json,.txt,text/csv,text/plain,application/json,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,application/vnd.ms-excel"
        className="hidden"
        onChange={handleFileChange}
      />
      <input
        ref={folderInputRef}
        type="file"
        // @ts-ignore
        webkitdirectory=""
        directory=""
        multiple
        className="hidden"
        onChange={handleFolderChange}
      />

      {/* Main Action Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 p-4 glass-card rounded-2xl">
        <div className="flex flex-wrap items-center gap-3">
          {/* Select Files Button */}
          <button
            onClick={() => fileInputRef.current?.click()}
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-emerald-600 to-emerald-500 hover:from-emerald-500 hover:to-emerald-400 text-white font-medium text-sm shadow-md shadow-emerald-950/40 hover:shadow-glow transition-all active:scale-[0.98] cursor-pointer group"
          >
            <FileUp className="w-4 h-4 transition-transform group-hover:-translate-y-0.5" />
            <span>Select Files</span>
          </button>

          {/* Select Folder Button */}
          <button
            onClick={() => folderInputRef.current?.click()}
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-cyan-600 to-teal-600 hover:from-cyan-500 hover:to-teal-500 text-white font-medium text-sm shadow-md shadow-cyan-950/40 hover:shadow-glow-cyan transition-all active:scale-[0.98] cursor-pointer group"
          >
            <FolderUp className="w-4 h-4 transition-transform group-hover:-translate-y-0.5" />
            <span>Select Folder</span>
          </button>

          {/* Sample Loader Shortcut */}
          {onLoadSamples && (
            <button
              onClick={onLoadSamples}
              className="inline-flex items-center gap-2 px-3.5 py-2 rounded-xl bg-purple-950/40 hover:bg-purple-900/60 border border-purple-500/30 text-purple-300 hover:text-purple-200 text-xs font-medium transition-all active:scale-[0.98] cursor-pointer"
              title="Loads generated test sample files (CSV, XLSX, JSON, TXT) for instant demonstration"
            >
              <Sparkles className="w-3.5 h-3.5 text-purple-400" />
              <span>Load Demo Samples</span>
            </button>
          )}
        </div>

        {/* Clear Files Button */}
        {fileCount > 0 && (
          <button
            onClick={onClearFiles}
            className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-rose-950/50 hover:bg-rose-900/70 border border-rose-500/40 text-rose-300 hover:text-rose-100 font-medium text-sm transition-all active:scale-[0.98] cursor-pointer group ml-auto"
            title="Clear all loaded files, parsed data, and memory references"
          >
            <Trash2 className="w-4 h-4 text-rose-400 transition-transform group-hover:rotate-12" />
            <span>Clear Files</span>
            <span className="bg-rose-900/80 px-2 py-0.5 rounded-full text-xs font-semibold text-rose-200">
              {fileCount}
            </span>
          </button>
        )}
      </div>

      {/* Drag and Drop Zone */}
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={`relative border-2 border-dashed rounded-2xl p-8 sm:p-10 transition-all duration-300 flex flex-col items-center justify-center text-center cursor-pointer ${
          isDragging
            ? 'border-emerald-400 bg-emerald-950/20 scale-[1.01] shadow-glow'
            : 'border-gray-800 hover:border-gray-700 bg-gray-950/30 hover:bg-gray-900/40'
        }`}
        onClick={() => fileInputRef.current?.click()}
      >
        <div className="p-4 rounded-2xl bg-gradient-to-b from-gray-800/80 to-gray-900/90 border border-gray-700/60 text-emerald-400 mb-4 shadow-md group-hover:scale-105 transition-transform">
          <UploadCloud className="w-8 h-8 animate-pulse-subtle" />
        </div>

        <h3 className="text-base sm:text-lg font-semibold text-gray-100 mb-1">
          Drop files or entire folders here
        </h3>
        <p className="text-xs sm:text-sm text-gray-400 max-w-md mb-4">
          Direct local access using browser File APIs. No data ever leaves your computer.
        </p>

        {/* Supported Formats Pill Row */}
        <div className="flex flex-wrap items-center justify-center gap-2 text-xs">
          <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-emerald-950/40 border border-emerald-500/20 text-emerald-300">
            <FileSpreadsheet className="w-3.5 h-3.5" /> CSV
          </span>
          <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-green-950/40 border border-green-500/20 text-green-300">
            <Layers className="w-3.5 h-3.5" /> XLSX / XLS
          </span>
          <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-amber-950/40 border border-amber-500/20 text-amber-300">
            <Code2 className="w-3.5 h-3.5" /> JSON
          </span>
          <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-cyan-950/40 border border-cyan-500/20 text-cyan-300">
            <FileText className="w-3.5 h-3.5" /> TXT
          </span>
        </div>
      </div>
    </div>
  );
};
