export type GeoStatus = "computed" | "survey_position_only" | "unavailable";

export interface Detection {
  id: string;
  class: string;
  confidence: number;
  bbox: { x: number; y: number; width: number; height: number };
  geolocation: { latitude: number | null; longitude: number | null; status: GeoStatus };
}

export interface RunResult {
  id: string;
  filename: string;
  model: string;
  image_width: number;
  image_height: number;
  metadata_attached: boolean;
  detections: Detection[];
}
