import { useState, useEffect } from 'react';
import {
  Database,
  BookOpen,
  History,
  Trash2,
  RefreshCw,
  X,
  Shield,
  ChevronRight,
  Fingerprint,
  AlertCircle,
} from 'lucide-react';

import { StoredDatasetSummary, StoredDatasetDetail, Recipe, AuditEventItem } from '../types';
import { apiClient } from '../api/client';

interface ReuseLibraryModalProps {
  isOpen: boolean;
  onClose: () => void;
  onLog: (msg: string, type?: 'info' | 'success' | 'warn' | 'error') => void;
}

export function ReuseLibraryModal({ isOpen, onClose, onLog }: ReuseLibraryModalProps) {
  const [activeTab, setActiveTab] = useState<'datasets' | 'recipes' | 'audit'>('datasets');
  const [datasets, setDatasets] = useState<StoredDatasetSummary[]>([]);
  const [selectedDataset, setSelectedDataset] = useState<StoredDatasetDetail | null>(null);
  const [recipes, setRecipes] = useState<Recipe[]>([]);
  const [auditEvents, setAuditEvents] = useState<AuditEventItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen) {
      loadTabContent(activeTab);
    }
  }, [isOpen, activeTab]);

  const loadTabContent = async (tab: 'datasets' | 'recipes' | 'audit') => {
    setIsLoading(true);
    setErrorMsg(null);
    try {
      if (tab === 'datasets') {
        const res = await apiClient.listStoredDatasets();
        setDatasets(res.datasets);
        setSelectedDataset(null);
      } else if (tab === 'recipes') {
        const res = await apiClient.listRecipes();
        setRecipes(res.recipes);
      } else if (tab === 'audit') {
        const res = await apiClient.listAuditEvents();
        setAuditEvents(res.events);
      }
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to load library items.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSelectDataset = async (id: string) => {
    setIsLoading(true);
    try {
      const detail = await apiClient.getStoredDataset(id);
      setSelectedDataset(detail);
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to fetch dataset details');
    } finally {
      setIsLoading(false);
    }
  };

  const handleDeleteDataset = async (id: string, name: string) => {
    if (!confirm(`Permanently delete stored metadata for "${name}"?`)) return;
    try {
      await apiClient.deleteStoredDataset(id);
      onLog(`Deleted stored metadata for "${name}".`, 'info');
      if (selectedDataset?.id === id) {
        setSelectedDataset(null);
      }
      loadTabContent('datasets');
    } catch (err: any) {
      setErrorMsg(err.message || 'Delete failed');
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-fade-in">
      <div className="relative w-full max-w-4xl bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[85vh]">
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between bg-slate-900/80">
          <div className="flex items-center space-x-3">
            <div className="p-2 rounded-xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-400">
              <Database className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-semibold text-white">Metadata & Reusable Recipe Library</h3>
              <p className="text-xs text-slate-400">MySQL encrypted store scoped to your active workspace key</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Tab Nav */}
        <div className="px-6 pt-3 border-b border-slate-800/80 flex items-center justify-between bg-slate-950/40">
          <div className="flex space-x-2">
            <button
              onClick={() => setActiveTab('datasets')}
              className={`px-3 py-2 text-xs font-medium rounded-t-lg border-b-2 flex items-center space-x-1.5 transition-colors ${
                activeTab === 'datasets'
                  ? 'border-indigo-400 text-indigo-400 bg-slate-900'
                  : 'border-transparent text-slate-400 hover:text-slate-300'
              }`}
            >
              <Database className="w-3.5 h-3.5" />
              <span>Stored Datasets ({datasets.length})</span>
            </button>
            <button
              onClick={() => setActiveTab('recipes')}
              className={`px-3 py-2 text-xs font-medium rounded-t-lg border-b-2 flex items-center space-x-1.5 transition-colors ${
                activeTab === 'recipes'
                  ? 'border-indigo-400 text-indigo-400 bg-slate-900'
                  : 'border-transparent text-slate-400 hover:text-slate-300'
              }`}
            >
              <BookOpen className="w-3.5 h-3.5" />
              <span>Reusable Recipes ({recipes.length})</span>
            </button>
            <button
              onClick={() => setActiveTab('audit')}
              className={`px-3 py-2 text-xs font-medium rounded-t-lg border-b-2 flex items-center space-x-1.5 transition-colors ${
                activeTab === 'audit'
                  ? 'border-indigo-400 text-indigo-400 bg-slate-900'
                  : 'border-transparent text-slate-400 hover:text-slate-300'
              }`}
            >
              <History className="w-3.5 h-3.5" />
              <span>Audit Log</span>
            </button>
          </div>
          <button
            onClick={() => loadTabContent(activeTab)}
            className="p-1.5 text-slate-400 hover:text-slate-200 hover:bg-slate-800 rounded-lg transition-colors"
            title="Refresh"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 flex-1 overflow-y-auto">
          {errorMsg && (
            <div className="mb-4 p-3 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-center space-x-2">
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
              <span>{errorMsg}</span>
            </div>
          )}

          {/* TAB: DATASETS */}
          {activeTab === 'datasets' && (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {/* Dataset List */}
              <div className="md:col-span-1 space-y-2 border-r border-slate-800 pr-4">
                <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
                  Stored Datasets
                </div>
                {datasets.length === 0 ? (
                  <div className="text-xs text-slate-500 py-6 text-center">
                    No datasets saved in this workspace yet.
                  </div>
                ) : (
                  datasets.map((ds) => (
                    <div
                      key={ds.id}
                      onClick={() => handleSelectDataset(ds.id)}
                      className={`p-3 rounded-xl border text-left cursor-pointer transition-all ${
                        selectedDataset?.id === ds.id
                          ? 'bg-indigo-950/40 border-indigo-500/50 text-white'
                          : 'bg-slate-950/40 border-slate-800 text-slate-300 hover:border-slate-700'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-semibold truncate">{ds.name}</span>
                        <ChevronRight className="w-3.5 h-3.5 text-slate-500" />
                      </div>
                      <div className="mt-1 text-[11px] text-slate-400">
                        {ds.row_count.toLocaleString()} rows &bull; {ds.col_count} cols
                      </div>
                      <div className="mt-1 flex items-center justify-between">
                        <span className="text-[10px] text-slate-500">
                          {ds.created_at ? new Date(ds.created_at).toLocaleDateString() : ''}
                        </span>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleDeleteDataset(ds.id, ds.name);
                          }}
                          className="p-1 text-slate-500 hover:text-rose-400 rounded transition-colors"
                          title="Delete Dataset"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </div>
                  ))
                )}
              </div>

              {/* Dataset Detail */}
              <div className="md:col-span-2">
                {selectedDataset ? (
                  <div className="space-y-4">
                    <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                      <div>
                        <h4 className="text-sm font-bold text-white">{selectedDataset.name}</h4>
                        <div className="flex items-center space-x-2 mt-1">
                          <span className="font-mono text-[10px] text-indigo-400 bg-indigo-950/50 px-2 py-0.5 rounded border border-indigo-800/40 flex items-center space-x-1">
                            <Fingerprint className="w-3 h-3" />
                            <span>{selectedDataset.fingerprint.substring(0, 16)}...</span>
                          </span>
                          <span className="text-xs text-slate-400">
                            {selectedDataset.row_count.toLocaleString()} rows &bull; {selectedDataset.col_count} columns
                          </span>
                        </div>
                      </div>
                      <button
                        onClick={() => handleDeleteDataset(selectedDataset.id, selectedDataset.name)}
                        className="px-3 py-1.5 rounded-lg text-xs font-medium bg-rose-950/60 hover:bg-rose-900 text-rose-300 border border-rose-800/60 transition-colors flex items-center space-x-1"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                        <span>Delete</span>
                      </button>
                    </div>

                    <div className="space-y-2">
                      <div className="text-xs font-semibold text-slate-300">Classified Column Signatures:</div>
                      <div className="overflow-x-auto border border-slate-800 rounded-xl">
                        <table className="w-full text-[11px] text-left">
                          <thead className="bg-slate-950/60 text-slate-400 uppercase font-mono text-[10px]">
                            <tr>
                              <th className="px-3 py-2">Column</th>
                              <th className="px-3 py-2">Class</th>
                              <th className="px-3 py-2">Nulls</th>
                              <th className="px-3 py-2">Cardinality</th>
                              <th className="px-3 py-2">Skew</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-slate-800 font-mono">
                            {selectedDataset.columns.map((c) => (
                              <tr key={c.id} className="hover:bg-slate-800/30">
                                <td className="px-3 py-2 text-white font-medium">{c.name}</td>
                                <td className="px-3 py-2 text-indigo-300">{c.type_class}</td>
                                <td className="px-3 py-2 text-slate-400">{c.null_rate_bucket}</td>
                                <td className="px-3 py-2 text-slate-400">{c.distinct_ratio_bucket}</td>
                                <td className="px-3 py-2 text-slate-400">{c.skew_bucket}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="text-center py-16 text-slate-500 text-xs">
                    Select a dataset on the left to view encrypted schema features and profile aggregates.
                  </div>
                )}
              </div>
            </div>
          )}

          {/* TAB: RECIPES */}
          {activeTab === 'recipes' && (
            <div className="space-y-3">
              {recipes.length === 0 ? (
                <div className="text-center py-12 text-slate-500 text-xs">
                  No recipes saved yet. Run analyses and click "Save as Recipe" to build your technique library.
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {recipes.map((r) => (
                    <div key={r.id} className="p-4 rounded-xl bg-slate-950/60 border border-slate-800 space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-bold text-white">{r.name}</span>
                        <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-indigo-950 text-indigo-300 border border-indigo-800">
                          {r.category}
                        </span>
                      </div>
                      <p className="text-xs text-slate-400">{r.description || 'No description provided.'}</p>
                      <div className="p-2 rounded bg-slate-900 border border-slate-800/80 font-mono text-[10px] text-cyan-300 overflow-x-auto">
                        {JSON.stringify(r.spec, null, 2)}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* TAB: AUDIT */}
          {activeTab === 'audit' && (
            <div className="space-y-2">
              <div className="text-xs font-semibold text-slate-400 mb-2">
                Security Audit Log (Key operations & Metadata actions):
              </div>
              <div className="divide-y divide-slate-800 border border-slate-800 rounded-xl overflow-hidden bg-slate-950/40">
                {auditEvents.length === 0 ? (
                  <div className="text-center py-8 text-slate-500 text-xs">No audit events recorded.</div>
                ) : (
                  auditEvents.map((evt) => (
                    <div key={evt.id} className="px-4 py-2.5 flex items-center justify-between text-xs font-mono">
                      <div className="flex items-center space-x-2">
                        <Shield className="w-3.5 h-3.5 text-cyan-400 flex-shrink-0" />
                        <span className="text-slate-200">{evt.action}</span>
                      </div>
                      <div className="flex items-center space-x-3 text-slate-500 text-[11px]">
                        <span>Key: {evt.key_id}</span>
                        <span>{new Date(evt.created_at).toLocaleString()}</span>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
