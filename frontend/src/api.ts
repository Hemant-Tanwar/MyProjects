export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || (typeof window !== "undefined" && window.location.hostname !== "localhost" && window.location.hostname !== "127.0.0.1" ? "/api" : "http://localhost:8001");

export interface Session {
  id: string;
  name: string;
  description: string | null;
  status: string;
  current_role: string;
  requirement_file?: string | null;
  created_at: string;
  updated_at: string;
}

export interface Artifact {
  id: number;
  session_id: string;
  stage: string;
  version: number;
  content: string;
  rationale: string | null;
  approved: boolean;
  approved_by: string | null;
  created_at: string;
}

export interface AuditLog {
  id: number;
  session_id: string;
  stage: string;
  agent_name: string;
  action: string;
  prompt: string | null;
  response: string | null;
  error: string | null;
  timestamp: string;
}

export async function createSession(name: string, initialRequirement: string): Promise<Session> {
  const response = await fetch(`${API_BASE_URL}/sessions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, initial_requirement: initialRequirement }),
  });
  if (!response.ok) {
    const err = await response.json();
    throw new Error(err.detail || "Failed to create session");
  }
  return response.json();
}

export async function listSessions(): Promise<Session[]> {
  const response = await fetch(`${API_BASE_URL}/sessions`);
  if (!response.ok) throw new Error("Failed to load sessions");
  return response.json();
}

export async function getSession(id: string): Promise<Session> {
  const response = await fetch(`${API_BASE_URL}/sessions/${id}`);
  if (!response.ok) throw new Error("Failed to load session details");
  return response.json();
}

export async function deleteSession(id: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/sessions/${id}`, { method: "DELETE" });
  if (!response.ok) throw new Error("Failed to delete session");
}

export async function triggerAgent(id: string, stage: string): Promise<Artifact> {
  const response = await fetch(`${API_BASE_URL}/sessions/${id}/trigger`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ stage }),
  });
  if (!response.ok) {
    const err = await response.json();
    throw new Error(err.detail || `Agent execution failed for stage: ${stage}`);
  }
  return response.json();
}

export async function getArtifact(id: string, stage: string): Promise<Artifact> {
  const response = await fetch(`${API_BASE_URL}/sessions/${id}/artifacts/${stage}`);
  if (!response.ok) {
    throw new Error(`No artifact generated for stage ${stage}`);
  }
  return response.json();
}

export async function editArtifact(id: string, stage: string, content: string, rationale: string): Promise<Artifact> {
  const response = await fetch(`${API_BASE_URL}/sessions/${id}/artifacts/${stage}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ content, rationale }),
  });
  if (!response.ok) {
    const err = await response.json();
    throw new Error(err.detail || "Failed to save edits");
  }
  return response.json();
}

export async function approveArtifact(id: string, stage: string, approved: boolean, notes: string): Promise<Artifact> {
  const response = await fetch(`${API_BASE_URL}/sessions/${id}/artifacts/${stage}/approve`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ approved, notes }),
  });
  if (!response.ok) {
    const err = await response.json();
    throw new Error(err.detail || "Failed to update approval status");
  }
  return response.json();
}

export async function switchRole(id: string, role: string): Promise<Session> {
  const response = await fetch(`${API_BASE_URL}/sessions/${id}/role`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ role }),
  });
  if (!response.ok) {
    const err = await response.json();
    throw new Error(err.detail || "Failed to switch role");
  }
  return response.json();
}

export async function getAuditLogs(id: string): Promise<AuditLog[]> {
  const response = await fetch(`${API_BASE_URL}/sessions/${id}/audit_logs`);
  if (!response.ok) throw new Error("Failed to load audit logs");
  return response.json();
}

export async function pushArtifact(id: string, stage: string): Promise<Artifact> {
  const response = await fetch(`${API_BASE_URL}/sessions/${id}/artifacts/${stage}/push`, {
    method: "POST"
  });
  if (!response.ok) {
    // Safely parse error body — backend may return text/plain on unhandled 500s
    let errorMsg = `Failed to push stage '${stage}' to Celonis.`;
    try {
      const err = await response.json();
      errorMsg = err.detail || errorMsg;
    } catch {
      try {
        const text = await response.text();
        if (text) errorMsg = text;
      } catch { /* ignore */ }
    }
    throw new Error(errorMsg);
  }
  return response.json();
}

export function getPromotionUrl(id: string): string {
  return `${API_BASE_URL}/sessions/${id}/promote`;
}

export async function uploadRequirementFile(id: string, file: File): Promise<{ message: string; filename: string; file_path: string }> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API_BASE_URL}/sessions/${id}/upload_requirement_file`, {
    method: "POST",
    body: formData,
  });
  if (!response.ok) {
    const err = await response.json();
    throw new Error(err.detail || "Failed to upload PowerPoint requirement file");
  }
  return response.json();
}

