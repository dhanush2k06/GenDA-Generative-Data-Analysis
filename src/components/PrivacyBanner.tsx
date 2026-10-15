import { useState } from 'react';
import { ShieldCheck, ChevronDown, ChevronUp, Lock, HardDrive, WifiOff } from 'lucide-react';

export function PrivacyBanner() {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 mb-6 backdrop-blur-sm shadow-sm">
      <div className="flex items-start justify-between">
        <div className="flex items-center space-x-3">
          <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <ShieldCheck className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h3 className="text-sm font-semibold text-slate-200">
                Local-First Loopback Privacy Model (v2.0)
              </h3>
              <span className="text-[10px] px-2 py-0.2 rounded-full bg-emerald-500/10 text-emerald-300 font-mono border border-emerald-500/30">
                127.0.0.1 ONLY
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-0.5">
              Raw data is transmitted strictly between this browser and your local Python service on loopback. No external servers or cloud endpoints are ever contacted.
            </p>
          </div>
        </div>

        <button
          onClick={() => setExpanded(!expanded)}
          className="text-xs text-slate-400 hover:text-slate-200 flex items-center space-x-1 px-2 py-1 rounded bg-slate-800/50 hover:bg-slate-800 transition-colors ml-4"
        >
          <span>{expanded ? 'Less Details' : 'View Guarantees'}</span>
          {expanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
        </button>
      </div>

      {expanded && (
        <div className="mt-4 pt-3 border-t border-slate-800 grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
          <div className="flex items-start space-x-2 bg-slate-950/40 p-2.5 rounded-lg border border-slate-800/80">
            <Lock className="w-4 h-4 text-cyan-400 mt-0.5 shrink-0" />
            <div>
              <strong className="text-slate-200 block mb-0.5">Cryptographic Launch Token</strong>
              <span className="text-slate-400">
                Every request requires a per-launch secret token and validates Origin & Host headers against DNS rebinding.
              </span>
            </div>
          </div>

          <div className="flex items-start space-x-2 bg-slate-950/40 p-2.5 rounded-lg border border-slate-800/80">
            <HardDrive className="w-4 h-4 text-emerald-400 mt-0.5 shrink-0" />
            <div>
              <strong className="text-slate-200 block mb-0.5">In-Memory RAM Only</strong>
              <span className="text-slate-400">
                Datasets are loaded into Polars DataFrames in RAM. Data is never persisted to disk by default and is purged on Clear Session.
              </span>
            </div>
          </div>

          <div className="flex items-start space-x-2 bg-slate-950/40 p-2.5 rounded-lg border border-slate-800/80">
            <WifiOff className="w-4 h-4 text-indigo-400 mt-0.5 shrink-0" />
            <div>
              <strong className="text-slate-200 block mb-0.5">Zero Remote Telemetry</strong>
              <span className="text-slate-400">
                Strict network isolation: the Python service never makes outbound HTTP requests or analytics calls.
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
