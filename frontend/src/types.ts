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
  width_m?: number | null;
  height_m?: number | null;
  estimated_height_m?: number | null;
  shadow_length_m?: number | null;
  acoustic_shadow_overlap?: boolean;
  would_pass_demo?: boolean;
  would_pass_survey?: boolean;
  review_priority?: string;
}

export interface OperatorBriefing {
  kept: number;
  suppressed: number;
  demo_kept: number;
  survey_kept: number;
  extra_survey_candidates: number;
  immediate_count: number;
  review_queue_count: number;
  shadow_overlap_count: number;
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
  detection_mode?: "demo" | "survey" | "custom";
  raw_detections?: Detection[];
  filtered_detections?: Detection[];
  detections: Detection[];
  filter_stats?: {
    total_raw: number;
    total_filtered: number;
    noise_reduced_count: number;
  };
  operator_briefing?: OperatorBriefing;
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
  detection_mode?: string;
  geolocation_available?: boolean;
  created_at?: string | null;
}

export interface BatchResult {
  runs: RunResult[];
  total: number;
  failed: number;
  errors: string[];
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

export interface DatasetQuality {
  total_images: number;
  labeled_images: number;
  background_images: number;
  total_annotations: number;
  class_counts: Record<string, number>;
  image_sizes: string[];
  label_issues: number;
  summary: string;
}

export interface EvaluationMetricSet {
  precision: number;
  recall: number;
  mAP50: number;
  mAP50_95: number;
  inference_ms_cpu: number;
  confidence_threshold: number;
  test_images: number;
  test_annotations: number;
}

export interface ModelQuality {
  model_name: string;
  task: string;
  classes: string[];
  segmentation_support: boolean;
  onnx_available: boolean;
  evaluation_split: string;
  quality_available?: boolean;
  metrics_source?: string;
  primary_metrics: EvaluationMetricSet;
  pr_sweep_metrics: EvaluationMetricSet;
  dataset: DatasetQuality;
  limitations: string[];
  next_improvements: string[];
}
