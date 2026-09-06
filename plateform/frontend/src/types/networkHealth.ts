export interface NetworkFilters {
  event_type: string;
  status: string;
  device: string;
  cluster: string;
  incident: string;
  search: string;
  start: string;
  end: string;
}

export interface NetworkSummary {
  connectivity_checks: number;
  grants: number;
  denials: number;
  releases: number;
  errors: number;
  latest_event_at: string | null;
  data_mode: string;
  contract_status: string;
  note: string;
  reference_time: string;
}

export interface NetworkEventSummary {
  id: string;
  public_id: string;
  event_id: string;
  event_type: string;
  status: string;
  summary: string;
  cluster_id: string | null;
  device_id: string | null;
  incident_id: string | null;
  occurred_at: string;
  data_mode: string;
  contract_version: string;
}

export interface NetworkEventDetail extends NetworkEventSummary {
  payload: Record<string, unknown>;
  input_summary: Record<string, unknown>;
  output_summary: Record<string, unknown>;
  error_code: string | null;
  error_message: string | null;
}

export interface NetworkEventListResponse {
  items: NetworkEventSummary[];
  total: number;
  page: number;
  page_size: number;
  data_mode: string;
  note: string;
}
