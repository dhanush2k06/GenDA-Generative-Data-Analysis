import {
  ShieldCheck,
  ShieldAlert,
  Key,
  Trash2,
  FileText,
  ExternalLink,
  Cpu,
  RefreshCw
} from 'lucide-react';
import { ServiceHealth } from '../types';

interface NavbarProps {
  health: ServiceHealth;
  hasActiveSession: boolean;
  hasResults: boolean;
  onClearSession: () => void;
  onOpenReport: () => void;
  onOpenTokenModal: () => void;
  onRefreshHealth: () => void;
}

export function Navbar({
  health,
  hasActiveSession,
  hasResults,
  onClearSession,
  onOpenReport,
  onOpenTokenModal,
  onRefreshHealth,
}: NavbarProps) {
  const isHealthy = health.status === 'ok';

  return (
    <header className="border-b border-slate-800 bg-slate-950/80 backdrop-blur-md sticky top-0 z-40">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Brand */}
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-cyan-600 to-indigo-600 flex items-center justify-center shadow-lg shadow-cyan-500/20 border border-cyan-400/30">
            <Cpu className="w-5 h-5 text-white" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <span className="font-bold text-lg tracking-tight bg-gradient-to-r from-white via-slate-200 to-slate-400 bg-clip-text text-transparent">
                GenDA
              </span>
              <span className="text-xs px-2 py-0.5 rounded-full font-semibold bg-cyan-500/10 text-cyan-400 border border-cyan-500/30">
                v2.0 Local
              </span>
            </div>
            <p className="text-[11px] text-slate-400 font-mono">
              Generative Data Analyst &bull; Loopback Service
            </p>
          </div>
        </div>

        {/* Status & Actions */}
        <div className="flex items-center space-x-3">
          {/* Health indicator */}
          <button
            onClick={onRefreshHealth}
            title={isHealthy ? 'Connected to local loopback Python service' : health.error || 'Service unreachable'}
            className={`flex items-center space-x-2 px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors ${
              isHealthy
                ? 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30 hover:bg-emerald-500/20'
                : 'bg-rose-500/10 text-rose-300 border-rose-500/30 hover:bg-rose-500/20'
            }`}
          >
            {isHealthy ? (
              <>
                <span className="relative flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
                </span>
                <ShieldCheck className="w-3.5 h-3.5" />
                <span>127.0.0.1:8000 Active</span>
              </>
            ) : (
              <>
                <ShieldAlert className="w-3.5 h-3.5" />
                <span>Service Offline</span>
                <RefreshCw className="w-3 h-3 ml-1 animate-spin" />
              </>
            )}
          </button>

          {/* Token Modal trigger */}
          <button
            onClick={onOpenTokenModal}
            className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-slate-900 border border-slate-700 text-slate-300 hover:text-white hover:border-slate-600 transition-colors"
          >
            <Key className="w-3.5 h-3.5 text-cyan-400" />
            <span>Token</span>
          </button>

          {/* Fast API Swagger link */}
          <a
            href="http://127.0.0.1:8000/docs"
            target="_blank"
            rel="noreferrer"
            className="hidden md:flex items-center space-x-1 px-2.5 py-1.5 rounded-lg text-xs text-slate-400 hover:text-slate-200 hover:bg-slate-900 transition-colors"
            title="FastAPI Interactive API Documentation"
          >
            <span>API Docs</span>
            <ExternalLink className="w-3 h-3" />
          </a>

          {/* Export Report */}
          {hasResults && (
            <button
              onClick={onOpenReport}
              className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-indigo-600 hover:bg-indigo-500 text-white shadow-sm shadow-indigo-600/30 transition-colors"
            >
              <FileText className="w-3.5 h-3.5" />
              <span>Full Report</span>
            </button>
          )}

          {/* Clear Session */}
          {hasActiveSession && (
            <button
              onClick={onClearSession}
              className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-rose-950/60 hover:bg-rose-900 text-rose-300 border border-rose-800/60 transition-colors"
              title="Delete server-side session dataframe and reset interface"
            >
              <Trash2 className="w-3.5 h-3.5" />
              <span>Clear Session</span>
            </button>
          )}
        </div>
      </div>
    </header>
  );
}
