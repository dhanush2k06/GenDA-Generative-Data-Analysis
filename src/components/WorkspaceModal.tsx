import { useState } from 'react';
import {
  KeyRound,
  ShieldAlert,
  Copy,
  Check,
  RefreshCw,
  Trash2,
  Lock,
  Database,
  BookOpen,
  AlertTriangle,
  X,
} from 'lucide-react';

import { WorkspaceStatus, WorkspaceKeyInfo, PurgeReport } from '../types';
import { apiClient } from '../api/client';

interface WorkspaceModalProps {
  isOpen: boolean;
  onClose: () => void;
  workspaceStatus: WorkspaceStatus | null;
  onWorkspaceUpdated: (status: WorkspaceStatus | null) => void;
  onWorkspacePurged: () => void;
  onLog: (msg: string, type?: 'info' | 'success' | 'warn' | 'error') => void;
}

export function WorkspaceModal({
  isOpen,
  onClose,
  workspaceStatus,
  onWorkspaceUpdated,
  onWorkspacePurged,
  onLog,
}: WorkspaceModalProps) {
  const [activeTab, setActiveTab] = useState<'status' | 'create' | 'enter' | 'purge'>('status');

  // Create state
  const [newKeyInfo, setNewKeyInfo] = useState<WorkspaceKeyInfo | null>(null);
  const [acknowledged, setAcknowledged] = useState(false);
  const [copied, setCopied] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Enter state
  const [keyInput, setKeyInput] = useState('');

  // Purge state
  const [confirmText, setConfirmText] = useState('');
  const [purgeReport, setPurgeReport] = useState<PurgeReport | null>(null);

  if (!isOpen) return null;

  const handleCreateWorkspace = async () => {
    setIsLoading(true);
    setErrorMsg(null);
    try {
      const data = await apiClient.createWorkspace();
      setNewKeyInfo(data);
      setAcknowledged(false);
      const status = await apiClient.validateWorkspace();
      onWorkspaceUpdated(status);
      onLog(`Generated workspace key with ID: ${data.key_id}`, 'success');
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to create workspace');
      onLog(`Failed to create workspace: ${err.message}`, 'error');
    } finally {
      setIsLoading(false);
    }
  };

  const handleEnterKey = async () => {
    if (!keyInput.trim()) return;
    setIsLoading(true);
    setErrorMsg(null);
    try {
      apiClient.setWorkspaceKey(keyInput.trim());
      const status = await apiClient.validateWorkspace(keyInput.trim());
      onWorkspaceUpdated(status);
      onLog(`Authenticated workspace ${status.key_id} successfully.`, 'success');
      setKeyInput('');
      setActiveTab('status');
    } catch (err: any) {
      apiClient.clearWorkspaceKey();
      setErrorMsg(err.message || 'Invalid workspace key');
      onLog(`Workspace authentication failed: ${err.message}`, 'error');
    } finally {
      setIsLoading(false);
    }
  };

  const handleRotateKey = async () => {
    if (!confirm('Rotating will invalidate your current key and derive a new key for this workspace. Continue?')) {
      return;
    }
    setIsLoading(true);
    setErrorMsg(null);
    try {
      const data = await apiClient.rotateWorkspaceKey();
      setNewKeyInfo(data);
      setAcknowledged(false);
      setActiveTab('create');
      const status = await apiClient.validateWorkspace();
      onWorkspaceUpdated(status);
      onLog(`Rotated workspace key. New key ID: ${data.key_id}`, 'success');
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to rotate key');
      onLog(`Key rotation failed: ${err.message}`, 'error');
    } finally {
      setIsLoading(false);
    }
  };

  const handlePurge = async () => {
    if (confirmText.trim() !== 'REVOKE PURGE') {
      setErrorMsg('Please type "REVOKE PURGE" exactly to confirm complete destruction.');
      return;
    }

    setIsLoading(true);
    setErrorMsg(null);
    try {
      const res = await apiClient.revokeWorkspace();
      setPurgeReport(res.purge_report);
      onWorkspacePurged();
      onLog('Workspace crypto-shredded and all records purged completely.', 'warn');
    } catch (err: any) {
      setErrorMsg(err.message || 'Purge failed');
      onLog(`Purge error: ${err.message}`, 'error');
    } finally {
      setIsLoading(false);
    }
  };

  const copyToClipboard = () => {
    if (newKeyInfo) {
      navigator.clipboard.writeText(newKeyInfo.workspace_key);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-fade-in">
      <div className="relative w-full max-w-xl bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl overflow-hidden flex flex-col">
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between bg-slate-900/60">
          <div className="flex items-center space-x-3">
            <div className="p-2 rounded-xl bg-cyan-500/10 border border-cyan-500/20 text-cyan-400">
              <KeyRound className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-semibold text-white">Workspace & Key Security</h3>
              <p className="text-xs text-slate-400">Envelope-encrypted MySQL isolation & crypto-shredding</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Tab Navigation */}
        <div className="px-6 pt-3 border-b border-slate-800/80 flex space-x-2 bg-slate-950/40">
          <button
            onClick={() => { setActiveTab('status'); setErrorMsg(null); }}
            className={`px-3 py-2 text-xs font-medium rounded-t-lg border-b-2 transition-colors ${
              activeTab === 'status'
                ? 'border-cyan-400 text-cyan-400 bg-slate-900'
                : 'border-transparent text-slate-400 hover:text-slate-300'
            }`}
          >
            Status
          </button>
          <button
            onClick={() => { setActiveTab('enter'); setErrorMsg(null); }}
            className={`px-3 py-2 text-xs font-medium rounded-t-lg border-b-2 transition-colors ${
              activeTab === 'enter'
                ? 'border-cyan-400 text-cyan-400 bg-slate-900'
                : 'border-transparent text-slate-400 hover:text-slate-300'
            }`}
          >
            Enter Key
          </button>
          <button
            onClick={() => { setActiveTab('create'); setErrorMsg(null); }}
            className={`px-3 py-2 text-xs font-medium rounded-t-lg border-b-2 transition-colors ${
              activeTab === 'create'
                ? 'border-cyan-400 text-cyan-400 bg-slate-900'
                : 'border-transparent text-slate-400 hover:text-slate-300'
            }`}
          >
            Create New Key
          </button>
          <button
            onClick={() => { setActiveTab('purge'); setErrorMsg(null); }}
            className={`px-3 py-2 text-xs font-medium rounded-t-lg border-b-2 transition-colors ${
              activeTab === 'purge'
                ? 'border-rose-500 text-rose-400 bg-slate-900'
                : 'border-transparent text-slate-400 hover:text-rose-400'
            }`}
          >
            Purge & Revoke
          </button>
        </div>

        {/* Content Area */}
        <div className="p-6 space-y-4 max-h-[75vh] overflow-y-auto">
          {errorMsg && (
            <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-center space-x-2">
              <AlertTriangle className="w-4 h-4 flex-shrink-0" />
              <span>{errorMsg}</span>
            </div>
          )}

          {/* TAB: STATUS */}
          {activeTab === 'status' && (
            <div className="space-y-4">
              {workspaceStatus ? (
                <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800 space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-slate-400">Workspace Status:</span>
                    <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 uppercase">
                      {workspaceStatus.status}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-slate-400">Key ID (Public):</span>
                    <span className="font-mono text-xs text-cyan-400 bg-slate-900 px-2 py-1 rounded border border-slate-800">
                      {workspaceStatus.key_id}
                    </span>
                  </div>
                  <div className="grid grid-cols-2 gap-3 pt-2">
                    <div className="p-3 rounded-lg bg-slate-900 border border-slate-800/80 flex items-center space-x-3">
                      <Database className="w-4 h-4 text-indigo-400" />
                      <div>
                        <div className="text-sm font-bold text-white">{workspaceStatus.datasets_count}</div>
                        <div className="text-[11px] text-slate-400">Stored Metadata</div>
                      </div>
                    </div>
                    <div className="p-3 rounded-lg bg-slate-900 border border-slate-800/80 flex items-center space-x-3">
                      <BookOpen className="w-4 h-4 text-cyan-400" />
                      <div>
                        <div className="text-sm font-bold text-white">{workspaceStatus.recipes_count}</div>
                        <div className="text-[11px] text-slate-400">Reusable Recipes</div>
                      </div>
                    </div>
                  </div>

                  <div className="pt-3 border-t border-slate-800 flex justify-between">
                    <button
                      onClick={handleRotateKey}
                      disabled={isLoading}
                      className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-slate-800 hover:bg-slate-700 text-slate-200 transition-colors"
                    >
                      <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
                      <span>Rotate Key</span>
                    </button>
                    <button
                      onClick={() => setActiveTab('purge')}
                      className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-rose-400 hover:bg-rose-950/40 border border-rose-900/40 rounded-lg transition-colors"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                      <span>Revoke & Purge</span>
                    </button>
                  </div>
                </div>
              ) : (
                <div className="text-center py-6 space-y-3">
                  <Lock className="w-8 h-8 text-slate-600 mx-auto" />
                  <p className="text-xs text-slate-400 max-w-sm mx-auto">
                    No active workspace key is attached. Operations are running in anonymous session RAM.
                    Create or enter a workspace key to persist metadata and reusable recipes.
                  </p>
                  <div className="flex justify-center space-x-3 pt-2">
                    <button
                      onClick={() => setActiveTab('create')}
                      className="px-4 py-2 rounded-xl text-xs font-semibold bg-cyan-600 hover:bg-cyan-500 text-white shadow-lg shadow-cyan-600/20"
                    >
                      Create Workspace Key
                    </button>
                    <button
                      onClick={() => setActiveTab('enter')}
                      className="px-4 py-2 rounded-xl text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-200"
                    >
                      Enter Existing Key
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* TAB: ENTER KEY */}
          {activeTab === 'enter' && (
            <div className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1.5">
                  Enter Workspace Key (Format: <code className="text-cyan-400">gk_&lt;key_id&gt;_&lt;secret&gt;</code>)
                </label>
                <input
                  type="password"
                  value={keyInput}
                  onChange={(e) => setKeyInput(e.target.value)}
                  placeholder="gk_0123456789abcdef_..."
                  className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-700 text-white font-mono text-xs focus:outline-none focus:border-cyan-500"
                />
              </div>
              <p className="text-[11px] text-slate-400">
                The key is retained strictly in browser RAM for the session. It is never saved to localStorage, sessionStorage, or cookies.
              </p>
              <button
                onClick={handleEnterKey}
                disabled={isLoading || !keyInput.trim()}
                className="w-full py-2.5 rounded-xl text-xs font-semibold bg-cyan-600 hover:bg-cyan-500 disabled:opacity-50 text-white shadow-lg shadow-cyan-600/20 flex items-center justify-center space-x-2"
              >
                {isLoading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Lock className="w-4 h-4" />}
                <span>Authenticate Workspace</span>
              </button>
            </div>
          )}

          {/* TAB: CREATE NEW KEY */}
          {activeTab === 'create' && (
            <div className="space-y-4">
              {!newKeyInfo ? (
                <div className="space-y-3">
                  <p className="text-xs text-slate-300">
                    A workspace key gives you an isolated, envelope-encrypted partition in MySQL.
                    The server only stores an HKDF verifier and wrapped DEK. It never stores your key.
                  </p>
                  <button
                    onClick={handleCreateWorkspace}
                    disabled={isLoading}
                    className="w-full py-2.5 rounded-xl text-xs font-semibold bg-cyan-600 hover:bg-cyan-500 disabled:opacity-50 text-white shadow-lg shadow-cyan-600/20 flex items-center justify-center space-x-2"
                  >
                    {isLoading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <KeyRound className="w-4 h-4" />}
                    <span>Generate Workspace Key</span>
                  </button>
                </div>
              ) : (
                <div className="space-y-4 animate-fade-in">
                  <div className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/30 text-amber-300 text-xs flex items-start space-x-2">
                    <ShieldAlert className="w-4 h-4 mt-0.5 flex-shrink-0" />
                    <div>
                      <span className="font-semibold block mb-0.5">Save this key now!</span>
                      It is displayed only once. If lost, your encrypted metadata cannot be recovered, by design.
                    </div>
                  </div>

                  <div className="space-y-1.5">
                    <div className="flex items-center justify-between text-xs text-slate-400">
                      <span>Your Secret Workspace Key:</span>
                      <button
                        onClick={copyToClipboard}
                        className="flex items-center space-x-1 text-cyan-400 hover:text-cyan-300 font-medium"
                      >
                        {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                        <span>{copied ? 'Copied' : 'Copy Key'}</span>
                      </button>
                    </div>
                    <div className="p-3 rounded-xl bg-slate-950 border border-slate-700 font-mono text-xs text-cyan-300 break-all select-all">
                      {newKeyInfo.workspace_key}
                    </div>
                  </div>

                  <div className="flex items-center space-x-2 pt-2">
                    <input
                      type="checkbox"
                      id="ack"
                      checked={acknowledged}
                      onChange={(e) => setAcknowledged(e.target.checked)}
                      className="rounded border-slate-700 bg-slate-950 text-cyan-500 focus:ring-cyan-500"
                    />
                    <label htmlFor="ack" className="text-xs text-slate-300 cursor-pointer">
                      I have copied and saved my workspace key in a secure location.
                    </label>
                  </div>

                  <button
                    onClick={() => {
                      if (acknowledged) {
                        setNewKeyInfo(null);
                        setActiveTab('status');
                      }
                    }}
                    disabled={!acknowledged}
                    className="w-full py-2 rounded-xl text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 disabled:opacity-40 text-white shadow-lg transition-colors"
                  >
                    Confirm & Activate Workspace
                  </button>
                </div>
              )}
            </div>
          )}

          {/* TAB: PURGE & REVOKE */}
          {activeTab === 'purge' && (
            <div className="space-y-4">
              {purgeReport ? (
                <div className="p-4 rounded-xl bg-slate-950/80 border border-emerald-500/30 space-y-3">
                  <div className="flex items-center space-x-2 text-emerald-400 text-sm font-semibold">
                    <Check className="w-4 h-4" />
                    <span>Workspace Purge Complete</span>
                  </div>
                  <p className="text-xs text-slate-400">
                    The workspace was crypto-shredded. Wrapped DEK and verifiers were destroyed.
                    All MySQL rows and in-memory caches have been permanently eliminated.
                  </p>
                  <div className="p-2.5 rounded-lg bg-slate-900 border border-slate-800 text-[11px] font-mono text-slate-300 space-y-1">
                    <div>Steps Completed: {purgeReport.steps_completed.join(' -> ')}</div>
                    <div>Database Rows Deleted: {JSON.stringify(purgeReport.deleted_db_rows || {})}</div>
                    <div>Memory Purged: {JSON.stringify(purgeReport.registry_stats || {})}</div>
                  </div>
                  <button
                    onClick={() => {
                      setPurgeReport(null);
                      setConfirmText('');
                      setActiveTab('enter');
                      onClose();
                    }}
                    className="w-full py-2 rounded-xl text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-200"
                  >
                    Close
                  </button>
                </div>
              ) : (
                <div className="space-y-3">
                  <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs space-y-1">
                    <div className="font-semibold flex items-center space-x-1.5">
                      <AlertTriangle className="w-4 h-4 flex-shrink-0" />
                      <span>Irreversible Crypto-Shredding & Deletion</span>
                    </div>
                    <p className="text-[11px] text-rose-200/80">
                      Revoking your key deletes the wrapped DEK, making leftover database ciphertext unreadable.
                      All dataset profiles, analysis history, caches, and in-memory frames will be purged immediately.
                    </p>
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-slate-300 mb-1">
                      Type <span className="font-mono text-rose-400 font-bold">REVOKE PURGE</span> to confirm:
                    </label>
                    <input
                      type="text"
                      value={confirmText}
                      onChange={(e) => setConfirmText(e.target.value)}
                      placeholder="REVOKE PURGE"
                      className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-rose-900/60 text-rose-300 font-mono text-xs focus:outline-none focus:border-rose-500"
                    />
                  </div>

                  <button
                    onClick={handlePurge}
                    disabled={isLoading || confirmText.trim() !== 'REVOKE PURGE'}
                    className="w-full py-2.5 rounded-xl text-xs font-semibold bg-rose-600 hover:bg-rose-500 disabled:opacity-40 text-white shadow-lg shadow-rose-600/20 flex items-center justify-center space-x-2 transition-colors"
                  >
                    {isLoading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Trash2 className="w-4 h-4" />}
                    <span>Execute 8-Step Complete Purge</span>
                  </button>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
