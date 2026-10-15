import React, { useState } from 'react';
import { 
  FileSpreadsheet, 
  FileText, 
  Code2, 
  Layers, 
  Folder, 
  Clock, 
  HardDrive, 
  Eye, 
  Trash, 
  CheckCircle, 
  FolderOpen, 
  Search, 
  Zap
} from 'lucide-react';
import { LocalFileItem } from '../types';
import { formatBytes, formatDate, formatRelativeTime } from '../utils/formatters';

interface FileCardListProps {
  files: LocalFileItem[];
  onPreview: (file: LocalFileItem) => void;
  onRemoveFile: (id: string) => void;
  onPreviewAll?: () => void;
}

export const FileCardList: React.FC<FileCardListProps> = ({
  files,
  onPreview,
  onRemoveFile,
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedFilter, setSelectedFilter] = useState<string>('all');

  if (files.length === 0) {
    return null;
  }

  // Filter files
  const filteredFiles = files.filter((item) => {
    const matchesSearch = item.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      item.relativePath.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesCategory = selectedFilter === 'all' || item.fileCategory === selectedFilter;
    return matchesSearch && matchesCategory;
  });

  const getFileIcon = (category: string) => {
    switch (category) {
      case 'csv':
        return <FileSpreadsheet className="w-5 h-5 text-emerald-400" />;
      case 'xlsx':
        return <Layers className="w-5 h-5 text-green-400" />;
      case 'json':
        return <Code2 className="w-5 h-5 text-amber-400" />;
      case 'txt':
        return <FileText className="w-5 h-5 text-cyan-400" />;
      default:
        return <FileText className="w-5 h-5 text-gray-400" />;
    }
  };

  const getCategoryBadgeClass = (category: string) => {
    switch (category) {
      case 'csv':
        return 'bg-emerald-950/70 border-emerald-500/30 text-emerald-300';
      case 'xlsx':
        return 'bg-green-950/70 border-green-500/30 text-green-300';
      case 'json':
        return 'bg-amber-950/70 border-amber-500/30 text-amber-300';
      case 'txt':
        return 'bg-cyan-950/70 border-cyan-500/30 text-cyan-300';
      default:
        return 'bg-gray-800/70 border-gray-600/30 text-gray-300';
    }
  };

  return (
    <div className="w-full space-y-4">
      {/* Section Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-2">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-lg bg-emerald-500/20 text-emerald-400">
            <FolderOpen className="w-4 h-4" />
          </div>
          <h2 className="text-base font-semibold text-gray-100">
            Selected Files <span className="text-emerald-400 text-sm font-mono">({files.length})</span>
          </h2>
        </div>

        {/* Search and Category Filter */}
        <div className="flex flex-wrap items-center gap-2">
          {/* Search Input */}
          <div className="relative">
            <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
            <input
              type="text"
              placeholder="Search files or paths..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-8 pr-3 py-1.5 bg-gray-900/90 border border-gray-800 rounded-xl text-xs text-gray-200 placeholder-gray-500 focus:outline-none focus:border-emerald-500/50 w-44 sm:w-56"
            />
          </div>

          {/* Category Filter Pills */}
          <div className="flex items-center gap-1 bg-gray-900/80 p-1 border border-gray-800 rounded-xl text-xs">
            {['all', 'csv', 'xlsx', 'json', 'txt'].map((cat) => (
              <button
                key={cat}
                onClick={() => setSelectedFilter(cat)}
                className={`px-2 py-1 rounded-lg uppercase text-[10px] font-semibold transition-all cursor-pointer ${
                  selectedFilter === cat
                    ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                    : 'text-gray-400 hover:text-gray-200'
                }`}
              >
                {cat}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Grid of File Cards */}
      {filteredFiles.length === 0 ? (
        <div className="text-center py-10 glass-card rounded-2xl border border-gray-800">
          <p className="text-sm text-gray-400">No files match the search criteria.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3.5">
          {filteredFiles.map((item) => {
            const hasParsed = !!item.parsedContent;
            const isReading = item.status === 'reading';

            return (
              <div
                key={item.id}
                className={`glass-card rounded-xl p-4 transition-all duration-200 flex flex-col justify-between group border relative ${
                  hasParsed ? 'border-emerald-500/30 bg-emerald-950/10' : 'border-gray-800/80 hover:border-gray-700'
                }`}
              >
                {/* Top: Icon + Name + Category + Delete */}
                <div>
                  <div className="flex items-start justify-between gap-2 mb-2">
                    <div className="flex items-center gap-2.5 min-w-0">
                      <div className="p-2 rounded-lg bg-gray-900/90 border border-gray-800 shrink-0">
                        {getFileIcon(item.fileCategory)}
                      </div>
                      <div className="min-w-0">
                        <h4 
                          className="text-sm font-semibold text-gray-100 truncate group-hover:text-emerald-300 transition-colors"
                          title={item.name}
                        >
                          {item.name}
                        </h4>
                        <span className={`inline-block px-1.5 py-0.5 rounded border text-[10px] uppercase font-bold tracking-wider ${getCategoryBadgeClass(item.fileCategory)}`}>
                          {item.extension.toUpperCase() || item.fileCategory.toUpperCase()}
                        </span>
                      </div>
                    </div>

                    {/* Delete single button */}
                    <button
                      onClick={() => onRemoveFile(item.id)}
                      className="text-gray-500 hover:text-rose-400 p-1.5 rounded-lg hover:bg-rose-950/40 transition-colors cursor-pointer"
                      title="Remove file from local memory"
                    >
                      <Trash className="w-3.5 h-3.5" />
                    </button>
                  </div>

                  {/* Path (if from folder selection) */}
                  {item.relativePath && item.relativePath !== item.name && (
                    <div className="flex items-center gap-1.5 text-[11px] text-gray-400 bg-gray-900/60 px-2 py-1 rounded-md mb-2.5 truncate font-mono">
                      <Folder className="w-3 h-3 text-cyan-400 shrink-0" />
                      <span className="truncate" title={item.relativePath}>
                        {item.relativePath}
                      </span>
                    </div>
                  )}

                  {/* Metadata Specs Grid */}
                  <div className="grid grid-cols-2 gap-2 text-xs text-gray-400 pt-2 border-t border-gray-800/60 mb-3">
                    <div className="flex items-center gap-1.5">
                      <HardDrive className="w-3 h-3 text-cyan-400 shrink-0" />
                      <span>{formatBytes(item.size)}</span>
                    </div>
                    <div className="flex items-center gap-1.5 truncate" title={formatDate(item.lastModified)}>
                      <Clock className="w-3 h-3 text-purple-400 shrink-0" />
                      <span className="truncate">{formatRelativeTime(item.lastModified)}</span>
                    </div>
                  </div>

                  {/* Status & Preview stats if loaded */}
                  {hasParsed && (
                    <div className="flex items-center justify-between text-[11px] bg-emerald-950/40 border border-emerald-500/20 px-2.5 py-1 rounded-lg text-emerald-300 mb-3">
                      <span className="flex items-center gap-1">
                        <CheckCircle className="w-3 h-3 text-emerald-400" />
                        In RAM ({formatBytes(item.readMemoryBytes || item.size)})
                      </span>
                      {item.readDurationMs !== undefined && (
                        <span className="text-gray-400 font-mono">{item.readDurationMs}ms</span>
                      )}
                    </div>
                  )}
                </div>

                {/* Bottom Action: Read / Preview Button */}
                <div className="pt-2">
                  <button
                    onClick={() => onPreview(item)}
                    disabled={isReading}
                    className={`w-full flex items-center justify-center gap-2 py-2 px-3 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
                      hasParsed
                        ? 'bg-emerald-600/20 hover:bg-emerald-600/30 border border-emerald-500/40 text-emerald-300 hover:text-emerald-200'
                        : 'bg-gray-800/90 hover:bg-gray-700/90 border border-gray-700 text-gray-200 hover:text-white'
                    }`}
                  >
                    {isReading ? (
                      <>
                        <Zap className="w-3.5 h-3.5 animate-spin text-emerald-400" />
                        <span>Reading locally...</span>
                      </>
                    ) : (
                      <>
                        <Eye className="w-3.5 h-3.5 text-emerald-400" />
                        <span>{hasParsed ? 'View / Preview Content' : 'Read / Preview'}</span>
                      </>
                    )}
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
