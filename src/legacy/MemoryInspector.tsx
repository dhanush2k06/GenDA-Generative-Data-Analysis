import React from 'react';
import { Activity, RefreshCw } from 'lucide-react';
import { formatBytes } from '../utils/formatters';

export interface MemoryLogEntry {
  id: string;
  timestamp: string;
  action: string;
  type: 'info' | 'success' | 'warn' | 'clear';
}

interface MemoryInspectorProps {
  logs: MemoryLogEntry[];
  totalBytes: number;
  fileCount: number;
  parsedCount: number;
  onClearLogs: () => void;
}

export const MemoryInspector: React.FC<MemoryInspectorProps> = ({
  logs,
  totalBytes,
  fileCount,
  parsedCount,
  onClearLogs,
}) => {
  return (
    <div className="w-full glass-panel rounded-2xl p-4 sm:p-5 border border-gray-800">
      <div className="flex items-center justify-between gap-3 mb-3 pb-3 border-b border-gray-800/80">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-lg bg-cyan-500/20 text-cyan-400">
            <Activity className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-gray-100">
              Local Memory & Event Inspector
            </h3>
            <p className="text-[11px] text-gray-400">
              Real-time audit log of client-side operations & RAM allocation
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={onClearLogs}
            className="text-gray-500 hover:text-gray-300 p-1.5 rounded-lg hover:bg-gray-800 transition-colors text-xs flex items-center gap-1 cursor-pointer"
            title="Clear event logs"
          >
            <RefreshCw className="w-3 h-3" />
            <span className="hidden sm:inline">Reset Log</span>
          </button>
        </div>
      </div>

      {/* Memory Status Mini Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mb-3 text-xs">
        <div className="bg-gray-900/60 p-2.5 rounded-xl border border-gray-800/80">
          <span className="text-gray-500 text-[10px] block uppercase font-mono">Heap Footprint</span>
          <span className="text-sm font-bold text-cyan-400 font-mono">{formatBytes(totalBytes)}</span>
        </div>
        <div className="bg-gray-900/60 p-2.5 rounded-xl border border-gray-800/80">
          <span className="text-gray-500 text-[10px] block uppercase font-mono">File Descriptors</span>
          <span className="text-sm font-bold text-emerald-400 font-mono">{fileCount}</span>
        </div>
        <div className="bg-gray-900/60 p-2.5 rounded-xl border border-gray-800/80">
          <span className="text-gray-500 text-[10px] block uppercase font-mono">Parsed In Memory</span>
          <span className="text-sm font-bold text-purple-400 font-mono">{parsedCount}</span>
        </div>
        <div className="bg-gray-900/60 p-2.5 rounded-xl border border-gray-800/80">
          <span className="text-gray-500 text-[10px] block uppercase font-mono">Cloud Requests</span>
          <span className="text-sm font-bold text-emerald-400 font-mono">0 (Blocked)</span>
        </div>
      </div>

      {/* Terminal Log Console */}
      <div className="rounded-xl border border-gray-800 bg-gray-950/80 p-3 max-h-36 overflow-y-auto font-mono text-[11px] space-y-1.5">
        {logs.length === 0 ? (
          <div className="text-gray-600 italic py-2 text-center">
            Awaiting file selection...
          </div>
        ) : (
          logs.map((log) => {
            const getColor = () => {
              switch (log.type) {
                case 'success':
                  return 'text-emerald-400';
                case 'warn':
                  return 'text-amber-400';
                case 'clear':
                  return 'text-rose-400';
                default:
                  return 'text-cyan-300';
              }
            };

            return (
              <div key={log.id} className="flex items-start gap-2 leading-relaxed">
                <span className="text-gray-600 shrink-0 select-none">[{log.timestamp}]</span>
                <span className={`${getColor()} break-all`}>
                  {log.action}
                </span>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
