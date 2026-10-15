import { X, Download, ExternalLink, FileText } from 'lucide-react';
import { apiClient } from '../api/client';

interface ReportModalProps {
  isOpen: boolean;
  onClose: () => void;
  sessionId: string;
  filename: string;
}

export function ReportModal({ isOpen, onClose, sessionId, filename }: ReportModalProps) {
  if (!isOpen) return null;

  const reportUrl = apiClient.getReportHtmlUrl(sessionId);

  const handleDownload = () => {
    apiClient.downloadReport(sessionId, filename);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-5xl h-[90vh] flex flex-col shadow-2xl overflow-hidden">
        {/* Modal Header */}
        <div className="p-4 border-b border-slate-800 bg-slate-950 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="p-2 rounded-lg bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
              <FileText className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-slate-100">
                GenDA Analytical Report Preview
              </h3>
              <p className="text-xs text-slate-400">
                Self-contained Jinja2 HTML report &bull; Embedded Plotly figures &bull; Zero external data leakage
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            <button
              onClick={handleDownload}
              className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white shadow-sm transition-colors"
            >
              <Download className="w-3.5 h-3.5" />
              <span>Download HTML</span>
            </button>

            <a
              href={reportUrl}
              target="_blank"
              rel="noreferrer"
              className="flex items-center space-x-1 px-3 py-1.5 rounded-lg text-xs font-medium bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors"
            >
              <span>Open in New Tab</span>
              <ExternalLink className="w-3.5 h-3.5 ml-1" />
            </a>

            <button
              onClick={onClose}
              className="p-1.5 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800 ml-2"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Iframe View */}
        <div className="flex-1 bg-slate-950 p-2">
          <iframe
            src={reportUrl}
            title="GenDA HTML Report"
            className="w-full h-full rounded-xl border border-slate-800/80 bg-[#0b0f19]"
          />
        </div>
      </div>
    </div>
  );
}
