import { useEffect, useRef, useState } from "react";

const SESSION_ID = `web-${Math.random().toString(36).slice(2, 10)}`;

export default function App() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [uploadStatus, setUploadStatus] = useState(null);
  const bottomRef = useRef(null);
  const fileInputRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  async function sendQuestion() {
    const question = input.trim();
    if (!question || loading) return;

    setInput("");
    setError(null);
    setMessages((prev) => [...prev, { role: "user", content: question }]);
    setLoading(true);

    try {
      const started = performance.now();
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question, session_id: SESSION_ID }),
      });
      if (!res.ok) throw new Error(`Server returned ${res.status}`);
      const data = await res.json();
      const elapsedMs = Math.round(performance.now() - started);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: data.answer,
          sources: data.sources,
          cached: data.cached,
          elapsedMs,
        },
      ]);
    } catch (err) {
      setError(
        "Couldn't reach the query service. Check that the containers are running."
      );
      console.error(err);
    } finally {
      setLoading(false);
    }
  }

  async function uploadDocument(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    e.target.value = ""; // allow re-selecting the same file later

    setUploadStatus({ state: "working", text: `Indexing ${file.name}…` });
    const form = new FormData();
    form.append("file", file);

    try {
      const res = await fetch("/ingest/upload", { method: "POST", body: form });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || `Server returned ${res.status}`);
      setUploadStatus({
        state: "done",
        text: `${data.filename} indexed — ${data.chunks_stored} chunks. Ask away!`,
      });
    } catch (err) {
      setUploadStatus({ state: "error", text: `Upload failed: ${err.message}` });
    }
  }

  function handleKeyDown(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendQuestion();
    }
  }

  return (
    <div className="shell">
      <header className="masthead">
        <div className="masthead-row">
          <div>
            <h1>NovaBot</h1>
            <p>Ask questions about your indexed documents</p>
          </div>
          <button
            className="upload-btn"
            onClick={() => fileInputRef.current?.click()}
          >
            Upload document
          </button>
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,.txt,.md"
            onChange={uploadDocument}
            hidden
          />
        </div>
        {uploadStatus && (
          <div className={`upload-status ${uploadStatus.state}`}>
            {uploadStatus.text}
          </div>
        )}
      </header>

      <main className="thread">
        {messages.length === 0 && !loading && (
          <div className="empty">
            <p>Your documents are indexed and ready.</p>
            <p className="hint">
              Upload a PDF above, or try:{" "}
              <em>"What experience does this person have with Kafka?"</em>
            </p>
          </div>
        )}

        {messages.map((msg, i) => (
          <div key={i} className={`turn ${msg.role}`}>
            <div className="bubble">
              <p>{msg.content}</p>
              {msg.sources && msg.sources.length > 0 && (
                <div className="sources">
                  {msg.sources.map((s, j) => (
                    <span key={j} className="source-chip">
                      {s.source} · {s.similarity}
                    </span>
                  ))}
                </div>
              )}
              {msg.role === "assistant" && msg.elapsedMs != null && (
                <div className="meta">
                  <span className={`time-chip ${msg.cached ? "hit" : ""}`}>
                    {msg.cached ? "⚡ cached · " : ""}
                    {msg.elapsedMs >= 1000
                      ? (msg.elapsedMs / 1000).toFixed(1) + "s"
                      : msg.elapsedMs + "ms"}
                  </span>
                </div>
              )}
            </div>
          </div>
        ))}

        {loading && (
          <div className="turn assistant">
            <div className="bubble thinking">
              <span className="dot" />
              <span className="dot" />
              <span className="dot" />
            </div>
          </div>
        )}

        {error && <div className="error">{error}</div>}
        <div ref={bottomRef} />
      </main>

      <footer className="composer">
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask a question…"
          rows={1}
          disabled={loading}
        />
        <button onClick={sendQuestion} disabled={loading || !input.trim()}>
          Ask
        </button>
      </footer>
    </div>
  );
}
