// Types aligned with backend API responses (see app/routes/api.py)

export interface Review {
  id: number;
  author: string;
  rating: number;
  title: string;
  content: string;
  version: string;
  date: string;
}

export interface Topic {
  id: number;
  name: string;
  description: string;
  confidence: number;
  sample_count: number;
  is_model_generated: boolean;
}

export interface Finding {
  id: number;
  run_id: number;
  topic_id: number | null;
  finding_text: string;
  description: string; // alias
  finding_type: string;
  impact: string;
  evidence_review_ids: number[];
  sample_count: number;
  supporting_count: number; // alias
  confidence: number;
  has_conflict: boolean;
  conflicting_review_ids: number[];
  conflicting_count: number; // alias
  is_model_generated: boolean;
  is_assumption: boolean;
  validation_status: string;
}

export interface Requirement {
  id: number;
  run_id: number;
  finding_id: number | null;
  requirement_text: string;
  title: string; // alias
  description: string;
  user_value: string;
  business_value: string;
  requirement_type: string;
  priority: string;
  version: string;
  status: string;
  estimated_effort: string;
  source_review_ids: number[];
  is_model_generated: boolean;
}

export interface TestCase {
  id: number;
  run_id: number;
  requirement_id: number | null;
  case_title: string;
  title: string; // alias
  case_description: string;
  description: string; // alias
  test_steps: string[];
  expected_result: string;
  test_type: string;
  priority: string;
  source_review_ids: number[];
  is_model_generated: boolean;
}

export interface AnalysisRun {
  id: number;
  app_id: string;
  app_name: string;
  analysis_goal: string;
  status: string;
  total_reviews: number;
  cleaned_reviews: number;
  started_at: string;
  completed_at: string;
  error_message?: string;
}

export interface AnalyzeRequest {
  app_url: string;
  analysis_goal: string;
  max_reviews?: number;
}

export interface AnalyzeResponse {
  status: string;
  run_id: number;
  app_id: string;
  app_name: string;
  message?: string;
}

export interface EvidenceSearchRequest {
  query: string;
  top_k?: number;
}

export interface EvidenceSearchResult {
  id: number | string;
  document: string;
  content: string;
  metadata: {
    review_id: string;
    app_id: string;
    rating: number;
    version: string;
    sentiment: number;
    language: string;
  };
  review?: {
    id: number;
    author: string;
    rating: number;
    title: string;
    version: string;
    date: string;
    content: string;
  };
  distance?: number;
}

export interface EvidenceValidateRequest {
  finding_text: string;
  topic?: string;
}

export interface EvidenceValidateResponse {
  finding_id: string;
  finding_text: string;
  topic: string;
  supporting_evidence: EvidenceSearchResult[];
  conflicting_evidence: EvidenceSearchResult[];
  support_count: number;
  conflict_count: number;
  confidence: number;
  has_conflict: boolean;
  is_assumption: boolean;
  validation_status: string;
}

export interface TraceabilityChain {
  findings: Finding[];
  requirements: Requirement[];
  test_cases: TestCase[];
  reviews_count: number;
  assumption_count: number;
  conflict_count: number;
}

export interface DashboardStats {
  total_runs: number;
  total_reviews: number;
  total_findings: number;
  total_requirements: number;
}

export interface ProgressEvent {
  run_id: number;
  stage: string;
  status: "started" | "in_progress" | "completed" | "failed";
  message: string;
  progress: number;
  data: Record<string, unknown>;
  timestamp: string;
}

export interface ProgressResponse {
  run_id: number;
  status: string;
  is_completed: boolean;
  events: ProgressEvent[];
  current_stage: string | null;
  progress: number;
}
