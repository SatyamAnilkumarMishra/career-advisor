import {
  ChatMessage,
  JobListing,
  ResumeAnalysis,
  ResumeUploadResponse,
  RoadmapResult,
  SkillGapResult,
  SourceItem,
  StatusResponse,
} from '@/types';

// When running in browser, default to relative path '' so Next.js rewrites proxy to backend
// seamlessly without CORS or localhost/127.0.0.1 IPv4/IPv6 mismatch.
const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? '';

let _authToken: string | null = null;

export function setAuthToken(token: string | null): void {
  _authToken = token;
}

export function getAuthToken(): string | null {
  return _authToken;
}

function getAuthHeaders(): Record<string, string> {
  const headers: Record<string, string> = {};
  if (_authToken) {
    headers['Authorization'] = `Bearer ${_authToken}`;
  }
  return headers;
}

/**
 * Narrow an unknown thrown value to a displayable message.
 *
 * `catch (err)` is typed `unknown` under TypeScript's `useUnknownInCatchVariables`
 * (and `catch (err: any)` is an eslint error), so every call site funnels through
 * here instead of reaching for `err.message` on an untyped value.
 */
export function getErrorMessage(err: unknown, fallback = 'Something went wrong.'): string {
  if (err instanceof Error && err.message) {
    const msg = err.message.toLowerCase();
    if (msg.includes('failed to fetch') || msg.includes('networkerror') || msg.includes('load failed')) {
      return 'Unable to connect to backend server. Please make sure the backend is running with "python app.py api" on http://127.0.0.1:8000.';
    }
    return err.message;
  }
  if (typeof err === 'string' && err) return err;
  return fallback;
}

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let errorMsg = `Server error (${res.status})`;
    let parsedJson = false;
    try {
      const err = await res.json();
      parsedJson = true;
      if (err.detail) {
        errorMsg = typeof err.detail === 'string' ? err.detail : JSON.stringify(err.detail);
      }
    } catch {
      // ignore json parse error
    }

    if (!parsedJson) {
      if (res.status === 401) {
        errorMsg = 'Your session has expired or you are not logged in. Please sign in again.';
      } else if (res.status === 404) {
        errorMsg = 'Backend server endpoint not found (404). Please ensure the backend is running with "python app.py api".';
      } else if (res.status === 502 || res.status === 503 || res.status === 504) {
        errorMsg = `Backend server is temporarily unavailable (${res.status}). Please run "python app.py api" to start the backend.`;
      }
    }

    throw new Error(errorMsg);
  }
  return res.json();
}

export async function fetchStatus(): Promise<StatusResponse> {
  const res = await fetch(`${API_BASE}/api/status`, {
    headers: { ...getAuthHeaders() },
    cache: 'no-store',
  });
  return handleResponse<StatusResponse>(res);
}

export async function fetchCurrentUser(): Promise<{
  uid: string;
  email: string | null;
  display_name: string | null;
  photo_url: string | null;
}> {
  const res = await fetch(`${API_BASE}/api/auth/me`, {
    headers: { ...getAuthHeaders() },
    cache: 'no-store',
  });
  return handleResponse(res);
}

export async function sendChatMessage(
  query: string,
  history: ChatMessage[],
  studentProfile: string = ''
): Promise<{ text: string; used_retrieval: boolean; sources: SourceItem[] }> {
  const res = await fetch(`${API_BASE}/api/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeaders(),
    },
    body: JSON.stringify({
      query,
      history: history.map((m) => ({ role: m.role, content: m.content })),
      student_profile: studentProfile,
    }),
  });
  return handleResponse(res);
}

export async function uploadResumeFile(file: File): Promise<ResumeUploadResponse> {
  const formData = new FormData();
  formData.append('file', file);

  const res = await fetch(`${API_BASE}/api/resume/upload`, {
    method: 'POST',
    headers: { ...getAuthHeaders() },
    body: formData,
  });
  return handleResponse<ResumeUploadResponse>(res);
}

export async function analyzeResume(
  resumeText: string,
  targetRole?: string
): Promise<ResumeAnalysis> {
  const res = await fetch(`${API_BASE}/api/resume/analyze`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeaders(),
    },
    body: JSON.stringify({
      resume_text: resumeText,
      target_role: targetRole || null,
    }),
  });
  return handleResponse<ResumeAnalysis>(res);
}

export async function analyzeSkillGap(
  skills: string[],
  targetRole: string
): Promise<SkillGapResult> {
  const res = await fetch(`${API_BASE}/api/skill-gap`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeaders(),
    },
    body: JSON.stringify({
      skills,
      target_role: targetRole,
    }),
  });
  return handleResponse<SkillGapResult>(res);
}

export async function generateRoadmap(
  skills: string[],
  targetRole: string,
  timeframeMonths: number = 6
): Promise<RoadmapResult> {
  const res = await fetch(`${API_BASE}/api/roadmap`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeaders(),
    },
    body: JSON.stringify({
      skills,
      target_role: targetRole,
      timeframe_months: timeframeMonths,
    }),
  });
  return handleResponse<RoadmapResult>(res);
}

export async function searchJobs(params: {
  role: string;
  skills?: string[];
  location?: string;
  experience_level?: string;
  limit?: number;
}): Promise<JobListing[]> {
  const res = await fetch(`${API_BASE}/api/jobs/search`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeaders(),
    },
    body: JSON.stringify(params),
  });
  return handleResponse<JobListing[]>(res);
}

export async function uploadDocumentFile(
  file: File
): Promise<{ success: boolean; filename: string; message: string }> {
  const formData = new FormData();
  formData.append('file', file);

  const res = await fetch(`${API_BASE}/api/documents/upload`, {
    method: 'POST',
    headers: { ...getAuthHeaders() },
    body: formData,
  });
  return handleResponse(res);
}

export async function fetchHistory(): Promise<{ id: string; query: string; timestamp: string }[]> {
  const res = await fetch(`${API_BASE}/api/history`, {
    headers: { ...getAuthHeaders() },
    cache: 'no-store',
  });
  return handleResponse(res);
}

export async function addHistoryItem(query: string): Promise<{ id: string; query: string; timestamp: string }> {
  const res = await fetch(`${API_BASE}/api/history`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeaders(),
    },
    body: JSON.stringify({ query }),
  });
  return handleResponse(res);
}

export async function deleteHistoryItem(id: string): Promise<{ success: boolean; deleted_id: string }> {
  const res = await fetch(`${API_BASE}/api/history/${item_id_param(id)}`, {
    method: 'DELETE',
    headers: { ...getAuthHeaders() },
  });
  return handleResponse(res);
}

function item_id_param(id: string): string {
  return encodeURIComponent(id);
}

export async function clearAllHistory(): Promise<{ success: boolean }> {
  const res = await fetch(`${API_BASE}/api/history`, {
    method: 'DELETE',
    headers: { ...getAuthHeaders() },
  });
  return handleResponse(res);
}

export async function clearConversation(): Promise<{ success: boolean }> {
  const res = await fetch(`${API_BASE}/api/chat/clear`, {
    method: 'POST',
    headers: { ...getAuthHeaders() },
  });
  return handleResponse(res);
}

export async function fetchUserLatestData(): Promise<{
  resume: any;
  skill_gap: any;
  roadmap: any;
}> {
  const res = await fetch(`${API_BASE}/api/user-data/latest`, {
    headers: { ...getAuthHeaders() },
    cache: 'no-store',
  });
  return handleResponse(res);
}
