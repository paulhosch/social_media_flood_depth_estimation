export interface FloodDepthDetection {
  level: number;
  confidence: number;
  bbox: [number, number, number, number];
}

export interface MapPoint {
  file_name: string;
  lon: number;
  lat: number;
  platform: string;
  post_id: string;
  caption: string;
  tags: string[];
  exif_taken_at_original: string | null;
  exif_taken_at_record: string | null;
  taken_at: string | null;
  stack_count: number;
  flood_class: string;
  flood_score_flooded: number;
  flood_score_non_flooded: number;
  flood_depth_max_level?: number | null;
  flood_depth_vehicle_count?: number;
  flood_depth_high_danger?: boolean;
  flood_depth_detections?: FloodDepthDetection[];
}

export interface MapIndex {
  generated_at: string;
  point_count: number;
  time_range: { min: string | null; max: string | null };
  points: MapPoint[];
}

export type ColorMode =
  | "uniform"
  | "datetime"
  | "density"
  | "flood_classification"
  | "flood_depth";

export type FloodClassificationFilter = "all" | "flooded" | "non_flooded";

export type FloodDepthFilter =
  | "all"
  | "has_vehicles"
  | "high_danger"
  | "no_vehicles";

export type MapPointColored = MapPoint & {
  color: [number, number, number, number];
};
