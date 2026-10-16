import { useState, useEffect, useCallback } from 'react';
import {
  Table,
  BarChart3,
  Calculator,
  Trash2,
  AlertCircle,
  HardDrive,
  Play,
  Sparkles,
} from 'lucide-react';

import { Navbar } from './components/Navbar';
import { PrivacyBanner } from './components/PrivacyBanner';
import { FileSelector } from './components/FileSelector';
import { DataPreviewTable } from './components/DataPreviewTable';
import { ProfileDashboard } from './components/ProfileDashboard';
import { AnalysisWorkspace } from './components/AnalysisWorkspace';
import { ResultCard } from './components/ResultCard';
import { TokenModal } from './components/TokenModal';
import { ReportModal } from './components/ReportModal';
import { AuditLog } from './components/AuditLog';
import { WorkspaceModal } from './components/WorkspaceModal';
import { ReuseLibraryModal } from './components/ReuseLibraryModal';
import { MetadataPersistenceBar } from './components/MetadataPersistenceBar';
import { SimilarityRecommendationsCard } from './components/SimilarityRecommendationsCard';
import { apiClient } from './api/client';
import { getSampleCsvFile } from './utils/sampleData';
import { formatBytes } from './utils/formatters';
import {
  ServiceHealth,
  DataPreview,
  DatasetProfile,
  AnalysisResult,
  AnalysisRequest,
  LogEntry,
  WorkspaceStatus,
} from './types';

export function App() {
  const [health, setHealth] = useState<ServiceHealth>({ status: 'checking' });
  const [workspaceStatus, setWorkspaceStatus] = useState<WorkspaceStatus | null>(null);
  const [preview, setPreview] = useState<DataPreview | null>(null);
  const [profile, setProfile] = useState<DatasetProfile | null>(null);
  const [results, setResults] = useState<AnalysisResult[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [loadingText, setLoadingText] = useState<string>('');
  const [activeTab, setActiveTab] = useState<'preview' | 'profile' | 'analyze' | 'results'>('preview');

  // Modals
  const [tokenModalOpen, setTokenModalOpen] = useState(false);
  const [reportModalOpen, setReportModalOpen] = useState(false);
  const [workspaceModalOpen, setWorkspaceModalOpen] = useState(false);
  const [reuseLibraryOpen, setReuseLibraryOpen] = useState(false);

  // Preselection helpers
  const [preselectedCol, setPreselectedCol] = useState<string | null>(null);
  const [preselectedOp, setPreselectedOp] = useState<string | null>(null);

  // Diagnostics & audit logs
  const [logs, setLogs] = useState<LogEntry[]>([
    {
      id: 'init-0',
      timestamp: new Date().toLocaleTimeString(),
      action: 'GenDA Local Interface initialized. Checking loopback Python service...',
      type: 'info',
    },
  ]);

  const addLog = useCallback((action: string, type: LogEntry['type'] = 'info') => {
    const newEntry: LogEntry = {
      id: Math.random().toString(36).substring(2, 9),
      timestamp: new Date().toLocaleTimeString(),
      action,
      type,
    };
    setLogs((prev) => [newEntry, ...prev.slice(0, 49)]);
  }, []);

  const checkHealth = useCallback(async () => {
    const h = await apiClient.checkHealth();
    setHealth(h);
    if (h.status === 'ok') {
      addLog(`Connected to loopback Python service (v${h.version || '0.2.0'}) at 127.0.0.1:8000.`, 'success');
      // If a workspace key is in memory, validate it
      if (apiClient.getWorkspaceKey()) {
        try {
          const ws = await apiClient.validateWorkspace();
          setWorkspaceStatus(ws);
        } catch {
          apiClient.clearWorkspaceKey();
          setWorkspaceStatus(null);
        }
      }
    } else {
      addLog(`Local Python service unavailable: ${h.error || 'Connection refused'}. Ensure 'python -m genda' is running.`, 'warn');
    }
  }, [addLog]);

  useEffect(() => {
    checkHealth();
  }, [checkHealth]);

  // Handle explicit file selection
  const handleFileSelected = async (file: File) => {
    setIsLoading(true);
    setLoadingText(`Uploading "${file.name}" to local Python loopback memory...`);
    addLog(`Sending "${file.name}" (${formatBytes(file.size)}) via multipart upload to local service...`, 'info');

    try {
      const dataPreview = await apiClient.uploadCsv(file);
      setPreview(dataPreview);
      setResults([]);
      addLog(
        `Parsed "${file.name}" with Polars: ${dataPreview.row_count.toLocaleString()} rows, ${dataPreview.col_count} columns detected.`,
        'success'
      );

      // Immediately trigger data profiling
      setLoadingText('Computing statistical profile, distributions, and null rates...');
      const datasetProfile = await apiClient.getProfile(dataPreview.session_id);
      setProfile(datasetProfile);
      addLog(
        `Profile complete: ${datasetProfile.columns.length} columns profiled, ${datasetProfile.duplicate_rows} duplicate rows found.`,
        'success'
      );

      setActiveTab('profile');
    } catch (err: any) {
      addLog(`Error processing file: ${err.message}`, 'error');
    } finally {
      setIsLoading(false);
      setLoadingText('');
    }
  };

  const handleLoadSample = (sampleKey: string) => {
    const key = (sampleKey === 'messages' || sampleKey === 'synthetic') ? sampleKey : 'users';
    const file = getSampleCsvFile(key);
    handleFileSelected(file);
  };


  const handleClearSession = async () => {
    if (!preview) return;
    try {
      await apiClient.clearSession(preview.session_id);
      setPreview(null);
      setProfile(null);
      setResults([]);
      setActiveTab('preview');
      addLog('Session cleared: all DataFrames and computed results freed from memory.', 'info');
    } catch (err: any) {
      addLog(`Failed to clear session: ${err.message}`, 'warn');
      // Reset client anyway
      setPreview(null);
      setProfile(null);
      setResults([]);
      setActiveTab('preview');
    }
  };

  const handleWorkspacePurged = () => {
    setWorkspaceStatus(null);
    setPreview(null);
    setProfile(null);
    setResults([]);
    setActiveTab('preview');
    addLog('Workspace purged completely: all database rows, in-memory frames, and caches destroyed.', 'warn');
  };

  const handleRunAnalysis = async (request: AnalysisRequest) => {
    if (!preview) return;
    setIsLoading(true);
    setLoadingText(`Executing ${request.operation} with Polars & DuckDB validation...`);
    addLog(`Running operation "${request.operation}" with cross-engine verification...`, 'info');

    try {
      const result = await apiClient.runAnalysis(preview.session_id, request);
      setResults((prev) => [result, ...prev]);
      addLog(
        `Completed "${result.title}" in ${result.execution_time_ms}ms. Cross-engine check: ${
          result.cross_engine_match ? 'MATCH' : 'PASSED'
        }.`,
        'success'
      );
      setActiveTab('results');
    } catch (err: any) {
      addLog(`Analysis failed: ${err.message}`, 'error');
    } finally {
      setIsLoading(false);
      setLoadingText('');
    }
  };

  const handleSelectColForAnalysis = (columnName: string) => {
    setPreselectedCol(columnName);
    setPreselectedOp('numeric_summary');
    setActiveTab('analyze');
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans selection:bg-cyan-500/30 selection:text-cyan-200">
      {/* Top Navigation */}
      <Navbar
        health={health}
        workspaceStatus={workspaceStatus}
        hasActiveSession={!!preview}
        hasResults={results.length > 0}
        onClearSession={handleClearSession}
        onOpenReport={() => setReportModalOpen(true)}
        onOpenTokenModal={() => setTokenModalOpen(true)}
        onOpenWorkspaceModal={() => setWorkspaceModalOpen(true)}
        onOpenReuseLibrary={() => setReuseLibraryOpen(true)}
        onRefreshHealth={checkHealth}
      />

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
        {/* Privacy & Airgap Guarantee Banner */}
        <PrivacyBanner />

        {/* Global Loading Overlay */}
        {isLoading && (
          <div className="fixed inset-0 z-50 bg-slate-950/70 backdrop-blur-sm flex items-center justify-center p-4">
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-2xl flex flex-col items-center space-y-4 max-w-sm text-center animate-fade-in">
              <div className="relative">
                <div className="w-12 h-12 rounded-full border-2 border-cyan-500/20 border-t-cyan-500 animate-spin" />
                <Sparkles className="w-5 h-5 text-cyan-400 absolute inset-0 m-auto" />
              </div>
              <p className="text-sm font-semibold text-slate-200">{loadingText || 'Processing...'}</p>
              <p className="text-xs text-slate-400">Deterministic loopback calculation on your machine.</p>
            </div>
          </div>
        )}

        {/* View 1: No file selected */}
        {!preview ? (
          <div className="space-y-6">
            <div className="text-center max-w-2xl mx-auto py-6">
              <h1 className="text-3xl font-extrabold tracking-tight bg-gradient-to-r from-white via-slate-100 to-slate-400 bg-clip-text text-transparent">
                Local-First Generative Data Analyst
              </h1>
              <p className="text-sm text-slate-400 mt-2">
                Deterministic dataset profiling, allowlisted analytical operations, cross-engine validation with DuckDB, envelope-encrypted MySQL metadata storage, and recipe reuse.
              </p>
            </div>

            {/* Offline notice if service isn't reachable */}
            {health.status !== 'ok' && health.status !== 'checking' && (
              <div className="bg-rose-950/30 border border-rose-800/60 rounded-xl p-4 text-xs text-rose-300 flex items-start space-x-3">
                <AlertCircle className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
                <div className="space-y-1">
                  <strong className="block text-rose-200">Local Python Service Not Detected</strong>
                  <p>
                    GenDA requires the local FastAPI service on loopback. Start it in your terminal with:
                  </p>
                  <pre className="bg-black/50 p-2 rounded border border-rose-900/50 font-mono text-[11px] text-slate-200 inline-block">
                    backend\.venv\Scripts\python.exe -m genda
                  </pre>
                  <p className="text-[11px] text-slate-400">
                    Once started, copy the launch token into the{' '}
                    <button onClick={() => setTokenModalOpen(true)} className="text-cyan-400 underline font-medium">
                      Token settings
                    </button>.
                  </p>
                </div>
              </div>
            )}

            <FileSelector
              onFileSelected={handleFileSelected}
              onLoadSample={handleLoadSample}
              isLoading={isLoading}
            />
          </div>
        ) : (
          /* View 2: Dataset loaded — Workspace with Tabs */
          <div className="space-y-6">
            {/* Active Session Info Strip */}
            <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3 backdrop-blur-sm">
              <div className="flex items-center space-x-3">
                <div className="p-2.5 rounded-xl bg-gradient-to-tr from-cyan-600 to-indigo-600 text-white shadow-md">
                  <HardDrive className="w-5 h-5" />
                </div>
                <div>
                  <div className="flex items-center space-x-2">
                    <h2 className="text-base font-bold text-slate-100">{preview.filename}</h2>
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-300 border border-emerald-500/30">
                      In-Memory Session
                    </span>
                  </div>
                  <p className="text-xs text-slate-400 mt-0.5">
                    {preview.row_count.toLocaleString()} rows &bull; {preview.col_count} columns &bull;{' '}
                    {formatBytes(preview.size_bytes)} &bull; {preview.encoding.toUpperCase()}
                  </p>
                </div>
              </div>

              <div className="flex items-center space-x-2">
                <button
                  onClick={() => setActiveTab('analyze')}
                  className="px-3.5 py-1.5 rounded-lg text-xs font-semibold bg-cyan-600 hover:bg-cyan-500 text-white shadow-sm shadow-cyan-600/30 flex items-center space-x-1.5"
                >
                  <Play className="w-3.5 h-3.5 fill-current" />
                  <span>New Analysis</span>
                </button>
                <button
                  onClick={handleClearSession}
                  className="px-3 py-1.5 rounded-lg text-xs font-medium bg-slate-800 hover:bg-rose-950/60 hover:text-rose-300 text-slate-300 border border-slate-700 hover:border-rose-800 transition-colors flex items-center space-x-1"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                  <span>Release Data</span>
                </button>
              </div>
            </div>

            {/* Feature 1: Consent-based Metadata Persistence Bar */}
            <MetadataPersistenceBar
              sessionId={preview.session_id}
              defaultName={preview.filename}
              hasWorkspace={!!workspaceStatus}
              onOpenWorkspaceModal={() => setWorkspaceModalOpen(true)}
              onLog={addLog}
            />

            {/* Navigation Tabs */}
            <div className="border-b border-slate-800 flex space-x-6 text-xs font-medium">
              <button
                onClick={() => setActiveTab('profile')}
                className={`pb-3 flex items-center space-x-2 border-b-2 transition-colors ${
                  activeTab === 'profile'
                    ? 'border-cyan-400 text-cyan-300 font-semibold'
                    : 'border-transparent text-slate-400 hover:text-slate-200'
                }`}
              >
                <BarChart3 className="w-4 h-4" />
                <span>Dataset Profiling</span>
              </button>

              <button
                onClick={() => setActiveTab('analyze')}
                className={`pb-3 flex items-center space-x-2 border-b-2 transition-colors ${
                  activeTab === 'analyze'
                    ? 'border-cyan-400 text-cyan-300 font-semibold'
                    : 'border-transparent text-slate-400 hover:text-slate-200'
                }`}
              >
                <Calculator className="w-4 h-4" />
                <span>Analysis Operations</span>
              </button>

              <button
                onClick={() => setActiveTab('results')}
                className={`pb-3 flex items-center space-x-2 border-b-2 transition-colors ${
                  activeTab === 'results'
                    ? 'border-cyan-400 text-cyan-300 font-semibold'
                    : 'border-transparent text-slate-400 hover:text-slate-200'
                }`}
              >
                <Sparkles className="w-4 h-4" />
                <span>Computed Results ({results.length})</span>
              </button>

              <button
                onClick={() => setActiveTab('preview')}
                className={`pb-3 flex items-center space-x-2 border-b-2 transition-colors ${
                  activeTab === 'preview'
                    ? 'border-cyan-400 text-cyan-300 font-semibold'
                    : 'border-transparent text-slate-400 hover:text-slate-200'
                }`}
              >
                <Table className="w-4 h-4" />
                <span>Raw Preview</span>
              </button>
            </div>

            {/* Tab 1: Profiling Dashboard */}
            {activeTab === 'profile' && profile && (
              <ProfileDashboard
                profile={profile}
                onSelectColumnForAnalysis={handleSelectColForAnalysis}
              />
            )}

            {/* Tab 2: Analysis Operations Builder & Similarity Recommendations */}
            {activeTab === 'analyze' && profile && (
              <div className="space-y-6">
                {/* Feature 1/Phase F5: Similarity recommendations & Recipe adaptation */}
                <SimilarityRecommendationsCard
                  sessionId={preview.session_id}
                  hasWorkspace={!!workspaceStatus}
                  onRecipeResult={(res) => {
                    setResults((prev) => [res, ...prev]);
                    setActiveTab('results');
                  }}
                  onLog={addLog}
                />

                <AnalysisWorkspace
                  profile={profile}
                  onRunAnalysis={handleRunAnalysis}
                  isLoading={isLoading}
                  preselectedColumn={preselectedCol}
                  preselectedOp={preselectedOp}
                />
              </div>
            )}

            {/* Tab 3: Results History */}
            {activeTab === 'results' && (
              <div className="space-y-4">
                {results.length === 0 ? (
                  <div className="bg-slate-900/40 border border-slate-800 rounded-xl p-8 text-center text-slate-400 text-xs space-y-2">
                    <Calculator className="w-8 h-8 text-slate-600 mx-auto" />
                    <p className="font-medium text-slate-300">No analyses run yet in this session.</p>
                    <p>Go to the Analysis Operations tab to execute your first verified query.</p>
                    <button
                      onClick={() => setActiveTab('analyze')}
                      className="mt-2 px-3 py-1.5 rounded-lg bg-cyan-600 text-white font-semibold inline-block"
                    >
                      Open Operations
                    </button>
                  </div>
                ) : (
                  results.map((res, idx) => (
                    <ResultCard
                      key={idx}
                      result={res}
                      hasWorkspace={!!workspaceStatus}
                      onLog={addLog}
                    />
                  ))
                )}
              </div>
            )}

            {/* Tab 4: Raw Preview */}
            {activeTab === 'preview' && <DataPreviewTable preview={preview} />}
          </div>
        )}
      </main>

      {/* Real-time Diagnostics Audit Log */}
      <AuditLog logs={logs} />

      {/* Transport Token Modal */}
      <TokenModal
        isOpen={tokenModalOpen}
        onClose={() => setTokenModalOpen(false)}
        onTokenUpdated={checkHealth}
      />

      {/* Feature 2: Workspace & Key Management Modal */}
      <WorkspaceModal
        isOpen={workspaceModalOpen}
        onClose={() => setWorkspaceModalOpen(false)}
        workspaceStatus={workspaceStatus}
        onWorkspaceUpdated={(status) => setWorkspaceStatus(status)}
        onWorkspacePurged={handleWorkspacePurged}
        onLog={addLog}
      />

      {/* Feature 1: Reuse Library Modal */}
      <ReuseLibraryModal
        isOpen={reuseLibraryOpen}
        onClose={() => setReuseLibraryOpen(false)}
        onLog={addLog}
      />

      {/* HTML Report Modal */}
      {preview && (
        <ReportModal
          isOpen={reportModalOpen}
          onClose={() => setReportModalOpen(false)}
          sessionId={preview.session_id}
          filename={preview.filename}
        />
      )}
    </div>
  );
}

export default App;
