import { useState, useEffect } from 'react';
import {
  Sparkles,
  Play,
  RefreshCw,
} from 'lucide-react';
import { RecipeRecommendationResponse, Recipe, AnalysisResult } from '../types';
import { apiClient } from '../api/client';


interface SimilarityRecommendationsCardProps {
  sessionId: string;
  hasWorkspace: boolean;
  onRecipeResult: (result: AnalysisResult) => void;
  onLog: (msg: string, type?: 'info' | 'success' | 'warn' | 'error') => void;
}

export function SimilarityRecommendationsCard({
  sessionId,
  hasWorkspace,
  onRecipeResult,
  onLog,
}: SimilarityRecommendationsCardProps) {
  const [data, setData] = useState<RecipeRecommendationResponse | null>(null);
  const [selectedRecipe, setSelectedRecipe] = useState<Recipe | null>(null);
  const [columnMapping, setColumnMapping] = useState<Record<string, string>>({});
  const [isLoading, setIsLoading] = useState(false);
  const [isExecuting, setIsExecuting] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  useEffect(() => {
    if (hasWorkspace && sessionId) {
      loadRecommendations();
    }
  }, [hasWorkspace, sessionId]);

  const loadRecommendations = async () => {
    setIsLoading(true);
    setStatusMessage(null);
    try {
      const recs = await apiClient.getRecipeRecommendations(sessionId);
      setData(recs);
      if (recs.available_recipes.length > 0) {
        initRecipeMapping(recs.available_recipes[0], recs);
      }
    } catch (err: any) {
      // Quietly ignore if no workspace key
    } finally {
      setIsLoading(false);
    }
  };

  const initRecipeMapping = (recipe: Recipe, recsData: RecipeRecommendationResponse) => {
    setSelectedRecipe(recipe);
    const mapping: Record<string, string> = {};
    const roles = recipe.spec?.roles || {};

    // Auto-map if matched columns exist
    const bestMatch = recsData.matches[0];
    const availableCols = recsData.source_columns || [];

    for (const [roleName, roleDef] of Object.entries(roles)) {
      if (typeof roleDef === 'object' && roleDef !== null) {
        // If best match has an exact or matched column
        const mapped = bestMatch?.matched_columns?.[roleName] || availableCols[0] || '';
        mapping[roleName] = mapped;
      }
    }
    setColumnMapping(mapping);
  };

  const handleApplyRecipe = async () => {
    if (!selectedRecipe) return;
    setIsExecuting(true);
    setStatusMessage(null);
    try {
      const res = await apiClient.applyRecipe(sessionId, selectedRecipe.id, columnMapping);
      onRecipeResult(res.result);
      onLog(`Executed reused recipe "${selectedRecipe.name}" successfully.`, 'success');
      setStatusMessage('Recipe successfully executed and verified against data!');
    } catch (err: any) {
      setStatusMessage(`Error: ${err.message}`);
      onLog(`Failed to apply recipe: ${err.message}`, 'error');
    } finally {
      setIsExecuting(false);
    }
  };

  if (!hasWorkspace || !data || (data.matches.length === 0 && data.available_recipes.length === 0)) {
    return null;
  }

  return (
    <div className="bg-gradient-to-br from-slate-900 to-indigo-950/30 border border-indigo-900/50 rounded-2xl p-5 shadow-xl space-y-4 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between pb-3 border-b border-indigo-950">
        <div className="flex items-center space-x-2.5">
          <div className="p-2 rounded-xl bg-indigo-500/20 text-indigo-400 border border-indigo-500/30">
            <Sparkles className="w-5 h-5 text-indigo-300" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-white flex items-center space-x-2">
              <span>Smart Recipe Reuse & Similarity Engine</span>
              <span className="text-[10px] px-2 py-0.5 rounded-full bg-cyan-500/10 text-cyan-400 border border-cyan-500/30 font-mono">
                Heuristic Calibrated
              </span>
            </h3>
            <p className="text-xs text-slate-400">
              Found {data.matches.length} similar dataset schema(s) and {data.available_recipes.length} reusable technique(s) in this workspace.
            </p>
          </div>
        </div>

        <button
          onClick={loadRecommendations}
          disabled={isLoading}
          className="p-1.5 text-slate-400 hover:text-slate-200 hover:bg-slate-800 rounded-lg transition-colors"
          title="Refresh Recommendations"
        >
          <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {/* Similarity Matches List */}
      {data.matches.length > 0 && (
        <div className="space-y-2">
          <div className="text-xs font-semibold text-slate-300">Top Similarity Match:</div>
          {data.matches.slice(0, 1).map((m) => (
            <div key={m.target_dataset_id} className="p-3 rounded-xl bg-slate-950/60 border border-slate-800 space-y-1.5">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-indigo-300">{m.target_name}</span>
                <span className="text-xs font-mono font-bold px-2 py-0.5 rounded bg-indigo-950 text-indigo-300 border border-indigo-800">
                  {Math.round(m.composite_score * 100)}% Similarity
                </span>
              </div>
              <p className="text-[11px] text-slate-400 leading-relaxed">{m.explanation}</p>
            </div>
          ))}
        </div>
      )}

      {/* Recipe Selection & Column Mapping */}
      {data.available_recipes.length > 0 && selectedRecipe && (
        <div className="space-y-3 pt-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-300">Select Recipe to Apply:</span>
            <select
              value={selectedRecipe.id}
              onChange={(e) => {
                const rec = data.available_recipes.find((r) => r.id === e.target.value);
                if (rec) initRecipeMapping(rec, data);
              }}
              className="px-2.5 py-1 rounded-lg bg-slate-950 border border-slate-700 text-xs text-white font-medium focus:outline-none focus:border-indigo-500"
            >
              {data.available_recipes.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.name} ({r.category})
                </option>
              ))}
            </select>
          </div>

          {/* Column Role Mapping */}
          <div className="p-3 rounded-xl bg-slate-950/80 border border-indigo-900/40 space-y-2.5">
            <div className="text-[11px] font-semibold text-indigo-300 uppercase tracking-wider">
              Verify & Confirm Column Roles (No Auto-Run):
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
              {Object.keys(columnMapping).map((role) => (
                <div key={role} className="flex flex-col space-y-1">
                  <span className="text-[11px] font-mono text-slate-400 capitalize">
                    Role: <strong className="text-white">{role}</strong>
                  </span>
                  <select
                    value={columnMapping[role]}
                    onChange={(e) => setColumnMapping({ ...columnMapping, [role]: e.target.value })}
                    className="px-2 py-1.5 rounded-lg bg-slate-900 border border-slate-700 text-xs text-white focus:outline-none focus:border-indigo-500"
                  >
                    {data.source_columns.map((c) => (
                      <option key={c} value={c}>
                        {c}
                      </option>
                    ))}
                  </select>
                </div>
              ))}
            </div>

            <div className="pt-2 flex items-center justify-between">
              <span className="text-[11px] text-slate-400">
                Operation: <code className="text-cyan-400">{selectedRecipe.spec?.operation}</code>
              </span>
              <button
                onClick={handleApplyRecipe}
                disabled={isExecuting}
                className="flex items-center space-x-1.5 px-4 py-2 rounded-xl text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white shadow-lg shadow-indigo-600/30 transition-all"
              >
                {isExecuting ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Play className="w-3.5 h-3.5" />}
                <span>Confirm & Apply Technique</span>
              </button>
            </div>

            {statusMessage && (
              <div
                className={`p-2 rounded-lg text-xs font-medium ${
                  statusMessage.startsWith('Error')
                    ? 'bg-rose-500/10 text-rose-300 border border-rose-500/20'
                    : 'bg-emerald-500/10 text-emerald-300 border border-emerald-500/20'
                }`}
              >
                {statusMessage}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
