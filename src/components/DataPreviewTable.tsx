import { useState, useMemo } from 'react';
import { Table, Search } from 'lucide-react';
import { DataPreview } from '../types';
import { formatBytes } from '../utils/formatters';

interface DataPreviewTableProps {
  preview: DataPreview;
}

export function DataPreviewTable({ preview }: DataPreviewTableProps) {
  const [searchTerm, setSearchTerm] = useState('');
  const [page, setPage] = useState(0);
  const rowsPerPage = 10;

  const filteredRows = useMemo(() => {
    if (!searchTerm.trim()) return preview.preview_rows;
    const term = searchTerm.toLowerCase();
    return preview.preview_rows.filter((row) =>
      Object.values(row).some((val) =>
        val !== null && val !== undefined && String(val).toLowerCase().includes(term)
      )
    );
  }, [preview.preview_rows, searchTerm]);

  const totalPages = Math.ceil(filteredRows.length / rowsPerPage);
  const displayedRows = filteredRows.slice(page * rowsPerPage, (page + 1) * rowsPerPage);

  const getTypeBadgeColor = (typeStr: string) => {
    const t = typeStr.toLowerCase();
    if (t.includes('int') || t.includes('float') || t.includes('numeric')) {
      return 'bg-cyan-500/10 text-cyan-400 border-cyan-500/30';
    }
    if (t.includes('str') || t.includes('utf8') || t.includes('cat')) {
      return 'bg-purple-500/10 text-purple-400 border-purple-500/30';
    }
    if (t.includes('date') || t.includes('time')) {
      return 'bg-amber-500/10 text-amber-400 border-amber-500/30';
    }
    if (t.includes('bool')) {
      return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30';
    }
    return 'bg-slate-800 text-slate-400 border-slate-700';
  };

  return (
    <div className="bg-slate-900/60 border border-slate-800 rounded-xl overflow-hidden backdrop-blur-sm">
      {/* Table Header Controls */}
      <div className="p-4 border-b border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex items-center space-x-3">
          <div className="p-2 rounded-lg bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
            <Table className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h3 className="text-sm font-semibold text-slate-100">{preview.filename}</h3>
              <span className="text-[11px] px-2 py-0.5 rounded-full bg-slate-800 text-slate-300 font-mono">
                {formatBytes(preview.size_bytes)}
              </span>
              <span className="text-[11px] px-2 py-0.5 rounded-full bg-slate-800 text-slate-400 font-mono">
                {preview.encoding.toUpperCase()}
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-0.5">
              {preview.row_count.toLocaleString()} rows &bull; {preview.col_count} columns &bull; Bounded preview in RAM
            </p>
          </div>
        </div>

        {/* Filter search */}
        <div className="relative min-w-[220px]">
          <Search className="w-3.5 h-3.5 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => {
              setSearchTerm(e.target.value);
              setPage(0);
            }}
            placeholder="Filter preview rows..."
            className="w-full pl-8 pr-3 py-1.5 text-xs bg-slate-950/60 border border-slate-800 rounded-lg text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500/50"
          />
        </div>
      </div>

      {/* Table Content */}
      <div className="overflow-x-auto max-h-[420px] scrollbar-thin scrollbar-thumb-slate-800 scrollbar-track-transparent">
        <table className="w-full text-left text-xs border-collapse">
          <thead className="bg-slate-950/80 sticky top-0 z-10 border-b border-slate-800">
            <tr>
              <th className="py-2.5 px-3 font-mono text-[11px] text-slate-500 w-12 text-center">
                #
              </th>
              {preview.headers.map((col) => (
                <th key={col} className="py-2.5 px-3 text-slate-300 font-semibold whitespace-nowrap">
                  <div className="flex flex-col space-y-1">
                    <span>{col}</span>
                    <span
                      className={`text-[10px] font-mono px-1.5 py-0.2 rounded border w-fit font-normal ${getTypeBadgeColor(
                        preview.column_types[col] || ''
                      )}`}
                    >
                      {preview.column_types[col] || 'unknown'}
                    </span>
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60">
            {displayedRows.length === 0 ? (
              <tr>
                <td colSpan={preview.headers.length + 1} className="py-8 text-center text-slate-500">
                  No matching preview rows found for "{searchTerm}".
                </td>
              </tr>
            ) : (
              displayedRows.map((row, idx) => (
                <tr key={idx} className="hover:bg-slate-800/30 transition-colors">
                  <td className="py-2 px-3 text-center font-mono text-[11px] text-slate-500">
                    {page * rowsPerPage + idx + 1}
                  </td>
                  {preview.headers.map((col) => {
                    const val = row[col];
                    const isNull = val === null || val === undefined;
                    return (
                      <td
                        key={col}
                        className={`py-2 px-3 max-w-[240px] truncate ${
                          isNull ? 'text-slate-600 italic font-mono' : 'text-slate-300'
                        }`}
                        title={isNull ? '(null)' : String(val)}
                      >
                        {isNull ? 'null' : String(val)}
                      </td>
                    );
                  })}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination Footer */}
      <div className="p-3 border-t border-slate-800 bg-slate-950/40 flex items-center justify-between text-xs text-slate-400">
        <div>
          Showing {displayedRows.length} of {filteredRows.length} preview rows (dataset total: {preview.row_count.toLocaleString()})
        </div>

        {totalPages > 1 && (
          <div className="flex items-center space-x-2">
            <button
              onClick={() => setPage((p) => Math.max(0, p - 1))}
              disabled={page === 0}
              className="px-2.5 py-1 rounded bg-slate-800 disabled:opacity-40 disabled:cursor-not-allowed hover:bg-slate-700 text-slate-300"
            >
              Previous
            </button>
            <span className="font-mono text-[11px]">
              Page {page + 1} of {totalPages}
            </span>
            <button
              onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
              disabled={page >= totalPages - 1}
              className="px-2.5 py-1 rounded bg-slate-800 disabled:opacity-40 disabled:cursor-not-allowed hover:bg-slate-700 text-slate-300"
            >
              Next
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
