export type JobStatus = "QUEUED" | "PROCESSING" | "COMPLETED" | "FAILED" | "CANCELLED";

export interface Job {
  id: string;
  batch_id: string | null;
  status: JobStatus;
  input_path: string;
  input_filename: string;
  source_language: string | null;
  detected_language: string | null;
  target_language: string | null;
  output_formats: string[];
  burn_in: boolean;
  enable_diarization: boolean;
  whisper_model: string;
  ollama_model: string | null;
  subtitle_style: SubtitleStyle | null;
  video_preset: string | null;
  priority: number;
  current_step: string | null;
  progress_percent: number;
  error_message: string | null;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
  output_subtitle_paths: string[] | null;
  output_video_path: string | null;
}

export interface SubtitleStyle {
  font_name: string;
  font_size: number;
  primary_color: string;
  secondary_color: string;
  outline_color: string;
  shadow_color: string;
  outline_width: number;
  shadow_depth: number;
  alignment: number;
  margin_left: number;
  margin_right: number;
  margin_vertical: number;
  bold: boolean;
  italic: boolean;
  max_line_length: number;
  max_lines: number;
}

export interface JobCreate {
  input_path: string;
  source_language?: string | null;
  target_language?: string | null;
  output_formats: string[];
  burn_in?: boolean;
  enable_diarization?: boolean;
  whisper_model?: string;
  ollama_model?: string;
  subtitle_style?: SubtitleStyle;
  video_preset?: string;
  priority?: number;
}

export interface Batch {
  id: string;
  name: string | null;
  status: string;
  total_jobs: number;
  completed_jobs: number;
  failed_jobs: number;
  created_at: string;
  completed_at: string | null;
}

export interface Preset {
  id: string;
  name: string;
  description: string | null;
  subtitle_style: SubtitleStyle;
  video_settings: Record<string, unknown> | null;
  is_builtin: boolean;
}

export interface HealthStatus {
  status: string;
  services: {
    api: string;
    redis: string;
    ollama: string;
    gpu: {
      available: boolean;
      name?: string;
      vram_total_mb?: number;
      vram_free_mb?: number;
    };
  };
  disk: {
    videos: DiskUsage;
    models: DiskUsage;
  };
}

export interface DiskUsage {
  total_gb: number;
  free_gb: number;
  used_percent: number;
}

export interface JobProgressEvent {
  job_id: string;
  status: JobStatus;
  step: string;
  step_number: number;
  total_steps: number;
  progress_percent: number;
  eta_seconds: number | null;
  message: string;
}
