import { useState } from 'react';
import { Terminal, ChevronUp, ChevronDown, CheckCircle2, AlertTriangle, Info, XCircle } from 'lucide-react';
import { LogEntry } from '../types';

interface AuditLogProps {
  logs: LogEntry[];
}

export function AuditLog({ logs }: AuditLogProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  const getIcon = (type: LogEntry['type']) => {
    switch (type) {
      case 'success':
        return <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0 mt-0.5" />;
      case 'warn':
        return <AlertTriangle className="w-3.5 h-3.5 text-amber-400 shrink-0 mt-0.5" />;
      case 'error':
        return <XCircle className="w-3.5 h-3.5 text-rose-400 shrink-0 mt-0.5" />;
      default:
        return <Info className="w-3.5 h-3.5 text-cyan-400 shrink-0 mt-0.5" />;
    }
  };

  return (
    <div className="border-t border-slate-800 bg-slate-950/90 backdrop-blur-md sticky bottom-0 z-30 transition-all">
      {/* Bar Header */}
      <div
        onClick={() => setIsExpanded(!isExpanded)}
        className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-2.5 flex items-center justify-between cursor-pointer hover:bg-slate-900/40 select-none text-xs"
      >
        <div className="flex items-center space-x-2 text-slate-400">
          <Terminal className="w-4 h-4 text-cyan-400" />
          <span className="font-semibold text-slate-300 font-mono">
            GenDA Audit & Diagnostics Log
          </span>
          <span className="text-[10px] px-1.5 py-0.2 rounded bg-slate-800 text-slate-400 font-mono">
            {logs.length} events
          </span>
        </div>

        <div className="flex items-center space-x-3">
          {logs.length > 0 && (
            <div className="hidden sm:block text-[11px] text-slate-500 font-mono truncate max-w-md">
              Latest: {logs[0].action}
            </div>
          )}
          <button className="text-slate-400 hover:text-slate-200">
            {isExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronUp className="w-4 h-4" />}
          </button>
        </div>
      </div>

      {/* Expanded Log List */}
      {isExpanded && (
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3 border-t border-slate-800/80 max-h-60 overflow-y-auto font-mono text-xs space-y-1.5">
          {logs.length === 0 ? (
            <div className="text-slate-500 py-4 text-center">No log events recorded yet.</div>
          ) : (
            logs.map((log) => (
              <div
                key={log.id}
                className="flex items-start space-x-2 py-1 px-2 rounded hover:bg-slate-900/60 transition-colors text-slate-300"
              >
                {getIcon(log.type)}
                <span className="text-[10px] text-slate-500 shrink-0">[{log.timestamp}]</span>
                <span className="text-xs break-all">{log.action}</span>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}
