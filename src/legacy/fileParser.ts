import Papa from 'papaparse';
import * as XLSX from 'xlsx';
import { 
  LocalFileItem, 
  ParsedContent, 
  CsvParsedData, 
  XlsxParsedData, 
  JsonParsedData, 
  TxtParsedData 
} from '../types';

/**
 * Reads and parses a local File object in-memory without uploading or persisting anything.
 * Uses native browser FileReader and arrayBuffer APIs.
 */
export async function readLocalFile(item: LocalFileItem): Promise<{
  parsedContent: ParsedContent;
  readDurationMs: number;
  readMemoryBytes: number;
}> {
  const startTime = performance.now();
  const file = item.file;

  switch (item.fileCategory) {
    case 'csv': {
      const text = await readFileAsText(file);
      const parsedCsv = parseCsvText(text);
      const endTime = performance.now();
      const readMemoryBytes = new Blob([JSON.stringify(parsedCsv)]).size + file.size;
      return {
        parsedContent: parsedCsv,
        readDurationMs: Math.round(endTime - startTime),
        readMemoryBytes,
      };
    }

    case 'xlsx': {
      const buffer = await readFileAsArrayBuffer(file);
      const parsedXlsx = parseXlsxBuffer(buffer);
      const endTime = performance.now();
      const readMemoryBytes = new Blob([JSON.stringify(parsedXlsx)]).size + file.size;
      return {
        parsedContent: parsedXlsx,
        readDurationMs: Math.round(endTime - startTime),
        readMemoryBytes,
      };
    }

    case 'json': {
      const text = await readFileAsText(file);
      const parsedJson = parseJsonText(text);
      const endTime = performance.now();
      const readMemoryBytes = new Blob([text]).size + file.size;
      return {
        parsedContent: parsedJson,
        readDurationMs: Math.round(endTime - startTime),
        readMemoryBytes,
      };
    }

    case 'txt':
    default: {
      const text = await readFileAsText(file);
      const parsedTxt = parseTxtContent(text);
      const endTime = performance.now();
      const readMemoryBytes = new Blob([text]).size + file.size;
      return {
        parsedContent: parsedTxt,
        readDurationMs: Math.round(endTime - startTime),
        readMemoryBytes,
      };
    }
  }
}

/**
 * Native FileReader API: readAsText
 */
function readFileAsText(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result as string || '');
    reader.onerror = () => reject(new Error('Failed to read file as text'));
    reader.readAsText(file);
  });
}

/**
 * Native FileReader / File API: readAsArrayBuffer / arrayBuffer()
 */
async function readFileAsArrayBuffer(file: File): Promise<ArrayBuffer> {
  if (typeof file.arrayBuffer === 'function') {
    return await file.arrayBuffer();
  }
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result as ArrayBuffer);
    reader.onerror = () => reject(new Error('Failed to read file as ArrayBuffer'));
    reader.readAsArrayBuffer(file);
  });
}

function parseCsvText(text: string): CsvParsedData {
  const result = Papa.parse<Record<string, any>>(text, {
    header: true,
    dynamicTyping: true,
    skipEmptyLines: true,
  });

  const headers = result.meta.fields || [];
  const rows = result.data || [];
  const snippet = text.slice(0, 1000);

  return {
    type: 'csv',
    headers,
    rows,
    rowCount: rows.length,
    colCount: headers.length,
    rawSnippet: snippet,
  };
}

function parseXlsxBuffer(buffer: ArrayBuffer): XlsxParsedData {
  const workbook = XLSX.read(buffer, { type: 'array' });
  const sheetNames = workbook.SheetNames || [];
  const sheets: Record<string, { headers: string[]; rows: Record<string, any>[]; rowCount: number; colCount: number }> = {};

  sheetNames.forEach((name) => {
    const worksheet = workbook.Sheets[name];
    if (worksheet) {
      const json: Record<string, any>[] = XLSX.utils.sheet_to_json(worksheet, { defval: '' });
      let headers: string[] = [];
      if (json.length > 0) {
        headers = Object.keys(json[0]);
      } else {
        // Fallback: extract range headers if available
        const range = XLSX.utils.decode_range(worksheet['!ref'] || 'A1');
        for (let C = range.s.c; C <= range.e.c; ++C) {
          const cell = worksheet[XLSX.utils.encode_cell({ r: range.s.r, c: C })];
          if (cell && cell.v) headers.push(String(cell.v));
        }
      }

      sheets[name] = {
        headers,
        rows: json,
        rowCount: json.length,
        colCount: headers.length,
      };
    }
  });

  const activeSheet = sheetNames[0] || '';

  return {
    type: 'xlsx',
    sheetNames,
    activeSheet,
    sheets,
    totalSheets: sheetNames.length,
  };
}

function parseJsonText(text: string): JsonParsedData {
  try {
    const data = JSON.parse(text);
    const isArray = Array.isArray(data);
    let keys: string[] = [];
    let itemCount = 0;

    if (isArray) {
      itemCount = data.length;
      if (data.length > 0 && typeof data[0] === 'object' && data[0] !== null) {
        keys = Object.keys(data[0]);
      }
    } else if (typeof data === 'object' && data !== null) {
      keys = Object.keys(data);
      itemCount = keys.length;
    }

    return {
      type: 'json',
      data,
      isArray,
      itemCount,
      keys,
      rawFormatted: JSON.stringify(data, null, 2),
    };
  } catch (err: any) {
    return {
      type: 'json',
      data: { error: 'Invalid JSON format', details: err.message },
      isArray: false,
      itemCount: 0,
      keys: [],
      rawFormatted: text,
    };
  }
}

function parseTxtContent(text: string): TxtParsedData {
  const lines = text.split(/\r\n|\r|\n/);
  const words = text.trim().split(/\s+/).filter(Boolean);

  return {
    type: 'txt',
    text,
    lineCount: lines.length,
    charCount: text.length,
    wordCount: words.length,
  };
}
