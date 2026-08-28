export type GeoStatus = "computed" | "survey_position_only" | "unavailable";

export type RiskLevel = "High" | "Medium" | "Low";

export interface BBox {
  x: number;
  y: number;
  width: number;
  height: number;
  x1: number;
  y1: number;
  x2: number;
  y2: number;
}

export interface Geolocation {
  latitude: number | null;
  longitude: number | null;
  status: GeoStatus;
}

export interface ShadowZone {
  x: number;
  y: number;
  width: number;
  height: number;
  adjacent_to_highlight: boolean;
}

export interface Detection {
  id: string;
  class: string;
  confidence: number;
  bbox: BBox;
  geolocation: Geolocation;
  risk_level: string;
  risk_score: number;
  passed_filter?: boolean;
  rejection_reason?: string | null;
  mask_points?: number[][] | null;
}

export interface RunResult {
  id: string;
  filename: string;
  model: string;
  inference_mode: string;
  image_width: number;
  image_height: number;
  metadata_attached: boolean;
  conf_threshold?: number;
  raw_detections?: Detection[];
  filtered_detections?: Detection[];
  detections: Detection[];
  shadow_zones: ShadowZone[];
  geolocation_available?: boolean;
  geolocation_note?: string;
  annotated_image_url?: string;
  json_report_url?: string;
  csv_report_url?: string;
}

export interface RunSummary {
  id: string;
  filename: string;
  inference_mode: string;
  detection_count: number;
}

export interface SystemInfo {
  version: string;
  model: string;
  classes: string[];
  segmentation_support: boolean;
  onnx_available: boolean;
  metadata_formats: string[];
  max_upload_mb: number;
  confidence_threshold: number;
}
