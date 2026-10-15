import { useState, useEffect } from 'react';
import { Play, Calculator } from 'lucide-react';
import {
  DatasetProfile,
  OperationType,
  AnalysisRequest,
} from '../types';

interface AnalysisWorkspaceProps {
  profile: DatasetProfile;
  onRunAnalysis: (request: AnalysisRequest) => void;
  isLoading: boolean;
  preselectedColumn?: string | null;
  preselectedOp?: string | null;
}

export function AnalysisWorkspace({
  profile,
  onRunAnalysis,
  isLoading,
  preselectedColumn,
  preselectedOp,
}: AnalysisWorkspaceProps) {
  const [operation, setOperation] = useState<OperationType>('group_agg');

  // Form states
  const [groupCol, setGroupCol] = useState<string>('');
  const [metricCol, setMetricCol] = useState<string>('');
  const [aggFunc, setAggFunc] = useState<'sum' | 'mean' | 'count' | 'min' | 'max'>('sum');
  const [numericCol, setNumericCol] = useState<string>('');
  const [filterCol, setFilterCol] = useState<string>('');
  const [filterOp, setFilterOp] = useState<'==' | '!=' | '>' | '>=' | '<' | '<=' | 'contains'>('==');
  const [filterVal, setFilterVal] = useState<string>('');
  const [rankCatCol, setRankCatCol] = useState<string>('');
  const [rankMetricCol, setRankMetricCol] = useState<string>('');
  const [rankTopN, setRankTopN] = useState<number>(10);
  const [dateCol, setDateCol] = useState<string>('');
  const [range1Start, setRange1Start] = useState<string>('2025-01-01');
  const [range1End, setRange1End] = useState<string>('2025-01-31');
  const [range2Start, setRange2Start] = useState<string>('2025-02-01');
  const [range2End, setRange2End] = useState<string>('2025-02-28');

  // Categorize columns
  const numericColumns = profile.columns.filter((c) => c.inferred_type === 'numeric');
  const categoricalColumns = profile.columns.filter((c) => c.inferred_type === 'categorical' || c.inferred_type === 'text');
  const dateColumns = profile.columns.filter((c) => c.inferred_type === 'datetime');
  const allColumns = profile.columns;

  // Initialize sensible defaults
  useEffect(() => {
    if (categoricalColumns.length > 0 && !groupCol) {
      setGroupCol(categoricalColumns[0].name);
      setRankCatCol(categoricalColumns[0].name);
    }
    if (numericColumns.length > 0 && !metricCol) {
      setMetricCol(numericColumns[0].name);
      setNumericCol(numericColumns[0].name);
      setRankMetricCol(numericColumns[0].name);
    }
    if (allColumns.length > 0 && !filterCol) {
      setFilterCol(allColumns[0].name);
    }
    if (dateColumns.length > 0 && !dateCol) {
      setDateCol(dateColumns[0].name);
    }
  }, [profile]);

  // Handle external preselection
  useEffect(() => {
    if (preselectedColumn && preselectedOp) {
      setOperation(preselectedOp as OperationType);
      if (preselectedOp === 'numeric_summary') {
        setNumericCol(preselectedColumn);
      } else if (preselectedOp === 'group_agg') {
        setGroupCol(preselectedColumn);
      } else if (preselectedOp === 'category_rank') {
        setRankCatCol(preselectedColumn);
      }
    }
  }, [preselectedColumn, preselectedOp]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (isLoading) return;

    if (operation === 'group_agg') {
      if (!groupCol || !metricCol) return;
      onRunAnalysis({
        operation: 'group_agg',
        group_by: groupCol,
        metric: metricCol,
        agg: aggFunc,
      });
    } else if (operation === 'numeric_summary') {
      if (!numericCol) return;
      onRunAnalysis({
        operation: 'numeric_summary',
        column: numericCol,
      });
    } else if (operation === 'missing_summary') {
      onRunAnalysis({
        operation: 'missing_summary',
      });
    } else if (operation === 'filter_count') {
      if (!filterCol) return;
      onRunAnalysis({
        operation: 'filter_count',
        column: filterCol,
        operator: filterOp,
        value: filterVal,
      });
    } else if (operation === 'category_rank') {
      if (!rankCatCol || !rankMetricCol) return;
      onRunAnalysis({
        operation: 'category_rank',
        category_column: rankCatCol,
        metric_column: rankMetricCol,
        agg: 'sum',
        top_n: rankTopN,
        ascending: false,
      });
    } else if (operation === 'date_comparison') {
      if (!dateCol || !metricCol) return;
      onRunAnalysis({
        operation: 'date_comparison',
        date_column: dateCol,
        metric_column: metricCol,
        range_1_start: range1Start,
        range_1_end: range1End,
        range_2_start: range2Start,
        range_2_end: range2End,
        agg: aggFunc === 'count' ? 'count' : 'sum',
      });
    }
  };

  return (
    <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 backdrop-blur-sm space-y-5">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2.5">
          <div className="p-2 rounded-lg bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
            <Calculator className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-slate-100">
              Deterministic Analytical Operations
            </h3>
            <p className="text-xs text-slate-400">
              Validated calculations with cross-engine Polars + DuckDB verification & Plotly visual specs
            </p>
          </div>
        </div>
      </div>

      {/* Operation Tabs */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2">
        <button
          type="button"
          onClick={() => setOperation('group_agg')}
          className={`px-3 py-2 rounded-lg text-xs font-medium border text-left transition-all ${
            operation === 'group_agg'
              ? 'bg-cyan-500/10 border-cyan-500/40 text-cyan-300 shadow-sm shadow-cyan-500/10'
              : 'bg-slate-950/40 border-slate-800 text-slate-400 hover:text-slate-200 hover:bg-slate-900'
          }`}
        >
          <div className="font-semibold">Group & Aggregate</div>
          <div className="text-[10px] text-slate-500 mt-0.5">Sum / Mean / Count</div>
        </button>

        <button
          type="button"
          onClick={() => setOperation('numeric_summary')}
          className={`px-3 py-2 rounded-lg text-xs font-medium border text-left transition-all ${
            operation === 'numeric_summary'
              ? 'bg-cyan-500/10 border-cyan-500/40 text-cyan-300 shadow-sm shadow-cyan-500/10'
              : 'bg-slate-950/40 border-slate-800 text-slate-400 hover:text-slate-200 hover:bg-slate-900'
          }`}
        >
          <div className="font-semibold">Numeric Summary</div>
          <div className="text-[10px] text-slate-500 mt-0.5">Distribution & Boxplot</div>
        </button>

        <button
          type="button"
          onClick={() => setOperation('category_rank')}
          className={`px-3 py-2 rounded-lg text-xs font-medium border text-left transition-all ${
            operation === 'category_rank'
              ? 'bg-cyan-500/10 border-cyan-500/40 text-cyan-300 shadow-sm shadow-cyan-500/10'
              : 'bg-slate-950/40 border-slate-800 text-slate-400 hover:text-slate-200 hover:bg-slate-900'
          }`}
        >
          <div className="font-semibold">Category Rank</div>
          <div className="text-[10px] text-slate-500 mt-0.5">Top N Categories</div>
        </button>

        <button
          type="button"
          onClick={() => setOperation('missing_summary')}
          className={`px-3 py-2 rounded-lg text-xs font-medium border text-left transition-all ${
            operation === 'missing_summary'
              ? 'bg-cyan-500/10 border-cyan-500/40 text-cyan-300 shadow-sm shadow-cyan-500/10'
              : 'bg-slate-950/40 border-slate-800 text-slate-400 hover:text-slate-200 hover:bg-slate-900'
          }`}
        >
          <div className="font-semibold">Missing Values</div>
          <div className="text-[10px] text-slate-500 mt-0.5">Null Audit Survey</div>
        </button>

        <button
          type="button"
          onClick={() => setOperation('filter_count')}
          className={`px-3 py-2 rounded-lg text-xs font-medium border text-left transition-all ${
            operation === 'filter_count'
              ? 'bg-cyan-500/10 border-cyan-500/40 text-cyan-300 shadow-sm shadow-cyan-500/10'
              : 'bg-slate-950/40 border-slate-800 text-slate-400 hover:text-slate-200 hover:bg-slate-900'
          }`}
        >
          <div className="font-semibold">Filter & Count</div>
          <div className="text-[10px] text-slate-500 mt-0.5">Condition Matching</div>
        </button>

        <button
          type="button"
          onClick={() => setOperation('date_comparison')}
          className={`px-3 py-2 rounded-lg text-xs font-medium border text-left transition-all ${
            operation === 'date_comparison'
              ? 'bg-cyan-500/10 border-cyan-500/40 text-cyan-300 shadow-sm shadow-cyan-500/10'
              : 'bg-slate-950/40 border-slate-800 text-slate-400 hover:text-slate-200 hover:bg-slate-900'
          }`}
        >
          <div className="font-semibold">Date Comparison</div>
          <div className="text-[10px] text-slate-500 mt-0.5">Two Period Delta</div>
        </button>
      </div>

      {/* Operation Form */}
      <form onSubmit={handleSubmit} className="bg-slate-950/50 p-4 rounded-xl border border-slate-800/80 space-y-4">
        {operation === 'group_agg' && (
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div>
              <label className="text-[11px] font-medium text-slate-400 uppercase block mb-1">
                Group By (Categorical)
              </label>
              <select
                value={groupCol}
                onChange={(e) => setGroupCol(e.target.value)}
                className="w-full text-xs bg-slate-900 border border-slate-800 rounded-lg p-2 text-slate-200 focus:outline-none focus:border-cyan-500"
              >
                {allColumns.map((c) => (
                  <option key={c.name} value={c.name}>
                    {c.name} ({c.inferred_type})
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="text-[11px] font-medium text-slate-400 uppercase block mb-1">
                Metric Column
              </label>
              <select
                value={metricCol}
                onChange={(e) => setMetricCol(e.target.value)}
                className="w-full text-xs bg-slate-900 border border-slate-800 rounded-lg p-2 text-slate-200 focus:outline-none focus:border-cyan-500"
              >
                {numericColumns.length > 0 ? (
                  numericColumns.map((c) => (
                    <option key={c.name} value={c.name}>
                      {c.name}
                    </option>
                  ))
                ) : (
                  allColumns.map((c) => (
                    <option key={c.name} value={c.name}>
                      {c.name}
                    </option>
                  ))
                )}
              </select>
            </div>

            <div>
              <label className="text-[11px] font-medium text-slate-400 uppercase block mb-1">
                Aggregation Function
              </label>
              <select
                value={aggFunc}
                onChange={(e) => setAggFunc(e.target.value as any)}
                className="w-full text-xs bg-slate-900 border border-slate-800 rounded-lg p-2 text-slate-200 focus:outline-none focus:border-cyan-500"
              >
                <option value="sum">SUM</option>
                <option value="mean">MEAN / AVERAGE</option>
                <option value="count">COUNT</option>
                <option value="min">MINIMUM</option>
                <option value="max">MAXIMUM</option>
              </select>
            </div>
          </div>
        )}

        {operation === 'numeric_summary' && (
          <div>
            <label className="text-[11px] font-medium text-slate-400 uppercase block mb-1">
              Select Numeric Column
            </label>
            <select
              value={numericCol}
              onChange={(e) => setNumericCol(e.target.value)}
              className="w-full sm:w-1/2 text-xs bg-slate-900 border border-slate-800 rounded-lg p-2 text-slate-200 focus:outline-none focus:border-cyan-500"
            >
              {numericColumns.map((c) => (
                <option key={c.name} value={c.name}>
                  {c.name} (min: {c.min_val}, max: {c.max_val})
                </option>
              ))}
            </select>
            <p className="text-[11px] text-slate-500 mt-1">
              Computes mean, median, standard deviation, quartiles, and renders interactive boxplot.
            </p>
          </div>
        )}

        {operation === 'category_rank' && (
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div>
              <label className="text-[11px] font-medium text-slate-400 uppercase block mb-1">
                Category Column
              </label>
              <select
                value={rankCatCol}
                onChange={(e) => setRankCatCol(e.target.value)}
                className="w-full text-xs bg-slate-900 border border-slate-800 rounded-lg p-2 text-slate-200 focus:outline-none focus:border-cyan-500"
              >
                {allColumns.map((c) => (
                  <option key={c.name} value={c.name}>
                    {c.name}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="text-[11px] font-medium text-slate-400 uppercase block mb-1">
                Metric Column
              </label>
              <select
                value={rankMetricCol}
                onChange={(e) => setRankMetricCol(e.target.value)}
                className="w-full text-xs bg-slate-900 border border-slate-800 rounded-lg p-2 text-slate-200 focus:outline-none focus:border-cyan-500"
              >
                {numericColumns.map((c) => (
                  <option key={c.name} value={c.name}>
                    {c.name}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="text-[11px] font-medium text-slate-400 uppercase block mb-1">
                Top N Categories
              </label>
              <input
                type="number"
                min={1}
                max={50}
                value={rankTopN}
                onChange={(e) => setRankTopN(Number(e.target.value))}
                className="w-full text-xs bg-slate-900 border border-slate-800 rounded-lg p-2 text-slate-200 focus:outline-none focus:border-cyan-500"
              />
            </div>
          </div>
        )}

        {operation === 'missing_summary' && (
          <p className="text-xs text-slate-300">
            Performs an exhaustive audit of null and missing values across all {profile.column_count} columns in this dataset.
          </p>
        )}

        {operation === 'filter_count' && (
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div>
              <label className="text-[11px] font-medium text-slate-400 uppercase block mb-1">
                Column
              </label>
              <select
                value={filterCol}
                onChange={(e) => setFilterCol(e.target.value)}
                className="w-full text-xs bg-slate-900 border border-slate-800 rounded-lg p-2 text-slate-200 focus:outline-none focus:border-cyan-500"
              >
                {allColumns.map((c) => (
                  <option key={c.name} value={c.name}>
                    {c.name}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="text-[11px] font-medium text-slate-400 uppercase block mb-1">
                Operator
              </label>
              <select
                value={filterOp}
                onChange={(e) => setFilterOp(e.target.value as any)}
                className="w-full text-xs bg-slate-900 border border-slate-800 rounded-lg p-2 text-slate-200 focus:outline-none focus:border-cyan-500"
              >
                <option value="==">equals (==)</option>
                <option value="!=">not equals (!=)</option>
                <option value=">">greater than (&gt;)</option>
                <option value=">=">greater than or equal (&gt;=)</option>
                <option value="<">less than (&lt;)</option>
                <option value="<=">less than or equal (&lt;=)</option>
                <option value="contains">contains text</option>
              </select>
            </div>

            <div>
              <label className="text-[11px] font-medium text-slate-400 uppercase block mb-1">
                Target Value
              </label>
              <input
                type="text"
                required
                value={filterVal}
                onChange={(e) => setFilterVal(e.target.value)}
                placeholder="Value..."
                className="w-full text-xs bg-slate-900 border border-slate-800 rounded-lg p-2 text-slate-200 focus:outline-none focus:border-cyan-500"
              />
            </div>
          </div>
        )}

        {operation === 'date_comparison' && (
          <div className="space-y-3">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="text-[11px] font-medium text-slate-400 uppercase block mb-1">
                  Date Column
                </label>
                <select
                  value={dateCol}
                  onChange={(e) => setDateCol(e.target.value)}
                  className="w-full text-xs bg-slate-900 border border-slate-800 rounded-lg p-2 text-slate-200 focus:outline-none focus:border-cyan-500"
                >
                  {allColumns.map((c) => (
                    <option key={c.name} value={c.name}>
                      {c.name}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="text-[11px] font-medium text-slate-400 uppercase block mb-1">
                  Metric Column
                </label>
                <select
                  value={metricCol}
                  onChange={(e) => setMetricCol(e.target.value)}
                  className="w-full text-xs bg-slate-900 border border-slate-800 rounded-lg p-2 text-slate-200 focus:outline-none focus:border-cyan-500"
                >
                  {numericColumns.map((c) => (
                    <option key={c.name} value={c.name}>
                      {c.name}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
              <div>
                <span className="text-[10px] text-slate-500 block mb-0.5">Period 1 Start</span>
                <input
                  type="date"
                  value={range1Start}
                  onChange={(e) => setRange1Start(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-800 rounded p-1.5 text-slate-200"
                />
              </div>
              <div>
                <span className="text-[10px] text-slate-500 block mb-0.5">Period 1 End</span>
                <input
                  type="date"
                  value={range1End}
                  onChange={(e) => setRange1End(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-800 rounded p-1.5 text-slate-200"
                />
              </div>
              <div>
                <span className="text-[10px] text-slate-500 block mb-0.5">Period 2 Start</span>
                <input
                  type="date"
                  value={range2Start}
                  onChange={(e) => setRange2Start(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-800 rounded p-1.5 text-slate-200"
                />
              </div>
              <div>
                <span className="text-[10px] text-slate-500 block mb-0.5">Period 2 End</span>
                <input
                  type="date"
                  value={range2End}
                  onChange={(e) => setRange2End(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-800 rounded p-1.5 text-slate-200"
                />
              </div>
            </div>
          </div>
        )}

        <div className="pt-2 flex justify-end">
          <button
            type="submit"
            disabled={isLoading}
            className="flex items-center space-x-2 px-5 py-2 rounded-xl text-xs font-semibold bg-gradient-to-r from-cyan-600 to-indigo-600 hover:from-cyan-500 hover:to-indigo-500 text-white shadow-md shadow-cyan-600/20 disabled:opacity-50 transition-all cursor-pointer"
          >
            {isLoading ? (
              <>
                <div className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                <span>Computing in Polars & DuckDB...</span>
              </>
            ) : (
              <>
                <Play className="w-3.5 h-3.5 fill-current" />
                <span>Run Analysis</span>
              </>
            )}
          </button>
        </div>
      </form>
    </div>
  );
}
