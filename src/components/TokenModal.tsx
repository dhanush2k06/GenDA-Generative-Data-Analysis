import { useState } from 'react';
import { X, Key, Check, Copy, Shield, RefreshCw } from 'lucide-react';
import { apiClient } from '../api/client';

interface TokenModalProps {
  isOpen: boolean;
  onClose: () => void;
  onTokenUpdated: () => void;
}

export function TokenModal({ isOpen, onClose, onTokenUpdated }: TokenModalProps) {
  const [tokenInput, setTokenInput] = useState(apiClient.getToken());
  const [copied, setCopied] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<{ success: boolean; msg: string } | null>(null);

  if (!isOpen) return null;

  const handleSave = () => {
    apiClient.setToken(tokenInput.trim());
    onTokenUpdated();
    onClose();
  };

  const handleCopy = () => {
    navigator.clipboard.writeText(tokenInput);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleTest = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      apiClient.setToken(tokenInput.trim());
      const ok = await apiClient.verifyAuth();
      if (ok) {
        setTestResult({ success: true, msg: 'Authentication successful! Loopback connection verified.' });
      } else {
        setTestResult({ success: false, msg: 'Authentication rejected: Invalid token or service unreachable.' });
      }
    } catch (err: any) {
      setTestResult({ success: false, msg: err.message || 'Connection test failed.' });
    } finally {
      setTesting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-md p-6 space-y-4 shadow-2xl relative">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-slate-400 hover:text-slate-200"
        >
          <X className="w-5 h-5" />
        </button>

        <div className="flex items-center space-x-3">
          <div className="p-2.5 rounded-xl bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
            <Key className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-base font-semibold text-slate-100">
              Security Token Configuration
            </h3>
            <p className="text-xs text-slate-400">
              Loopback per-launch authentication (<code className="text-cyan-400">X-GenDA-Token</code>)
            </p>
          </div>
        </div>

        <div className="space-y-2">
          <label className="text-xs font-medium text-slate-300 block">
            Active Security Token
          </label>
          <div className="relative">
            <input
              type="text"
              value={tokenInput}
              onChange={(e) => setTokenInput(e.target.value)}
              placeholder="Paste launch token..."
              className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2.5 text-xs text-slate-200 font-mono pr-20 focus:outline-none focus:border-cyan-500"
            />
            <button
              onClick={handleCopy}
              className="absolute right-2 top-1/2 -translate-y-1/2 px-2.5 py-1 text-[11px] font-medium bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg flex items-center space-x-1"
            >
              {copied ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
              <span>{copied ? 'Copied' : 'Copy'}</span>
            </button>
          </div>
          <p className="text-[11px] text-slate-500">
            The local Python service generates this cryptographic token when launched or auto-reads it from <code className="text-slate-400">.genda_token</code>.
          </p>
        </div>

        {testResult && (
          <div
            className={`p-3 rounded-xl text-xs border ${
              testResult.success
                ? 'bg-emerald-950/30 text-emerald-300 border-emerald-800/60'
                : 'bg-rose-950/30 text-rose-300 border-rose-800/60'
            }`}
          >
            {testResult.msg}
          </div>
        )}

        <div className="flex items-center justify-between pt-2">
          <button
            type="button"
            onClick={handleTest}
            disabled={testing}
            className="flex items-center space-x-1.5 px-3 py-2 text-xs font-medium text-slate-300 bg-slate-800 hover:bg-slate-700 rounded-xl transition-colors"
          >
            {testing ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Shield className="w-3.5 h-3.5 text-cyan-400" />}
            <span>Test Auth</span>
          </button>

          <div className="flex items-center space-x-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-xs font-medium text-slate-400 hover:text-slate-200"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handleSave}
              className="px-4 py-2 text-xs font-semibold bg-cyan-600 hover:bg-cyan-500 text-white rounded-xl shadow-md shadow-cyan-600/20"
            >
              Save Token
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
