import {
  ServiceHealth,
  DataPreview,
  DatasetProfile,
  AnalysisRequest,
  AnalysisResult,
  WorkspaceKeyInfo,
  WorkspaceStatus,
  StoredDatasetSummary,
  StoredDatasetDetail,
  Recipe,
  RecipeRecommendationResponse,
  PurgeReport,
  AuditEventItem,
} from '../types';

export class GenDAApiClient {
  private baseUrl: string;
  private token: string;
  // Security requirement (Part 3.2): Workspace key in memory only! No localStorage/cookies.
  private workspaceKey: string = '';

  constructor(baseUrl: string = '', token: string = '') {
    // If empty baseUrl, relative paths go through Vite's /api proxy to 127.0.0.1:8000
    this.baseUrl = baseUrl;
    this.token = token || localStorage.getItem('genda_token') || 'dev-token-local-genda-123';
  }

  setToken(token: string) {
    this.token = token;
    localStorage.setItem('genda_token', token);
  }

  getToken(): string {
    return this.token;
  }

  setWorkspaceKey(key: string) {
    this.workspaceKey = key.trim();
  }

  getWorkspaceKey(): string {
    return this.workspaceKey;
  }

  clearWorkspaceKey() {
    this.workspaceKey = '';
  }

  private getHeaders(
    contentType: string | null = 'application/json',
    overrideKey?: string
  ): Record<string, string> {
    const headers: Record<string, string> = {};
    if (contentType) {
      headers['Content-Type'] = contentType;
    }
    if (this.token) {
      headers['X-GenDA-Token'] = this.token;
    }
    const keyToUse = overrideKey !== undefined ? overrideKey : this.workspaceKey;
    if (keyToUse) {
      headers['Authorization'] = `Bearer ${keyToUse}`;
      headers['X-GenDA-Workspace-Key'] = keyToUse;
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

  // -------------------------------------------------------------------------
  // Workspace Lifecycle
  // -------------------------------------------------------------------------

  async createWorkspace(): Promise<WorkspaceKeyInfo> {
    const res = await fetch(`${this.baseUrl}/api/workspace/create`, {
      method: 'POST',
      headers: this.getHeaders(),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Failed to create workspace' }));
      throw new Error(err.detail || `Create workspace failed with HTTP ${res.status}`);
    }
    const data: WorkspaceKeyInfo = await res.json();
    this.setWorkspaceKey(data.workspace_key);
    return data;
  }

  async validateWorkspace(key?: string): Promise<WorkspaceStatus> {
    const res = await fetch(`${this.baseUrl}/api/workspace/validate`, {
      headers: this.getHeaders(null, key),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Invalid or revoked workspace key' }));
      throw new Error(err.detail || `Validation failed with HTTP ${res.status}`);
    }
    return res.json();
  }

  async rotateWorkspaceKey(): Promise<WorkspaceKeyInfo> {
    const res = await fetch(`${this.baseUrl}/api/workspace/rotate`, {
      method: 'POST',
      headers: this.getHeaders(),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Key rotation failed' }));
      throw new Error(err.detail || `Key rotation failed with HTTP ${res.status}`);
    }
    const data: WorkspaceKeyInfo = await res.json();
    this.setWorkspaceKey(data.workspace_key);
    return data;
  }

  async revokeWorkspace(): Promise<{ status: string; message: string; purge_report: PurgeReport }> {
    const res = await fetch(`${this.baseUrl}/api/workspace/revoke`, {
      method: 'POST',
      headers: this.getHeaders(),
    });
    this.clearWorkspaceKey();
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Workspace revocation failed' }));
      throw new Error(err.detail || `Revocation failed with HTTP ${res.status}`);
    }
    return res.json();
  }

  async clearEverything(): Promise<{ status: string; message: string; purge_report: PurgeReport }> {
    const res = await fetch(`${this.baseUrl}/api/workspace/clear-everything`, {
      method: 'POST',
      headers: this.getHeaders(),
    });
    this.clearWorkspaceKey();
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Clear everything failed' }));
      throw new Error(err.detail || `Clear failed with HTTP ${res.status}`);
    }
    return res.json();
  }

  // -------------------------------------------------------------------------
  // Session & Data Ingestion
  // -------------------------------------------------------------------------

  async uploadCsv(file: File): Promise<DataPreview> {
    const formData = new FormData();
    formData.append('file', file);

    const headers: Record<string, string> = {};
    if (this.token) {
      headers['X-GenDA-Token'] = this.token;
    }
    if (this.workspaceKey) {
      headers['Authorization'] = `Bearer ${this.workspaceKey}`;
      headers['X-GenDA-Workspace-Key'] = this.workspaceKey;
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

  // -------------------------------------------------------------------------
  // Metadata & Reuse Library
  // -------------------------------------------------------------------------

  async persistDatasetMetadata(
    sessionId: string,
    consent: boolean,
    customName?: string
  ): Promise<{ status: string; dataset_id: string; fingerprint: string; name: string }> {
    const res = await fetch(`${this.baseUrl}/api/session/${sessionId}/persist`, {
      method: 'POST',
      headers: this.getHeaders(),
      body: JSON.stringify({ consent, custom_name: customName }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Metadata persistence failed' }));
      throw new Error(err.detail || `Persistence failed with HTTP ${res.status}`);
    }

    return res.json();
  }

  async listStoredDatasets(limit: number = 50, offset: number = 0): Promise<{ datasets: StoredDatasetSummary[]; count: number }> {
    const res = await fetch(`${this.baseUrl}/api/metadata/datasets?limit=${limit}&offset=${offset}`, {
      headers: this.getHeaders(null),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Failed to fetch stored datasets' }));
      throw new Error(err.detail || `List datasets failed with HTTP ${res.status}`);
    }

    return res.json();
  }

  async getStoredDataset(datasetId: string): Promise<StoredDatasetDetail> {
    const res = await fetch(`${this.baseUrl}/api/metadata/datasets/${datasetId}`, {
      headers: this.getHeaders(null),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Failed to fetch dataset details' }));
      throw new Error(err.detail || `Get dataset failed with HTTP ${res.status}`);
    }

    return res.json();
  }

  async deleteStoredDataset(datasetId: string): Promise<void> {
    const res = await fetch(`${this.baseUrl}/api/metadata/datasets/${datasetId}`, {
      method: 'DELETE',
      headers: this.getHeaders(null),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Failed to delete dataset' }));
      throw new Error(err.detail || `Delete dataset failed with HTTP ${res.status}`);
    }
  }

  async listRecipes(category?: string): Promise<{ recipes: Recipe[]; count: number }> {
    const url = category
      ? `${this.baseUrl}/api/recipes?category=${encodeURIComponent(category)}`
      : `${this.baseUrl}/api/recipes`;
    const res = await fetch(url, {
      headers: this.getHeaders(null),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Failed to list recipes' }));
      throw new Error(err.detail || `List recipes failed with HTTP ${res.status}`);
    }

    return res.json();
  }

  async createRecipe(name: string, category: string, spec: any, description: string = ''): Promise<{ status: string; recipe_id: string }> {
    const res = await fetch(`${this.baseUrl}/api/recipes`, {
      method: 'POST',
      headers: this.getHeaders(),
      body: JSON.stringify({ name, category, spec, description }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Failed to create recipe' }));
      throw new Error(err.detail || `Create recipe failed with HTTP ${res.status}`);
    }

    return res.json();
  }

  async getRecipeRecommendations(sessionId: string): Promise<RecipeRecommendationResponse> {
    const res = await fetch(`${this.baseUrl}/api/session/${sessionId}/recommend-recipes`, {
      headers: this.getHeaders(null),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Recommendation failed' }));
      throw new Error(err.detail || `Recommendations failed with HTTP ${res.status}`);
    }

    return res.json();
  }

  async applyRecipe(
    sessionId: string,
    recipeId: string,
    columnMapping: Record<string, string>
  ): Promise<{ result: AnalysisResult; adapted_parameters: any; validation_notes: string[] }> {
    const res = await fetch(`${this.baseUrl}/api/session/${sessionId}/apply-recipe`, {
      method: 'POST',
      headers: this.getHeaders(),
      body: JSON.stringify({ recipe_id: recipeId, column_mapping: columnMapping }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Failed to apply recipe' }));
      throw new Error(err.detail || `Apply recipe failed with HTTP ${res.status}`);
    }

    return res.json();
  }

  async listAuditEvents(limit: number = 50): Promise<{ events: AuditEventItem[]; count: number }> {
    const res = await fetch(`${this.baseUrl}/api/audit/events?limit=${limit}`, {
      headers: this.getHeaders(null),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Failed to fetch audit events' }));
      throw new Error(err.detail || `Audit fetch failed with HTTP ${res.status}`);
    }

    return res.json();
  }

  // -------------------------------------------------------------------------
  // Reports
  // -------------------------------------------------------------------------

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
