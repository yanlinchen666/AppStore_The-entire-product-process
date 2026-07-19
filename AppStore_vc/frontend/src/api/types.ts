export interface Review {
  id: number;
  title: string;
  body: string;
  rating: number;
  author: string;
  version: string;
  date: string;
  sentiment: string;
}

export interface Topic {
  id: number;
  name: string;
  description: string;
  priority: string;
}

export interface Finding {
  id: number;
  topic_id: number;
  description: string;
  confidence: number;
  supporting_count: number;
  conflicting_count: number;
}

export interface Requirement {
  id: number;
  finding_id: number;
  title: string;
  description: string;
  priority: string;
  version: string;
}

export interface TestCase {
  id: number;
  requirement_id: number;
  title: string;
  description: string;
  expected_result: string;
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
}

export interface AnalyzeRequest {
  app_url: string;
  analysis_goal: string;
  max_reviews?: number;
}

export interface AnalyzeResponse {
  run_id: number;
  status: string;
  message: string;
}

export interface EvidenceSearchRequest {
  query: string;
  top_k?: number;
}

export interface EvidenceSearchResult {
  id: number;
  content: string;
  score: number;
  sentiment: string;
}

export interface EvidenceValidateRequest {
  finding_id: number;
}

export interface EvidenceValidateResponse {
  finding_id: number;
  supporting_evidence: EvidenceSearchResult[];
  conflicting_evidence: EvidenceSearchResult[];
  confidence: number;
}

export interface TraceabilityChain {
  review: Review;
  findings: Finding[];
  requirements: Requirement[];
  test_cases: TestCase[];
}

export interface DashboardStats {
  total_runs: number;
  total_reviews: number;
  total_findings: number;
  total_requirements: number;
}
