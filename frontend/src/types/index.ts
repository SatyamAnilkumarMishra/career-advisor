export interface SourceItem {
  content: string;
  page?: number | null;
  relevance_score: number;
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  sources?: SourceItem[];
  timestamp?: string;
}

export interface StatusResponse {
  status: string;
  model: string;
  has_job_api: boolean;
  document_loaded: boolean;
  document_name?: string | null;
}

export interface ResumeUploadResponse {
  filename: string;
  text: string;
  size_bytes: number;
}

export interface ResumeAnalysis {
  extracted_skills: string[];
  experience_summary: string;
  strengths: string[];
  gaps_or_improvements: string[];
  suggested_target_roles: string[];
}

export interface SkillGapResult {
  matched_skills: string[];
  missing_skills: string[];
  partially_met_skills: string[];
  overall_readiness: 'low' | 'medium' | 'high' | string;
  summary: string;
}

export interface RoadmapMilestone {
  title: string;
  duration: string;
  focus_skills: string[];
  actions: string[];
}

export interface RoadmapResult {
  target_role: string;
  milestones: RoadmapMilestone[];
  summary: string;
}

export interface JobListing {
  title: string;
  company: string;
  location: string;
  url: string;
  description: string;
  skills: string[];
  experience_level?: string | null;
  source: string;
}

export interface HistoryItem {
  id: string;
  query: string;
  timestamp: string;
  pinned?: boolean;
  archived?: boolean;
}

export type ActiveView = 'chat' | 'resume' | 'skillgap' | 'roadmap' | 'jobs';
