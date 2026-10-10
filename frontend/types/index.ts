export type ObjectClass = "marine_debris" | "suspected_ghost_gear" | "unknown_floating_object";
export type DetectionStatus = "unverified" | "verified" | "assigned" | "being_handled" | "resolved" | "rejected" | "recovered";
export type RiskLevel = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
export type PriorityLevel = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
export type AlertSeverity = "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";
export type AlertStatus = "active" | "acknowledged" | "in_progress" | "resolved";

export interface Detection {
  id: string;
  external_id: string;
  latitude: number;
  longitude: number;
  confidence: number;
  object_class: ObjectClass;
  status: DetectionStatus;
  incident_status?: string;
  assigned_to?: string;
  assigned_team?: string;
  verification_notes?: string;
  verified_by?: string;
  verified_at?: string | null;
  is_actionable_alert?: boolean;
  timestamp: string;
  source: string;
  scene_id: string;
  area_m2: number;
}

export interface DetectionListResponse {
  total: number;
  items: Detection[];
}

export interface AnalysisResult {
  detection_id: string;
  drift: {
    detection_id: string;
    mode: string;
    horizons: Array<{
      forecast_hour: number;
      timestamp: string;
      mean_latitude: number;
      mean_longitude: number;
      position_geometry?: any;
      uncertainty_geometry?: any;
    }>;
  };
  geospatial: {
    protected_area_overlap: boolean;
    protected_areas: string[];
    habitat_overlap: boolean;
    habitats: string[];
    habitat_kinds: string[];
    distance_to_coastline_km: number;
    distance_to_nearest_protected_area_km: number;
    nearest_protected_area: string | null;
    estimated_time_to_protected_area_hours: number;
  };
  risk: {
    risk_score: number;
    risk_level: RiskLevel;
    reason_codes: string[];
    feature_values?: Record<string, any>;
  };
  priority: {
    priority_level: PriorityLevel;
    recommended_action: string;
    priority_rank?: number;
  };
  report: {
    summary: string;
    evidence: Array<{ text: string; source: string; score: number }>;
    limitations: string[];
  };
}

export interface User {
  id: string;
  email: string;
  full_name: string;
  organization: string;
  role: "ngo" | "responder" | "researcher" | "coast_guard" | "admin";
  phone?: string;
  created_at?: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface IncidentAction {
  id: string;
  action: "verify" | "reject" | "assign" | "being_handled" | "resolve" | "note_added";
  previous_status: string;
  new_status: string;
  user_name: string;
  organization: string;
  assigned_team?: string;
  notes?: string;
  timestamp: string;
}

export interface IncidentHistoryResponse {
  detection_id: string;
  current_status: string;
  actions: IncidentAction[];
}

export interface ResponderAlertItem {
  id: string;
  external_id: string;
  latitude: number;
  longitude: number;
  confidence: number;
  object_class: string;
  status: string;
  timestamp: string;
  source: string;
  assigned_to?: string;
  assigned_team?: string;
  verification_notes?: string;
  verified_by?: string;
  risk_score?: number | null;
  risk_level?: RiskLevel | null;
  priority_level?: PriorityLevel | null;
  recommended_action?: string | null;
}

export interface ResponderAlertsResponse {
  verification_queue: ResponderAlertItem[];
  actionable_alerts: ResponderAlertItem[];
  total_requiring_action: number;
  total_actionable: number;
}

export interface EcologicalAlert {
  id: string;
  detection_id: string;
  external_id: string;
  alert_type: string;
  severity: AlertSeverity;
  status: AlertStatus;
  headline: string;
  details: string;
  region_name: string;
  feature_type: string;
  species_at_risk: string[];
  distance_km: number;
  estimated_impact_hours: number;
  impact_point_geometry: any;
  recommended_action: string;
  source_citation: string;
  created_at: string;
  updated_at: string;
}

export interface FeatureCollection {
  type: "FeatureCollection";
  features: any[];
  properties?: Record<string, any>;
}

export interface DataSourceItem {
  id: string;
  endpoint?: string;
  source: string;
  license?: string;
}

export interface MarineModelInfo {
  status: string;
  model_name: string;
  checkpoint_file: string;
  checkpoint_path: string;
  checkpoint_exists: boolean;
  checkpoint_size_mb: number;
  val_mIoU: number;
  val_mIoU_percentage: string;
  best_epoch: number;
  input_channels: number;
  num_classes: number;
  classes: string[];
  class_palette: string[];
  framework: string;
}

export interface ClassBreakdownItem {
  class_id: number;
  name: string;
  pixel_count: number;
  percentage: number;
  area_m2: number;
  area_km2: number;
  color: string;
}

export interface MarinePredictionSummary {
  debris_pixel_count: number;
  debris_area_m2: number;
  debris_area_km2: number;
  debris_percentage: number;
  debris_mean_confidence: number;
  sargassum_pixel_count: number;
  ship_pixel_count: number;
  severity_level: "CRITICAL" | "HIGH" | "MODERATE" | "LOW";
  recommended_action: string;
  image_dimensions: { width: number; height: number };
  pixel_resolution_meters: number;
}

export interface MarinePredictionResult {
  status: string;
  filename?: string;
  sample_name?: string;
  is_geotiff?: boolean;
  georeferencing?: any;
  summary: MarinePredictionSummary;
  class_breakdown: ClassBreakdownItem[];
  visualizations: {
    rgb_quicklook: string;
    segmentation_mask: string;
    debris_overlay: string;
  };
  created_detections?: Array<{
    id: string;
    external_id: string;
    latitude: number;
    longitude: number;
    area_m2: number;
    confidence: number;
  }>;
}

export interface SatellitePreviewResponse {
  external_id: string;
  region_name?: string;
  scene_id: string;
  acquisition_date?: string;
  cloud_coverage_pct?: number;
  source: string;
  project_id?: string;
  summary: MarinePredictionSummary;
  class_breakdown: ClassBreakdownItem[];
  visualizations: {
    rgb_quicklook: string;
    segmentation_mask: string;
    debris_overlay: string;
  };
}
