import { useState } from 'react';
import {
  BarChart3,
  AlertTriangle,
  Layers,
  Copy,
  Hash,
  Activity,
  Filter
} from 'lucide-react';
import { DatasetProfile, InferredColumnType } from '../types';
import { formatBytes } from '../utils/formatters';

interface ProfileDashboardProps {
  profile: DatasetProfile;
  onSelectColumnForAnalysis?: (column: string, suggestedOp: string) => void;
}

export function ProfileDashboard({ profile, onSelectColumnForAnalysis }: ProfileDashboardProps) {
  const [filterType, setFilterType] = useState<string>('all');

  const filteredColumns = profile.columns.filter((c) => {
    if (filterType === 'all') return true;
    return c.inferred_type === filterType;
  });

  const getTypeColor = (type: InferredColumnType) => {
    switch (type) {
      case 'numeric':
        return 'text-cyan-400 bg-cyan-500/10 border-cyan-500/30';
      case 'categorical':
        return 'text-purple-400 bg-purple-500/10 border-purple-500/30';
      case 'datetime':
        return 'text-amber-400 bg-amber-500/10 border-amber-500/30';
      case 'boolean':
        return 'text-emerald-400 bg-emerald-500/10 border-emerald-500/30';
      default:
        return 'text-slate-400 bg-slate-800 border-slate-700';
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Metrics Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 backdrop-blur-sm">
          <div className="flex items-center space-x-2 text-slate-400 text-xs uppercase font-mono">
            <Hash className="w-4 h-4 text-cyan-400" />
            <span>Total Rows</span>
          </div>
          <div className="text-2xl font-bold text-slate-100 mt-2 font-mono">
            {profile.row_count.toLocaleString()}
          </div>
        </div>

        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 backdrop-blur-sm">
          <div className="flex items-center space-x-2 text-slate-400 text-xs uppercase font-mono">
            <Layers className="w-4 h-4 text-indigo-400" />
            <span>Columns</span>
          </div>
          <div className="text-2xl font-bold text-slate-100 mt-2 font-mono">
            {profile.column_count}
          </div>
        </div>

        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 backdrop-blur-sm">
          <div className="flex items-center space-x-2 text-slate-400 text-xs uppercase font-mono">
            <Copy className="w-4 h-4 text-amber-400" />
            <span>Duplicate Rows</span>
          </div>
          <div className="text-2xl font-bold text-slate-100 mt-2 font-mono">
            {profile.duplicate_rows}
          </div>
        </div>

        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 backdrop-blur-sm">
          <div className="flex items-center space-x-2 text-slate-400 text-xs uppercase font-mono">
            <Activity className="w-4 h-4 text-emerald-400" />
            <span>RAM Footprint</span>
          </div>
          <div className="text-2xl font-bold text-slate-100 mt-2 font-mono">
            {formatBytes(profile.memory_bytes)}
          </div>
        </div>
      </div>

      {/* Dataset-level warnings */}
      {profile.dataset_warnings.length > 0 && (
        <div className="bg-amber-950/30 border border-amber-800/60 rounded-xl p-4 text-xs text-amber-300">
          <div className="flex items-center space-x-2 font-semibold text-amber-200 mb-1">
            <AlertTriangle className="w-4 h-4 text-amber-400" />
            <span>Data Quality Notes</span>
          </div>
          <ul className="list-disc list-inside space-y-1 text-amber-300/90 pl-1">
            {profile.dataset_warnings.map((w, idx) => (
              <li key={idx}>{w}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Column Type Filter Pills */}
      <div className="flex items-center justify-between flex-wrap gap-2 pt-2">
        <div className="flex items-center space-x-2">
          <BarChart3 className="w-4 h-4 text-cyan-400" />
          <h3 className="text-sm font-semibold text-slate-200">
            Column Profiles & Quality Check
          </h3>
        </div>

        <div className="flex items-center space-x-1.5 text-xs">
          <Filter className="w-3.5 h-3.5 text-slate-500 mr-1" />
          {['all', 'numeric', 'categorical', 'datetime', 'boolean'].map((t) => (
            <button
              key={t}
              onClick={() => setFilterType(t)}
              className={`px-2.5 py-1 rounded-lg capitalize transition-colors ${
                filterType === t
                  ? 'bg-slate-800 text-slate-100 border border-slate-700 font-medium'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
              }`}
            >
              {t}
            </button>
          ))}
        </div>
      </div>

      {/* Column Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {filteredColumns.map((col) => (
          <div
            key={col.name}
            className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 backdrop-blur-sm flex flex-col justify-between space-y-3 hover:border-slate-700 transition-colors"
          >
            <div>
              {/* Card Header */}
              <div className="flex items-start justify-between gap-2">
                <div className="font-medium text-slate-200 text-sm truncate" title={col.name}>
                  {col.name}
                </div>
                <span
                  className={`text-[10px] uppercase font-mono px-2 py-0.5 rounded-full border shrink-0 ${getTypeColor(
                    col.inferred_type
                  )}`}
                >
                  {col.inferred_type}
                </span>
              </div>

              {/* Missing & Distinct Stats */}
              <div className="grid grid-cols-2 gap-2 mt-3 pt-2 border-t border-slate-800/80 text-xs">
                <div>
                  <span className="text-slate-500 block text-[10px] uppercase">Missing</span>
                  <div className="flex items-center space-x-1.5 mt-0.5">
                    <span className="font-mono text-slate-300">
                      {col.null_count} ({col.null_percentage}%)
                    </span>
                  </div>
                </div>

                <div>
                  <span className="text-slate-500 block text-[10px] uppercase">Distinct</span>
                  <div className="font-mono text-slate-300 mt-0.5">
                    {col.distinct_count} {col.is_unique && <span className="text-cyan-400 text-[10px]">(unique)</span>}
                  </div>
                </div>
              </div>

              {/* Null percentage bar */}
              <div className="w-full bg-slate-950 rounded-full h-1.5 mt-2 overflow-hidden">
                <div
                  className={`h-full ${
                    col.null_percentage > 30
                      ? 'bg-rose-500'
                      : col.null_percentage > 10
                      ? 'bg-amber-500'
                      : 'bg-emerald-500'
                  }`}
                  style={{ width: `${Math.min(100, col.null_percentage)}%` }}
                />
              </div>

              {/* Numeric Stats */}
              {col.inferred_type === 'numeric' && col.mean !== null && (
                <div className="mt-3 bg-slate-950/50 p-2.5 rounded-lg border border-slate-800/80 text-[11px] grid grid-cols-3 gap-1 text-slate-400">
                  <div>
                    <span className="text-slate-500 block text-[9px] uppercase">Min</span>
                    <span className="font-mono text-slate-200">{col.min_val}</span>
                  </div>
                  <div>
                    <span className="text-slate-500 block text-[9px] uppercase">Mean</span>
                    <span className="font-mono text-cyan-300">{col.mean}</span>
                  </div>
                  <div>
                    <span className="text-slate-500 block text-[9px] uppercase">Max</span>
                    <span className="font-mono text-slate-200">{col.max_val}</span>
                  </div>
                  <div className="mt-1">
                    <span className="text-slate-500 block text-[9px] uppercase">Median</span>
                    <span className="font-mono text-slate-300">{col.median}</span>
                  </div>
                  <div className="mt-1">
                    <span className="text-slate-500 block text-[9px] uppercase">Std Dev</span>
                    <span className="font-mono text-slate-300">{col.std}</span>
                  </div>
                  <div className="mt-1">
                    <span className="text-slate-500 block text-[9px] uppercase">IQR (25-75)</span>
                    <span className="font-mono text-slate-300">{col.q25} - {col.q75}</span>
                  </div>
                </div>
              )}

              {/* Categorical Frequencies */}
              {col.top_frequencies.length > 0 && col.inferred_type !== 'numeric' && (
                <div className="mt-3 bg-slate-950/50 p-2 rounded-lg border border-slate-800/80 space-y-1.5 text-[11px]">
                  <div className="text-[10px] text-slate-500 uppercase">Top Values</div>
                  {col.top_frequencies.slice(0, 3).map((freq, i) => (
                    <div key={i} className="flex items-center justify-between text-slate-300">
                      <span className="truncate max-w-[130px]" title={freq.value}>
                        {freq.value}
                      </span>
                      <span className="font-mono text-slate-400 text-[10px]">
                        {freq.count} ({freq.percentage}%)
                      </span>
                    </div>
                  ))}
                </div>
              )}

              {/* Column Warnings */}
              {col.warnings.length > 0 && (
                <div className="mt-2 space-y-1">
                  {col.warnings.map((w, i) => (
                    <div key={i} className="text-[10px] text-amber-400 flex items-center space-x-1">
                      <AlertTriangle className="w-3 h-3 shrink-0" />
                      <span className="truncate" title={w}>{w}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Quick Analyze Action */}
            {onSelectColumnForAnalysis && (
              <div className="pt-2 border-t border-slate-800/60 flex justify-end">
                <button
                  onClick={() => {
                    const op = col.inferred_type === 'numeric' ? 'numeric_summary' : 'category_rank';
                    onSelectColumnForAnalysis(col.name, op);
                  }}
                  className="text-xs text-cyan-400 hover:text-cyan-300 font-medium flex items-center space-x-1"
                >
                  <span>Analyze Column</span>
                  <span>&rarr;</span>
                </button>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
