import { useState } from 'react';
import { Database, Check, RefreshCw } from 'lucide-react';
import { apiClient } from '../api/client';

interface MetadataPersistenceBarProps {
  sessionId: string;
  defaultName: string;
  hasWorkspace: boolean;
  onOpenWorkspaceModal: () => void;
  onLog: (msg: string, type?: 'info' | 'success' | 'warn' | 'error') => void;
}

export function MetadataPersistenceBar({
  sessionId,
  defaultName,
  hasWorkspace,
  onOpenWorkspaceModal,
  onLog,
}: MetadataPersistenceBarProps) {
  const [persisted, setPersisted] = useState(false);
  const [customName] = useState(defaultName);
  const [isLoading, setIsLoading] = useState(false);
  const [showConsentDetails, setShowConsentDetails] = useState(false);


  const handlePersist = async () => {
    if (!hasWorkspace) {
      onOpenWorkspaceModal();
      return;
    }
    setIsLoading(true);
    try {
      const res = await apiClient.persistDatasetMetadata(sessionId, true, customName);
      setPersisted(true);
      onLog(`Dataset schema & aggregate profile saved to MySQL (ID: ${res.dataset_id.substring(0, 8)}).`, 'success');
    } catch (err: any) {
      onLog(`Failed to persist metadata: ${err.message}`, 'error');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="bg-gradient-to-r from-slate-900 via-indigo-950/40 to-slate-900 border border-indigo-900/40 rounded-xl p-3.5 flex flex-col md:flex-row items-start md:items-center justify-between gap-3 shadow-lg">
      <div className="flex items-start space-x-3">
        <div className="p-2 rounded-lg bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 mt-0.5">
          <Database className="w-4 h-4" />
        </div>
        <div>
          <div className="flex items-center space-x-2">
            <span className="text-xs font-semibold text-white">Reuse Library & MySQL Metadata Store</span>
            <button
              onClick={() => setShowConsentDetails(!showConsentDetails)}
              className="text-[11px] text-indigo-400 hover:text-indigo-300 underline"
            >
              {showConsentDetails ? 'Hide details' : 'Privacy & Classification details'}
            </button>
          </div>
          <p className="text-[11px] text-slate-400">
            {persisted
              ? 'Dataset metadata is securely persisted in MySQL. Techniques can be recommended for similar datasets.'
              : 'Save this schema signature and aggregate profile to enable similarity matching and recipe reuse.'}
          </p>

          {showConsentDetails && (
            <div className="mt-2 p-2.5 rounded-lg bg-slate-950/80 border border-indigo-900/60 text-[11px] text-slate-300 space-y-1">
              <div>&bull; <strong className="text-indigo-300">Never Stored:</strong> Raw CSV rows, individual cell values, and file data.</div>
              <div>&bull; <strong className="text-indigo-300">Encrypted with DEK:</strong> Column names and statistical profile distributions.</div>
              <div>&bull; <strong className="text-indigo-300">Differential Privacy Threshold:</strong> Categorical frequencies below 5 are suppressed.</div>
            </div>
          )}
        </div>
      </div>

      <div className="flex items-center space-x-2 w-full md:w-auto">
        {!persisted ? (
          <button
            onClick={handlePersist}
            disabled={isLoading}
            className="flex-1 md:flex-none flex items-center justify-center space-x-1.5 px-3.5 py-1.5 rounded-lg text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white shadow-md shadow-indigo-600/20 transition-colors"
          >
            {isLoading ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Database className="w-3.5 h-3.5" />}
            <span>Save Metadata for Reuse</span>
          </button>
        ) : (
          <div className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
            <Check className="w-3.5 h-3.5" />
            <span>Metadata Persisted</span>
          </div>
        )}
      </div>
    </div>
  );
}
