import { FormEvent, useState } from "react";
import type { ChatResponse, Source } from "./types";

const examples = ["What is the purpose of the Registration Request?", "What is the role of AMF in the 5G architecture?", "What is PDU Session Establishment?", "What is the role of RRC in NR?"];

function SourceCard({ source }: { source: Source }) {
  const content = <><strong>{source.specification}</strong><span>{source.section ? `Section ${source.section}` : "Section unavailable"}{source.page ? ` · Page ${source.page}` : ""}</span><p>{source.excerpt}</p></>;
  return source.source_url ? <a className="source-card" href={source.source_url} target="_blank" rel="noreferrer">{content}<small>View official source ↗</small></a> : <div className="source-card">{content}</div>;
}

export default function App() {
  const [question, setQuestion] = useState("");
  const [showDebug, setShowDebug] = useState(false);
  const [result, setResult] = useState<ChatResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function ask(event?: FormEvent) {
    event?.preventDefault();
    if (!question.trim() || loading) return;
    setLoading(true); setError(""); setResult(null);
    try {
      const response = await fetch("/api/chat", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ question, include_debug: showDebug }) });
      const body = await response.text();
      let data: ChatResponse | { detail?: string };
      try { data = JSON.parse(body); }
      catch { throw new Error(`The backend returned an empty or invalid response (HTTP ${response.status}). Check the backend terminal.`); }
      if (!response.ok) throw new Error(("detail" in data && data.detail) || "The assistant could not process the question.");
      setResult(data as ChatResponse);
    } catch (caught) { setError(caught instanceof Error ? caught.message : "Network error. Check that the backend is running."); }
    finally { setLoading(false); }
  }

  return <main>
    <nav><div className="brand-mark">3G</div><div><strong>3GPP Standards Assistant</strong><span>Citation-grounded technical retrieval</span></div><div className="status"><i /> Evidence-first</div></nav>
    <section className="hero"><p className="eyebrow">3GPP KNOWLEDGE RETRIEVAL</p><h1>Answers you can trace back to the standard.</h1><p>Search your indexed 3GPP specifications with hybrid retrieval, evidence thresholds, and source-bound citations.</p></section>
    <section className="workspace">
      <form onSubmit={ask} className="ask-box"><label htmlFor="question">Ask about an indexed specification</label><textarea id="question" value={question} onChange={(event) => setQuestion(event.target.value)} placeholder="e.g. What is the purpose of the Registration Request?" rows={3} maxLength={1000} /><div className="form-footer"><label className="toggle"><input type="checkbox" checked={showDebug} onChange={(event) => setShowDebug(event.target.checked)} /> Show retrieval details</label><button disabled={!question.trim() || loading}>{loading ? "Retrieving evidence…" : "Ask assistant"}</button></div></form>
      {!result && !loading && !error && <div className="empty"><h2>Start with a focused question</h2><p>The assistant only answers from documents you have indexed. Try one of these:</p><div className="examples">{examples.map(example => <button key={example} onClick={() => setQuestion(example)}>{example}</button>)}</div></div>}
      {loading && <div className="loading"><span className="spinner" />Searching dense and keyword indexes, then validating evidence…</div>}
      {error && <div className="error"><strong>Couldn’t complete the request.</strong><span>{error}</span></div>}
      {result && <article className="answer"><header><div><p className="eyebrow">ANSWER</p><span className={`badge ${result.confidence}`}>{result.confidence === "insufficient" ? "Insufficient evidence" : `${result.confidence} evidence confidence`}</span></div>{result.grounded && <span className="grounded">Grounded response</span>}</header><div className="answer-text">{result.answer}</div><section className="sources"><h2>Retrieved sources <small>{result.sources.length} evidence chunk{result.sources.length === 1 ? "" : "s"}</small></h2><div className="source-grid">{result.sources.map(source => <SourceCard key={source.chunk_id} source={source} />)}</div></section>{result.debug && <details className="debug"><summary>Retrieval details</summary><div><span>Dense {result.debug.dense_candidates}</span><span>BM25 {result.debug.bm25_candidates}</span><span>Fused {result.debug.fused_candidates}</span><span>Reranked {result.debug.reranked_candidates}</span></div>{result.debug.reason && <p>{result.debug.reason}</p>}</details>}</article>}
    </section>
    <footer>Designed to minimize unsupported claims through retrieval validation, reranking, evidence thresholds, citation enforcement, and abstention.</footer>
  </main>;
}
