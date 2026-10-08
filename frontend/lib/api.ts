import type {
  AnalysisResult,
  AuthResponse,
  Detection,
  DetectionListResponse,
  EcologicalAlert,
  FeatureCollection,
  IncidentHistoryResponse,
  ResponderAlertsResponse,
  User,
} from "@/types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

function getAuthHeader(): Record<string, string> {
  if (typeof window === "undefined") return {};
  const token = localStorage.getItem("ghostnet_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = {
    "Content-Type": "application/json",
    ...getAuthHeader(),
    ...(init?.headers || {}),
  };

  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers,
    cache: "no-store",
  });

  if (!res.ok) {
    let errorDetail = "";
    try {
      const json = await res.json();
      errorDetail = json.detail || JSON.stringify(json);
    } catch {
      errorDetail = await res.text().catch(() => "");
    }
    throw new Error(`API error (${res.status}): ${errorDetail || res.statusText}`);
  }

  return res.json() as Promise<T>;
}

export const api = {
  // Auth & Profile
  login: async (email: string, password: string): Promise<AuthResponse> => {
    const data = await request<AuthResponse>("/api/v1/users/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    if (typeof window !== "undefined" && data.access_token) {
      localStorage.setItem("ghostnet_token", data.access_token);
      localStorage.setItem("ghostnet_user", JSON.stringify(data.user));
    }
    return data;
  },

  register: async (payload: {
    email: string;
    password: string;
    full_name: string;
    organization?: string;
    role?: string;
    phone?: string;
  }): Promise<{ id: string; email: string; full_name: string; message: string }> => {
    return request("/api/v1/users/register", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  getMe: (): Promise<User> => request<User>("/api/v1/users/me"),

  logout: () => {
    if (typeof window !== "undefined") {
      localStorage.removeItem("ghostnet_token");
      localStorage.removeItem("ghostnet_user");
    }
  },

  getCurrentStoredUser: (): User | null => {
    if (typeof window === "undefined") return null;
    const raw = localStorage.getItem("ghostnet_user");
    if (!raw) return null;
    try {
      return JSON.parse(raw);
    } catch {
      return null;
    }
  },

  // Responder Inbox & Incident Lifecycle
  getResponderAlerts: (): Promise<ResponderAlertsResponse> =>
    request<ResponderAlertsResponse>("/api/v1/users/alerts"),

  updateIncident: (
    detectionId: string,
    action: "verify" | "reject" | "assign" | "being_handled" | "resolve",
    payload?: { assigned_team?: string; notes?: string }
  ): Promise<any> =>
    request(`/api/v1/users/incidents/${detectionId}/update`, {
      method: "POST",
      body: JSON.stringify({ action, ...(payload || {}) }),
    }),

  getIncidentHistory: (detectionId: string): Promise<IncidentHistoryResponse> =>
    request<IncidentHistoryResponse>(`/api/v1/users/incidents/${detectionId}/history`),

  // Ecological Alerts
  listEcologicalAlerts: (params?: { status?: string; severity?: string }): Promise<{ total: number; alerts: EcologicalAlert[] }> => {
    const query = new URLSearchParams();
    if (params?.status) query.set("status", params.status);
    if (params?.severity) query.set("severity", params.severity);
    const qs = query.toString() ? `?${query.toString()}` : "";
    return request<{ total: number; alerts: EcologicalAlert[] }>(`/api/v1/alerts${qs}`);
  },

  getActiveEcologicalAlerts: (): Promise<{
    total_active: number;
    critical: number;
    high: number;
    alerts: EcologicalAlert[];
  }> => request("/api/v1/alerts/active"),

  acknowledgeAlert: (alertId: string): Promise<{ id: string; status: string }> =>
    request(`/api/v1/alerts/${alertId}/acknowledge`, { method: "POST" }),

  resolveAlert: (alertId: string): Promise<{ id: string; status: string }> =>
    request(`/api/v1/alerts/${alertId}/resolve`, { method: "POST" }),

  mapAlertsGeoJSON: (): Promise<FeatureCollection> =>
    request<FeatureCollection>("/api/v1/alerts/map/geojson"),

  // Detections & Analysis
  listDetections: (status?: string): Promise<DetectionListResponse> => {
    const qs = status ? `?status=${status}` : "";
    return request<DetectionListResponse>(`/api/v1/detections${qs}`);
  },

  getDetection: (id: string): Promise<Detection> =>
    request<Detection>(`/api/v1/detections/${id}`),

  analyzeSync: (id: string): Promise<AnalysisResult> =>
    request<AnalysisResult>(`/api/v1/detections/${id}/analyze?sync=true`, {
      method: "POST",
    }),

  createDetection: (payload: {
    latitude: number;
    longitude: number;
    confidence: number;
    object_class?: string;
    source?: string;
  }): Promise<Detection> =>
    request<Detection>("/api/v1/detections", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  // Map Data Layers
  mapDetections: (): Promise<FeatureCollection> =>
    request<FeatureCollection>("/api/v1/map/detections"),

  mapTrajectories: (): Promise<FeatureCollection> =>
    request<FeatureCollection>("/api/v1/map/trajectories"),

  mapRiskZones: (): Promise<FeatureCollection> =>
    request<FeatureCollection>("/api/v1/map/risk-zones"),

  mapProtectedAreas: (): Promise<FeatureCollection> =>
    request<FeatureCollection>("/api/v1/map/protected-areas"),

  mapHabitats: (): Promise<FeatureCollection> =>
    request<FeatureCollection>("/api/v1/map/habitats"),

  mapCoralReefs: (): Promise<FeatureCollection> =>
    request<FeatureCollection>("/api/v1/map/coral-reefs"),

  mapSpeciesHabitats: (): Promise<FeatureCollection> =>
    request<FeatureCollection>("/api/v1/map/species-habitats"),

  mapExtendedMPAs: (): Promise<FeatureCollection> =>
    request<FeatureCollection>("/api/v1/map/extended-mpas"),

  mapCurrents: (): Promise<{ source: string; dataset_id: string; timestamp: string; count: number; vectors: any[] }> =>
    request("/api/v1/map/currents"),

  mapLayersMetadata: (): Promise<{ layers: any[] }> =>
    request<{ layers: any[] }>("/api/v1/map/layers"),

  systemStatus: (): Promise<Record<string, unknown>> =>
    request<Record<string, unknown>>("/api/v1/system/status"),
};
