// ---------------------------------------------------------------------------
// GenDA v2.0 Loopback Types
// ---------------------------------------------------------------------------

export type InferredColumnType = 'numeric' | 'categorical' | 'datetime' | 'boolean' | 'text' | 'unknown';

export interface CategoricalFrequency {
  value: string;
  count: number;
  percentage: number;
}

export interface ColumnProfile {
  name: string;
  inferred_type: InferredColumnType;
  polars_type: string;
  total_count: number;
  null_count: number;
  null_percentage: number;
  distinct_count: number;
  is_unique: boolean;
  min_val?: number | string | null;
  max_val?: number | string | null;
  mean?: number | null;
  median?: number | null;
  std?: number | null;
  q25?: number | null;
  q75?: number | null;
  top_frequencies: CategoricalFrequency[];
  warnings: string[];
}

export interface DatasetProfile {
  row_count: number;
  column_count: number;
  columns: ColumnProfile[];
  duplicate_rows: number;
  memory_bytes: number;
  dataset_warnings: string[];
}

export interface DataPreview {
  session_id: string;
  filename: string;
  size_bytes: number;
  headers: string[];
  row_count: number;
  col_count: number;
  preview_rows: Record<string, any>[];
  column_types: Record<string, string>;
  encoding: string;
}

export type OperationType =
  | 'group_agg'
  | 'numeric_summary'
  | 'missing_summary'
  | 'filter_count'
  | 'category_rank'
  | 'date_comparison';

export interface GroupAggRequest {
  operation: 'group_agg' | 'group_sum';
  group_by: string;
  metric: string;
  agg: 'sum' | 'mean' | 'count' | 'min' | 'max';
}

export interface NumericSummaryRequest {
  operation: 'numeric_summary';
  column: string;
}

export interface MissingSummaryRequest {
  operation: 'missing_summary';
}

export interface FilterCountRequest {
  operation: 'filter_count';
  column: string;
  operator: '==' | '!=' | '>' | '>=' | '<' | '<=' | 'contains';
  value: any;
}

export interface CategoryRankRequest {
  operation: 'category_rank';
  category_column: string;
  metric_column: string;
  agg: 'sum' | 'mean' | 'count';
  top_n: number;
  ascending: boolean;
}

export interface DateComparisonRequest {
  operation: 'date_comparison';
  date_column: string;
  metric_column: string;
  range_1_start: string;
  range_1_end: string;
  range_2_start: string;
  range_2_end: string;
  agg: 'sum' | 'mean' | 'count';
}

export type AnalysisRequest =
  | GroupAggRequest
  | NumericSummaryRequest
  | MissingSummaryRequest
  | FilterCountRequest
  | CategoryRankRequest
  | DateComparisonRequest;

export interface AnalysisResult {
  title: string;
  operation: string;
  inputs: Record<string, any>;
  result: any;
  chart_spec?: any | null;
  warnings: string[];
  validation_status: 'passed' | 'warning' | 'failed';
  execution_time_ms: number;
  cross_engine_match?: boolean | null;
  engine_details: string;
  evidence_summary: string;
  limitations: string[];
}

export interface ServiceHealth {
  status: 'ok' | 'unreachable' | 'checking' | 'unauthorized';
  service?: string;
  version?: string;
  loopback_only?: boolean;
  session_count?: number;
  error?: string;
}

export interface LogEntry {
  id: string;
  timestamp: string;
  action: string;
  type: 'info' | 'success' | 'warn' | 'error';
}

// ---------------------------------------------------------------------------
// Backward-compatible v1 types
// ---------------------------------------------------------------------------

export type SupportedFileType = 'csv' | 'xlsx' | 'json' | 'txt' | 'unknown';
export type FileStatus = 'selected' | 'reading' | 'ready' | 'error' | 'cleared';
export type LifecycleStage = 'select' | 'access' | 'preview' | 'clear' | 'released';

export interface CsvParsedData {
  type: 'csv';
  headers: string[];
  rows: Record<string, any>[];
  rowCount: number;
  colCount: number;
  rawSnippet: string;
}

export interface XlsxSheetData {
  headers: string[];
  rows: Record<string, any>[];
  rowCount: number;
  colCount: number;
}

export interface XlsxParsedData {
  type: 'xlsx';
  sheetNames: string[];
  activeSheet: string;
  sheets: Record<string, XlsxSheetData>;
  totalSheets: number;
}

export interface JsonParsedData {
  type: 'json';
  data: any;
  isArray: boolean;
  itemCount: number;
  keys: string[];
  rawFormatted: string;
}

export interface TxtParsedData {
  type: 'txt';
  text: string;
  lineCount: number;
  charCount: number;
  wordCount: number;
}

export type ParsedContent = CsvParsedData | XlsxParsedData | JsonParsedData | TxtParsedData;

export interface LocalFileItem {
  id: string;
  file: File;
  name: string;
  type: string;
  extension: string;
  fileCategory: SupportedFileType;
  size: number;
  lastModified: number;
  relativePath: string;
  status: FileStatus;
  errorMessage?: string;
  parsedContent?: ParsedContent;
  readDurationMs?: number;
  readMemoryBytes?: number;
  readTimestamp?: number;
}
