// Everything that talks to the backend lives here.

const TOKEN_KEY = "studysphere_token";

export const getToken = (): string | null => localStorage.getItem(TOKEN_KEY);

export function setToken(token: string | null): void {
  if (token) localStorage.setItem(TOKEN_KEY, token);
  else localStorage.removeItem(TOKEN_KEY);
}

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

export function messageOf(error: unknown): string {
  return error instanceof Error ? error.message : "Something went wrong.";
}

export interface SubjectItem {
  id: number;
  name: string;
  document_count: number;
  chunk_count: number;
  created_at: string;
}

export interface DocumentSummary {
  id: number;
  filename: string;
  kind: string;
  size_bytes: number;
  page_count: number;
  chunk_count: number;
  subject_id: number | null;
  created_at: string;
}

export interface DashboardData {
  document_count: number;
  chunk_count: number;
  unassigned_document_count: number;
  subjects: SubjectItem[];
  documents: DocumentSummary[];
}

export interface Source {
  number: number;
  chunk_id: number;
  document_id: number;
  filename: string;
  page_number: number;
  text: string;
  cited: boolean;
}

export interface AnswerResponse {
  status: string;
  message: string;
  answer: string | null;
  sources: Source[];
  warnings: string[];
  support: number | null;
  provider: string | null;
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  const token = getToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);

  let response: Response;
  try {
    response = await fetch(`/api${path}`, { ...init, headers });
  } catch {
    throw new ApiError(0, "Could not reach the server. Is it running?");
  }

  if (!response.ok) {
    let detail = `Request failed (${response.status})`;
    try {
      const body = await response.json();
      if (typeof body.detail === "string") detail = body.detail;
      else if (Array.isArray(body.detail)) detail = "Please check what you typed.";
    } catch {
      /* keep the default message */
    }
    if (response.status === 401 && token) {
      setToken(null); // the session expired: send the person back to the login page
      window.dispatchEvent(new Event("auth-expired"));
    }
    throw new ApiError(response.status, detail);
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

const jsonHeaders = { "Content-Type": "application/json" };

export const api = {
  async register(email: string, password: string): Promise<void> {
    await request("/auth/register", { method: "POST", headers: jsonHeaders, body: JSON.stringify({ email, password }) });
  },

  async login(email: string, password: string): Promise<void> {
    const form = new URLSearchParams({ username: email, password });
    const data = await request<{ access_token: string }>("/auth/login", { method: "POST", body: form });
    setToken(data.access_token);
  },

  dashboard: () => request<DashboardData>("/dashboard"),

  listSubjects: () => request<SubjectItem[]>("/subjects"),

  createSubject: (name: string) =>
    request<SubjectItem>("/subjects", { method: "POST", headers: jsonHeaders, body: JSON.stringify({ name }) }),

  deleteSubject: (id: number) => request<void>(`/subjects/${id}`, { method: "DELETE" }),

  assignDocument: (subjectId: number, documentId: number) =>
    request<void>(`/subjects/${subjectId}/documents/${documentId}`, { method: "PUT" }),

  unassignDocument: (subjectId: number, documentId: number) =>
    request<void>(`/subjects/${subjectId}/documents/${documentId}`, { method: "DELETE" }),

  async uploadDocument(file: File): Promise<void> {
    const form = new FormData();
    form.append("file", file);
    await request<unknown>("/documents", { method: "POST", body: form });
  },

  deleteDocument: (id: number) => request<void>(`/documents/${id}`, { method: "DELETE" }),

  ask: (question: string, subjectId?: number) =>
    request<AnswerResponse>("/ask", {
      method: "POST",
      headers: jsonHeaders,
      body: JSON.stringify({ question, subject_id: subjectId ?? null }),
    }),
};