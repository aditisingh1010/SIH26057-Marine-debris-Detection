export type GeoStatus = "computed" | "survey_position_only" | "unavailable";

export type RiskLevel = "High" | "Medium" | "Low";

export interface BBox {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface Geolocation {
  latitude: number | null;
  longitude: number | null;
  status: GeoStatus;
}

export interface Detection {
  id: string;
  class: string;
  confidence: number;
  bbox: BBox;
  geolocation: Geolocation;
  risk_level: string;
  risk_score: number;
}

export interface RunResult {
  id: string;
  filename: string;
  model: string;
  inference_mode: string;
  image_width: number;
  image_height: number;
  metadata_attached: boolean;
  detections: Detection[];
}
