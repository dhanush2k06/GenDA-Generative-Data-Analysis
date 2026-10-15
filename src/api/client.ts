import {
  ServiceHealth,
  DataPreview,
  DatasetProfile,
  AnalysisRequest,
  AnalysisResult,
} from '../types';

export class GenDAApiClient {
  private baseUrl: string;
  private token: string;

  constructor(baseUrl: string = '', token: string = '') {
    // If empty baseUrl, relative paths go through Vite's /api proxy to 127.0.0.1:8000
    this.baseUrl = baseUrl;
    this.token = token || localStorage.getItem('genda_token') || '';
  }

  setToken(token: string) {
    this.token = token;
    localStorage.setItem('genda_token', token);
  }

  getToken(): string {
    return this.token;
  }

  private getHeaders(contentType: string | null = 'application/json'): Record<string, string> {
    const headers: Record<string, string> = {};
    if (contentType) {
      headers['Content-Type'] = contentType;
    }
    if (this.token) {
      headers['X-GenDA-Token'] = this.token;
    }
    return headers;
  }

  async checkHealth(): Promise<ServiceHealth> {
    try {
      const res = await fetch(`${this.baseUrl}/api/health`, {
        headers: this.getHeaders(null),
      });
      if (!res.ok) {
        return { status: 'unreachable', error: `HTTP ${res.status}: ${res.statusText}` };
      }
      const data = await res.json();
      return {
        status: 'ok',
        service: data.service,
        version: data.version,
        loopback_only: data.loopback_only,
        session_count: data.session_count,
      };
    } catch (err: any) {
      return { status: 'unreachable', error: err.message || 'Cannot connect to local Python service.' };
    }
  }

  async verifyAuth(): Promise<boolean> {
    try {
      const res = await fetch(`${this.baseUrl}/api/auth/verify`, {
        headers: this.getHeaders(null),
      });
      return res.ok;
    } catch {
      return false;
    }
  }

  async uploadCsv(file: File): Promise<DataPreview> {
    const formData = new FormData();
    formData.append('file', file);

    const headers: Record<string, string> = {};
    if (this.token) {
      headers['X-GenDA-Token'] = this.token;
    }

    const res = await fetch(`${this.baseUrl}/api/session/upload`, {
      method: 'POST',
      headers,
      body: formData,
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Upload failed' }));
      throw new Error(err.detail || `Upload failed with HTTP ${res.status}`);
    }

    return res.json();
  }

  async getProfile(sessionId: string): Promise<DatasetProfile> {
    const res = await fetch(`${this.baseUrl}/api/session/${sessionId}/profile`, {
      method: 'POST',
      headers: this.getHeaders(),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Profiling failed' }));
      throw new Error(err.detail || `Profiling failed with HTTP ${res.status}`);
    }

    return res.json();
  }

  async runAnalysis(sessionId: string, request: AnalysisRequest): Promise<AnalysisResult> {
    const res = await fetch(`${this.baseUrl}/api/session/${sessionId}/analyze`, {
      method: 'POST',
      headers: this.getHeaders(),
      body: JSON.stringify(request),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Analysis failed' }));
      throw new Error(err.detail || `Analysis failed with HTTP ${res.status}`);
    }

    return res.json();
  }

  async clearSession(sessionId: string): Promise<void> {
    const res = await fetch(`${this.baseUrl}/api/session/${sessionId}`, {
      method: 'DELETE',
      headers: this.getHeaders(null),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Clear session failed' }));
      throw new Error(err.detail || `Clear session failed with HTTP ${res.status}`);
    }
  }

  getReportHtmlUrl(sessionId: string): string {
    return `${this.baseUrl}/api/session/${sessionId}/report/html?token=${encodeURIComponent(this.token)}`;
  }

  async downloadReport(sessionId: string, filename: string): Promise<void> {
    const res = await fetch(`${this.baseUrl}/api/session/${sessionId}/report/download`, {
      headers: this.getHeaders(null),
    });

    if (!res.ok) {
      throw new Error('Failed to download report');
    }

    const blob = await res.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `genda_report_${filename.replace(/\.[^/.]+$/, '')}.html`;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
  }
}

export const apiClient = new GenDAApiClient();
