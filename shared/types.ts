// TypeScript types mirroring Pydantic models
// See client/src/lib/api.ts for the client-side types used in React components

export interface AnalysisRequest {
  url: string;
}

export interface LeadRequest {
  name: string;
  email: string;
  dealership: string;
  phone?: string;
  analysis_url?: string;
  score?: number;
}
