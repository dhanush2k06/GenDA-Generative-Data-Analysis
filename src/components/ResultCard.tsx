import { useState } from 'react';
import {
  CheckCircle2,
  AlertTriangle,
  XCircle,
  ShieldCheck,
  Clock,
  ChevronDown,
  ChevronUp,
  Table as TableIcon,
  BarChart2,
  Info
} from 'lucide-react';
import { AnalysisResult } from '../types';
import { PlotlyChart } from './PlotlyChart';

interface ResultCardProps {
  result: AnalysisResult;
}

export function ResultCard({ result }: ResultCardProps) {
  const [showTable, setShowTable] = useState(true);
  const [showChart, setShowChart] = useState(true);

  const isPassed = result.validation_status === 'passed';
  const isWarn = result.validation_status === 'warning';

  // Extract tabular data if available in result.result
  const getTableData = (): { headers: string[]; rows: any[] } | null => {
    const res = result.result;
    if (!res) return null;

    if (res.groups && Array.isArray(res.groups)) {
      if (res.groups.length === 0) return null;
      return {
        headers: Object.keys(res.groups[0]),
        rows: res.groups,
      };
    }

    if (res.rankings && Array.isArray(res.rankings)) {
      if (res.rankings.length === 0) return null;
      return {
        headers: Object.keys(res.rankings[0]),
        rows: res.rankings,
      };
    }

    if (res.columns && Array.isArray(res.columns)) {
      if (res.columns.length === 0) return null;
      return {
        headers: Object.keys(res.columns[0]),
        rows: res.columns,
      };
    }

    if (res.sample_matches && Array.isArray(res.sample_matches)) {
      if (res.sample_matches.length === 0) return null;
      return {
        headers: Object.keys(res.sample_matches[0]),
        rows: res.sample_matches,
      };
    }

    // Numeric summary key-value pairs
    if (result.operation === 'numeric_summary') {
      const rows = Object.entries(res).map(([k, v]) => ({ metric: k, value: String(v) }));
      return {
        headers: ['metric', 'value'],
        rows,
      };
    }

    return null;
  };

  const tableData = getTableData();

  return (
    <div className="bg-slate-900/60 border border-slate-800 rounded-xl overflow-hidden backdrop-blur-sm shadow-md transition-all">
      {/* Result Header */}
      <div className="p-4 border-b border-slate-800 bg-slate-950/40 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <div className="flex items-center space-x-2">
            <h3 className="text-base font-semibold text-slate-100">{result.title}</h3>
          </div>
          <p className="text-xs text-slate-400 mt-0.5">
            Engine: {result.engine_details}
          </p>
        </div>

        <div className="flex items-center space-x-2 flex-wrap gap-y-1">
          {/* Validation Status */}
          <span
            className={`inline-flex items-center space-x-1 px-2.5 py-1 rounded-full text-xs font-semibold uppercase tracking-wider border ${
              isPassed
                ? 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30'
                : isWarn
                ? 'bg-amber-500/10 text-amber-300 border-amber-500/30'
                : 'bg-rose-500/10 text-rose-300 border-rose-500/30'
            }`}
          >
            {isPassed ? (
              <CheckCircle2 className="w-3.5 h-3.5" />
            ) : isWarn ? (
              <AlertTriangle className="w-3.5 h-3.5" />
            ) : (
              <XCircle className="w-3.5 h-3.5" />
            )}
            <span>{result.validation_status}</span>
          </span>

          {/* Cross Engine Badge */}
          {result.cross_engine_match !== undefined && result.cross_engine_match !== null && (
            <span
              className={`inline-flex items-center space-x-1 px-2.5 py-1 rounded-full text-xs font-medium border ${
                result.cross_engine_match
                  ? 'bg-cyan-500/10 text-cyan-300 border-cyan-500/30'
                  : 'bg-rose-500/10 text-rose-300 border-rose-500/30'
              }`}
              title="Calculated in Polars and independently verified in DuckDB"
            >
              <ShieldCheck className="w-3.5 h-3.5 text-cyan-400" />
              <span>DuckDB Verified</span>
            </span>
          )}

          {/* Execution Time */}
          <span className="inline-flex items-center space-x-1 px-2 py-1 rounded-md text-xs text-slate-400 font-mono bg-slate-900 border border-slate-800">
            <Clock className="w-3 h-3 text-slate-500" />
            <span>{result.execution_time_ms} ms</span>
          </span>
        </div>
      </div>

      <div className="p-5 space-y-4">
        {/* Evidence Summary Callout */}
        {result.evidence_summary && (
          <div className="bg-cyan-950/20 border-l-4 border-cyan-500 p-3 rounded-r-lg text-xs text-cyan-200">
            <strong className="text-cyan-300 block mb-0.5">Verified Finding:</strong>
            {result.evidence_summary}
          </div>
        )}

        {/* Interactive Plotly Chart */}
        {result.chart_spec && (
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-1.5 text-xs font-semibold text-slate-300 uppercase tracking-wider">
                <BarChart2 className="w-4 h-4 text-cyan-400" />
                <span>Interactive Visualization (Plotly Spec)</span>
              </div>
              <button
                onClick={() => setShowChart(!showChart)}
                className="text-slate-400 hover:text-slate-200 text-xs flex items-center space-x-1"
              >
                <span>{showChart ? 'Hide Chart' : 'Show Chart'}</span>
                {showChart ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
              </button>
            </div>

            {showChart && (
              <div className="border border-slate-800 rounded-xl overflow-hidden bg-slate-950/60 p-2">
                <PlotlyChart spec={result.chart_spec} height={360} />
              </div>
            )}
          </div>
        )}

        {/* Data Table */}
        {tableData && (
          <div className="space-y-2 pt-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-1.5 text-xs font-semibold text-slate-300 uppercase tracking-wider">
                <TableIcon className="w-4 h-4 text-indigo-400" />
                <span>Computed Results Table</span>
              </div>
              <button
                onClick={() => setShowTable(!showTable)}
                className="text-slate-400 hover:text-slate-200 text-xs flex items-center space-x-1"
              >
                <span>{showTable ? 'Hide Table' : 'Show Table'}</span>
                {showTable ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
              </button>
            </div>

            {showTable && (
              <div className="overflow-x-auto max-h-64 border border-slate-800 rounded-xl bg-slate-950/40">
                <table className="w-full text-left text-xs border-collapse">
                  <thead className="bg-slate-950/80 sticky top-0 border-b border-slate-800">
                    <tr>
                      {tableData.headers.map((h) => (
                        <th key={h} className="py-2 px-3 text-slate-300 font-semibold uppercase text-[11px] font-mono">
                          {h}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60">
                    {tableData.rows.slice(0, 25).map((row, i) => (
                      <tr key={i} className="hover:bg-slate-800/20">
                        {tableData.headers.map((h) => (
                          <td key={h} className="py-1.5 px-3 font-mono text-slate-300">
                            {row[h] !== null && row[h] !== undefined ? String(row[h]) : 'null'}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {/* Warnings & Method Notes */}
        {result.warnings.length > 0 && (
          <div className="bg-amber-950/20 border border-amber-800/40 rounded-lg p-3 text-xs text-amber-300">
            <div className="font-semibold text-amber-200 mb-1 flex items-center space-x-1.5">
              <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
              <span>Warnings & Methodology Notes</span>
            </div>
            <ul className="list-disc list-inside space-y-0.5 pl-1 text-amber-300/90">
              {result.warnings.map((w, i) => (
                <li key={i}>{w}</li>
              ))}
            </ul>
          </div>
        )}

        {/* Limitations */}
        {result.limitations.length > 0 && (
          <div className="text-[11px] text-slate-500 border-t border-slate-800/80 pt-2 flex items-start space-x-1.5">
            <Info className="w-3.5 h-3.5 shrink-0 text-slate-500 mt-0.5" />
            <span>
              <strong>Documented Limitations:</strong> {result.limitations.join('; ')}
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
