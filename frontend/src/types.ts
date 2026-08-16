export type Source = { chunk_id: string; specification: string; release?: string; section?: string; section_title?: string; page?: number; source: string; source_url?: string; excerpt: string; score?: number };
export type Debug = { dense_candidates: number; bm25_candidates: number; fused_candidates: number; reranked_candidates: number; evidence_accepted: boolean; reason?: string };
export type ChatResponse = { answer: string; grounded: boolean; confidence: "high" | "medium" | "low" | "insufficient"; sources: Source[]; debug?: Debug };
