/**
 * Chat API client — wraps POST /api/v1/chat
 */

const CHAT_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export interface UserLocation {
  lat: number;
  lon: number;
}

export interface ChatRequest {
  message: string;
  session_id: string;
  user_location?: UserLocation | null;
}

export interface OriginCoords {
  lat: number;
  lon: number;
}

export interface ParsedQuery {
  intent: "debris_near_route" | "off_topic" | "clarification_needed";
  date?: string | null;
  date_label?: string | null;
  origin_name?: string | null;
  origin_coords?: OriginCoords | null;
  bearing_deg?: number | null;
  bearing_label?: string | null;
  distance_km?: number | null;
  search_radius_km: number;
  needs_clarification: boolean;
  clarification_field?: string | null;
  raw_message: string;
}

export interface HotspotPoint {
  lat: number;
  lon: number;
  object_class: string;
  count: number;
  confidence_avg: number;
  distance_from_start_km: number;
}

export interface DebrisSummary {
  total_debris: number;
  ghost_nets: number;
  suspected_ghost_gear: number;
  other_debris: number;
  unknown_objects: number;
  hotspots: HotspotPoint[];
  data_date: string | null;
  nearest_available_date: string | null;
  data_source: string;
}

export interface ChatResponse {
  reply: string;
  parsed_query: ParsedQuery;
  geojson: GeoJSON.FeatureCollection | null;
  summary: DebrisSummary | null;
  needs_clarification: boolean;
  session_id: string;
}

export async function postChat(req: ChatRequest): Promise<ChatResponse> {
  const res = await fetch(`${CHAT_BASE}/api/v1/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  if (!res.ok) {
    const detail = await res.text().catch(() => res.statusText);
    throw new Error(`Chat API error ${res.status}: ${detail}`);
  }
  return res.json() as Promise<ChatResponse>;
}
