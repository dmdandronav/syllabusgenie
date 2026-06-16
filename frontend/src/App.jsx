import React, { useState, useRef, useEffect } from "react";

const APP_NAME = "SyllabusGenie";
const TAGLINE = "Ask your class, not the internet.";

export default function App() {
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      content:
        "Hi — I'm a starter template for your hackathon project. Ask me anything, or drop a .txt/.md file in the backend's /data folder and I'll use it to answer questions (lightweight RAG).",
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [sources, setSources] = useState([]);
  const scrollRef = useRef(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, loading]);

  async function sendMessage(e) {
    e.preventDefault();
    const text = input.trim();
    if (!text || loading) return;

    const next = [...messages, { role: "user", content: text }];
    setMessages(next);
    setInput("");
    setLoading(true);
    setSources([]);

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ messages: next }),
      });
      const data = await res.json();
      if (data.error) throw new Error(data.error);
      setMessages([...next, { role: "assistant", content: data.reply }]);
      setSources(data.sources || []);
    } catch (err) {
      setMessages([
        ...next,
        {
          role: "assistant",
          content:
            "Hmm, I couldn't reach the backend. Make sure the Flask server is running on port 5000 and your API key is set in backend/.env.",
        },
      ]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex flex-col">
      <header className="border-b border-[var(--color-line)] px-6 py-5">
        <h1 className="font-[var(--font-display)] text-2xl text-[var(--color-pine)]">
          {APP_NAME}
        </h1>
        <p className="text-sm text-[var(--color-ink)]/60">{TAGLINE}</p>
      </header>

      <main
        ref={scrollRef}
        className="flex-1 overflow-y-auto px-6 py-6 space-y-4 max-w-2xl w-full mx-auto"
      >
        {messages.map((m, i) => (
          <div
            key={i}
            className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}
          >
            <div
              className={`max-w-[80%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                m.role === "user"
                  ? "bg-[var(--color-pine)] text-[var(--color-paper)]"
                  : "bg-white border border-[var(--color-line)]"
              }`}
            >
              {m.content}
            </div>
          </div>
        ))}

        {loading && (
          <div className="flex items-center gap-2 text-[var(--color-pine)]/70 text-sm pl-1">
            <span className="w-2 h-2 rounded-full bg-[var(--color-clay)] pulse-soft" />
            thinking…
          </div>
        )}

        {sources.length > 0 && (
          <div className="text-xs text-[var(--color-ink)]/50 pl-1">
            Sources: {sources.join(", ")}
          </div>
        )}
      </main>

      <form
        onSubmit={sendMessage}
        className="border-t border-[var(--color-line)] px-6 py-4 max-w-2xl w-full mx-auto flex gap-3"
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Type a message…"
          className="flex-1 rounded-xl border border-[var(--color-line)] bg-white px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--color-pine-light)]"
        />
        <button
          type="submit"
          disabled={loading}
          className="rounded-xl bg-[var(--color-clay)] text-white px-5 py-2 text-sm font-medium disabled:opacity-50"
        >
          Send
        </button>
      </form>
    </div>
  );
}
