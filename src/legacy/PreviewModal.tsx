import React, { useState } from 'react';
import { 
  X, 
  FileSpreadsheet, 
  Layers, 
  Code2, 
  FileText, 
  Copy, 
  Check, 
  ChevronLeft, 
  ChevronRight, 
  Search, 
  ShieldCheck,
  Hash,
  Database,
  HardDrive
} from 'lucide-react';
import { LocalFileItem, CsvParsedData, XlsxParsedData, JsonParsedData, TxtParsedData } from '../types';
import { formatBytes, formatDate } from '../utils/formatters';

interface PreviewModalProps {
  fileItem: LocalFileItem | null;
  onClose: () => void;
}

export const PreviewModal: React.FC<PreviewModalProps> = ({ fileItem, onClose }) => {
  if (!fileItem || !fileItem.parsedContent) return null;

  const [activeSheetName, setActiveSheetName] = useState<string>(() => {
    if (fileItem.parsedContent?.type === 'xlsx') {
      return (fileItem.parsedContent as XlsxParsedData).sheetNames[0] || '';
    }
    return '';
  });
  const [searchFilter, setSearchFilter] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [copied, setCopied] = useState(false);

  const parsed = fileItem.parsedContent;

  const handleCopy = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  // Render content based on type
  const renderContent = () => {
    switch (parsed.type) {
      case 'csv':
        return renderCsvPreview(parsed as CsvParsedData);
      case 'xlsx':
        return renderXlsxPreview(parsed as XlsxParsedData);
      case 'json':
        return renderJsonPreview(parsed as JsonParsedData);
      case 'txt':
        return renderTxtPreview(parsed as TxtParsedData);
      default:
        return (
          <div className="p-8 text-center text-gray-400">
            Unsupported preview format
          </div>
        );
    }
  };

  // CSV Preview Renderer
  const renderCsvPreview = (data: CsvParsedData) => {
    const filteredRows = data.rows.filter((row) => {
      if (!searchFilter) return true;
      return Object.values(row).some((val) =>
        String(val).toLowerCase().includes(searchFilter.toLowerCase())
      );
    });

    const totalPages = Math.ceil(filteredRows.length / pageSize) || 1;
    const startIndex = (currentPage - 1) * pageSize;
    const paginatedRows = filteredRows.slice(startIndex, startIndex + pageSize);

    return (
      <div className="space-y-4">
        {/* Quick Metrics Bar */}
        <div className="flex flex-wrap items-center justify-between gap-3 bg-gray-900/60 p-3 rounded-xl border border-gray-800 text-xs text-gray-300">
          <div className="flex items-center gap-4">
            <span className="flex items-center gap-1.5">
              <Database className="w-3.5 h-3.5 text-emerald-400" />
              Rows: <strong className="text-white font-mono">{data.rowCount}</strong>
            </span>
            <span className="flex items-center gap-1.5">
              <Hash className="w-3.5 h-3.5 text-cyan-400" />
              Columns: <strong className="text-white font-mono">{data.colCount}</strong>
            </span>
          </div>

          <div className="flex items-center gap-2">
            <div className="relative">
              <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-500" />
              <input
                type="text"
                placeholder="Filter table rows..."
                value={searchFilter}
                onChange={(e) => {
                  setSearchFilter(e.target.value);
                  setCurrentPage(1);
                }}
                className="pl-8 pr-2.5 py-1 bg-gray-950/80 border border-gray-800 rounded-lg text-xs text-gray-200 placeholder-gray-500 focus:outline-none focus:border-emerald-500/50 w-44"
              />
            </div>

            <select
              value={pageSize}
              onChange={(e) => {
                setPageSize(Number(e.target.value));
                setCurrentPage(1);
              }}
              className="bg-gray-950/80 border border-gray-800 rounded-lg text-xs text-gray-300 px-2 py-1 focus:outline-none"
            >
              <option value={5}>5 / page</option>
              <option value={10}>10 / page</option>
              <option value={25}>25 / page</option>
              <option value={50}>50 / page</option>
            </select>
          </div>
        </div>

        {/* Interactive Data Table */}
        <div className="overflow-x-auto rounded-xl border border-gray-800 bg-gray-950/40 max-h-[52vh]">
          <table className="w-full text-left text-xs border-collapse">
            <thead className="sticky top-0 bg-gray-900/95 backdrop-blur-md border-b border-gray-800 text-gray-300 font-semibold z-10">
              <tr>
                <th className="py-2.5 px-3 border-r border-gray-800/80 w-12 text-center text-gray-500 font-mono">
                  #
                </th>
                {data.headers.map((h, i) => (
                  <th key={i} className="py-2.5 px-3 border-r border-gray-800/80 font-mono text-emerald-400 whitespace-nowrap">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800/60 font-mono text-gray-300">
              {paginatedRows.length === 0 ? (
                <tr>
                  <td colSpan={data.headers.length + 1} className="py-8 text-center text-gray-500">
                    No matching records found
                  </td>
                </tr>
              ) : (
                paginatedRows.map((row, rIdx) => (
                  <tr key={rIdx} className="hover:bg-gray-900/50 transition-colors">
                    <td className="py-2 px-3 border-r border-gray-800/80 text-center text-gray-500">
                      {startIndex + rIdx + 1}
                    </td>
                    {data.headers.map((h, cIdx) => (
                      <td key={cIdx} className="py-2 px-3 border-r border-gray-800/80 whitespace-nowrap max-w-xs truncate" title={String(row[h] ?? '')}>
                        {row[h] !== undefined && row[h] !== null ? String(row[h]) : <span className="text-gray-600">null</span>}
                      </td>
                    ))}
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Table Pagination Controls */}
        <div className="flex items-center justify-between text-xs text-gray-400 pt-2">
          <span>
            Showing <strong className="text-white">{filteredRows.length > 0 ? startIndex + 1 : 0}</strong> - <strong className="text-white">{Math.min(startIndex + pageSize, filteredRows.length)}</strong> of <strong className="text-white">{filteredRows.length}</strong> entries
          </span>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
              disabled={currentPage <= 1}
              className="p-1.5 rounded-lg border border-gray-800 bg-gray-900/80 disabled:opacity-40 disabled:cursor-not-allowed hover:bg-gray-800 text-gray-300"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <span className="font-mono text-xs text-gray-300">
              Page {currentPage} / {totalPages}
            </span>
            <button
              onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
              disabled={currentPage >= totalPages}
              className="p-1.5 rounded-lg border border-gray-800 bg-gray-900/80 disabled:opacity-40 disabled:cursor-not-allowed hover:bg-gray-800 text-gray-300"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    );
  };

  // XLSX Preview Renderer
  const renderXlsxPreview = (data: XlsxParsedData) => {
    const currentSheetKey = activeSheetName || data.sheetNames[0] || '';
    const sheetData = data.sheets[currentSheetKey] || { headers: [], rows: [], rowCount: 0, colCount: 0 };

    const filteredRows = sheetData.rows.filter((row) => {
      if (!searchFilter) return true;
      return Object.values(row).some((val) =>
        String(val).toLowerCase().includes(searchFilter.toLowerCase())
      );
    });

    const totalPages = Math.ceil(filteredRows.length / pageSize) || 1;
    const startIndex = (currentPage - 1) * pageSize;
    const paginatedRows = filteredRows.slice(startIndex, startIndex + pageSize);

    return (
      <div className="space-y-4">
        {/* Sheet Tabs Bar */}
        <div className="flex items-center gap-2 overflow-x-auto pb-1 border-b border-gray-800">
          <span className="text-xs text-gray-400 font-semibold uppercase tracking-wider shrink-0 mr-1">
            Worksheets:
          </span>
          {data.sheetNames.map((sheet) => (
            <button
              key={sheet}
              onClick={() => {
                setActiveSheetName(sheet);
                setCurrentPage(1);
              }}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium shrink-0 transition-all cursor-pointer ${
                currentSheetKey === sheet
                  ? 'bg-green-500/20 text-green-300 border border-green-500/40 shadow-sm'
                  : 'bg-gray-900/80 text-gray-400 hover:text-gray-200 border border-gray-800'
              }`}
            >
              {sheet} ({data.sheets[sheet]?.rowCount || 0} rows)
            </button>
          ))}
        </div>

        {/* Quick Metrics Bar */}
        <div className="flex flex-wrap items-center justify-between gap-3 bg-gray-900/60 p-3 rounded-xl border border-gray-800 text-xs text-gray-300">
          <div className="flex items-center gap-4">
            <span className="flex items-center gap-1.5">
              <Database className="w-3.5 h-3.5 text-green-400" />
              Sheet Rows: <strong className="text-white font-mono">{sheetData.rowCount}</strong>
            </span>
            <span className="flex items-center gap-1.5">
              <Hash className="w-3.5 h-3.5 text-cyan-400" />
              Sheet Cols: <strong className="text-white font-mono">{sheetData.colCount}</strong>
            </span>
          </div>

          <div className="flex items-center gap-2">
            <div className="relative">
              <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-500" />
              <input
                type="text"
                placeholder="Filter sheet rows..."
                value={searchFilter}
                onChange={(e) => {
                  setSearchFilter(e.target.value);
                  setCurrentPage(1);
                }}
                className="pl-8 pr-2.5 py-1 bg-gray-950/80 border border-gray-800 rounded-lg text-xs text-gray-200 placeholder-gray-500 focus:outline-none focus:border-green-500/50 w-44"
              />
            </div>

            <select
              value={pageSize}
              onChange={(e) => {
                setPageSize(Number(e.target.value));
                setCurrentPage(1);
              }}
              className="bg-gray-950/80 border border-gray-800 rounded-lg text-xs text-gray-300 px-2 py-1 focus:outline-none"
            >
              <option value={5}>5 / page</option>
              <option value={10}>10 / page</option>
              <option value={25}>25 / page</option>
              <option value={50}>50 / page</option>
            </select>
          </div>
        </div>

        {/* Sheet Table */}
        <div className="overflow-x-auto rounded-xl border border-gray-800 bg-gray-950/40 max-h-[48vh]">
          <table className="w-full text-left text-xs border-collapse">
            <thead className="sticky top-0 bg-gray-900/95 backdrop-blur-md border-b border-gray-800 text-gray-300 font-semibold z-10">
              <tr>
                <th className="py-2.5 px-3 border-r border-gray-800/80 w-12 text-center text-gray-500 font-mono">
                  #
                </th>
                {sheetData.headers.map((h, i) => (
                  <th key={i} className="py-2.5 px-3 border-r border-gray-800/80 font-mono text-green-400 whitespace-nowrap">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800/60 font-mono text-gray-300">
              {paginatedRows.length === 0 ? (
                <tr>
                  <td colSpan={sheetData.headers.length + 1} className="py-8 text-center text-gray-500">
                    No matching records found
                  </td>
                </tr>
              ) : (
                paginatedRows.map((row, rIdx) => (
                  <tr key={rIdx} className="hover:bg-gray-900/50 transition-colors">
                    <td className="py-2 px-3 border-r border-gray-800/80 text-center text-gray-500">
                      {startIndex + rIdx + 1}
                    </td>
                    {sheetData.headers.map((h, cIdx) => (
                      <td key={cIdx} className="py-2 px-3 border-r border-gray-800/80 whitespace-nowrap max-w-xs truncate" title={String(row[h] ?? '')}>
                        {row[h] !== undefined && row[h] !== null ? String(row[h]) : <span className="text-gray-600">null</span>}
                      </td>
                    ))}
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        <div className="flex items-center justify-between text-xs text-gray-400 pt-2">
          <span>
            Showing <strong className="text-white">{filteredRows.length > 0 ? startIndex + 1 : 0}</strong> - <strong className="text-white">{Math.min(startIndex + pageSize, filteredRows.length)}</strong> of <strong className="text-white">{filteredRows.length}</strong> entries
          </span>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
              disabled={currentPage <= 1}
              className="p-1.5 rounded-lg border border-gray-800 bg-gray-900/80 disabled:opacity-40 disabled:cursor-not-allowed hover:bg-gray-800 text-gray-300"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <span className="font-mono text-xs text-gray-300">
              Page {currentPage} / {totalPages}
            </span>
            <button
              onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
              disabled={currentPage >= totalPages}
              className="p-1.5 rounded-lg border border-gray-800 bg-gray-900/80 disabled:opacity-40 disabled:cursor-not-allowed hover:bg-gray-800 text-gray-300"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    );
  };

  // JSON Preview Renderer
  const renderJsonPreview = (data: JsonParsedData) => {
    return (
      <div className="space-y-4">
        {/* Metric Bar */}
        <div className="flex flex-wrap items-center justify-between gap-3 bg-gray-900/60 p-3 rounded-xl border border-gray-800 text-xs text-gray-300">
          <div className="flex items-center gap-4">
            <span className="flex items-center gap-1.5">
              <Database className="w-3.5 h-3.5 text-amber-400" />
              Structure: <strong className="text-white font-mono">{data.isArray ? `Array [${data.itemCount} items]` : `Object {${data.itemCount} keys}`}</strong>
            </span>
            {data.keys.length > 0 && (
              <span className="flex items-center gap-1.5 truncate max-w-sm">
                <Hash className="w-3.5 h-3.5 text-cyan-400" />
                Root Keys: <span className="text-gray-400 font-mono truncate">{data.keys.slice(0, 5).join(', ')}{data.keys.length > 5 ? '...' : ''}</span>
              </span>
            )}
          </div>

          <button
            onClick={() => handleCopy(data.rawFormatted)}
            className="flex items-center gap-1.5 px-3 py-1 bg-gray-800 hover:bg-gray-700 text-gray-200 rounded-lg text-xs font-medium transition-colors cursor-pointer"
          >
            {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5 text-gray-400" />}
            <span>{copied ? 'Copied' : 'Copy JSON'}</span>
          </button>
        </div>

        {/* JSON Code Block */}
        <div className="relative rounded-xl border border-gray-800 bg-gray-950 p-4 max-h-[52vh] overflow-auto">
          <pre className="font-mono text-xs text-amber-300/90 leading-relaxed whitespace-pre-wrap">
            {data.rawFormatted}
          </pre>
        </div>
      </div>
    );
  };

  // TXT Preview Renderer
  const renderTxtPreview = (data: TxtParsedData) => {
    return (
      <div className="space-y-4">
        {/* Metric Bar */}
        <div className="flex flex-wrap items-center justify-between gap-3 bg-gray-900/60 p-3 rounded-xl border border-gray-800 text-xs text-gray-300">
          <div className="flex items-center gap-4">
            <span className="flex items-center gap-1.5">
              <Database className="w-3.5 h-3.5 text-cyan-400" />
              Lines: <strong className="text-white font-mono">{data.lineCount}</strong>
            </span>
            <span className="flex items-center gap-1.5">
              <Hash className="w-3.5 h-3.5 text-emerald-400" />
              Words: <strong className="text-white font-mono">{data.wordCount}</strong>
            </span>
            <span className="flex items-center gap-1.5">
              <HardDrive className="w-3.5 h-3.5 text-purple-400" />
              Characters: <strong className="text-white font-mono">{data.charCount}</strong>
            </span>
          </div>

          <button
            onClick={() => handleCopy(data.text)}
            className="flex items-center gap-1.5 px-3 py-1 bg-gray-800 hover:bg-gray-700 text-gray-200 rounded-lg text-xs font-medium transition-colors cursor-pointer"
          >
            {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5 text-gray-400" />}
            <span>{copied ? 'Copied' : 'Copy Text'}</span>
          </button>
        </div>

        {/* Text Block with Line Numbers */}
        <div className="relative rounded-xl border border-gray-800 bg-gray-950 p-4 max-h-[52vh] overflow-auto flex font-mono text-xs">
          {/* Line Numbers */}
          <div className="pr-4 select-none text-gray-600 text-right font-mono border-r border-gray-800/80 mr-4">
            {Array.from({ length: Math.min(data.lineCount, 500) }).map((_, i) => (
              <div key={i} className="leading-6">{i + 1}</div>
            ))}
            {data.lineCount > 500 && <div className="leading-6 text-gray-700">...</div>}
          </div>

          {/* Text Content */}
          <div className="text-gray-200 leading-6 whitespace-pre-wrap break-words flex-1">
            {data.text}
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-6 bg-black/75 backdrop-blur-md animate-fade-in">
      <div className="relative w-full max-w-5xl bg-[#111827] border border-gray-800 rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[92vh] animate-scale-up">
        {/* Modal Header */}
        <div className="flex items-center justify-between p-4 sm:p-5 border-b border-gray-800 bg-gray-900/60">
          <div className="flex items-center gap-3 min-w-0">
            <div className="p-2 rounded-xl bg-emerald-500/20 border border-emerald-500/30 text-emerald-400 shrink-0">
              {fileItem.fileCategory === 'csv' && <FileSpreadsheet className="w-5 h-5" />}
              {fileItem.fileCategory === 'xlsx' && <Layers className="w-5 h-5" />}
              {fileItem.fileCategory === 'json' && <Code2 className="w-5 h-5" />}
              {fileItem.fileCategory === 'txt' && <FileText className="w-5 h-5" />}
            </div>

            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <h3 className="text-base sm:text-lg font-bold text-gray-100 truncate" title={fileItem.name}>
                  {fileItem.name}
                </h3>
                <span className="px-2 py-0.5 rounded-full bg-emerald-950/60 border border-emerald-500/30 text-emerald-300 text-[11px] font-semibold uppercase">
                  {fileItem.extension || fileItem.fileCategory}
                </span>
              </div>
              <p className="text-xs text-gray-400 truncate mt-0.5">
                {fileItem.relativePath || fileItem.name} • {formatBytes(fileItem.size)} • Modified {formatDate(fileItem.lastModified)}
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-2 rounded-xl bg-gray-800/80 hover:bg-gray-700 text-gray-400 hover:text-white transition-colors cursor-pointer ml-2"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-4 sm:p-6 overflow-y-auto flex-1 bg-[#0d121f]">
          {renderContent()}
        </div>

        {/* Modal Footer with Privacy & RAM Info */}
        <div className="flex flex-col sm:flex-row items-center justify-between gap-3 p-3.5 sm:p-4 border-t border-gray-800 bg-gray-900/90 text-xs">
          <div className="flex items-center gap-2 text-emerald-400 font-medium">
            <ShieldCheck className="w-4 h-4 shrink-0" />
            <span>Parsed in browser memory only. No data is stored or transmitted.</span>
          </div>

          <div className="flex items-center gap-3">
            <span className="text-gray-400 font-mono">
              Memory: <strong className="text-cyan-300">{formatBytes(fileItem.readMemoryBytes || fileItem.size)}</strong>
            </span>
            <button
              onClick={onClose}
              className="px-4 py-1.5 rounded-xl bg-gray-800 hover:bg-gray-700 text-gray-200 font-medium transition-colors cursor-pointer"
            >
              Close Preview
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
