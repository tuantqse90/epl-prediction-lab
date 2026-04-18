"use client";

import { useEffect, useRef, useState } from "react";
import { fetchChatHistory, fetchSuggestedPrompts, streamChat } from "@/lib/api";

type Message = { role: "user" | "assistant"; content: string };

export default function ChatWidget({ matchId }: { matchId: number }) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [streaming, setStreaming] = useState("");
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [prompts, setPrompts] = useState<string[]>([]);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetchSuggestedPrompts(matchId).then(setPrompts).catch(() => setPrompts([]));
    fetchChatHistory(matchId)
      .then((rows) => {
        // Drop the first user message (it carries the RAG data dump — noisy for the UI).
        const filtered = rows.filter((r, i) => !(i === 0 && r.role === "user"));
        setMessages(filtered.map((r) => ({ role: r.role as "user" | "assistant", content: r.content })));
      })
      .catch(() => void 0);
  }, [matchId]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, streaming]);

  async function send(question: string) {
    if (!question.trim() || busy) return;
    setBusy(true);
    setMessages((m) => [...m, { role: "user", content: question }]);
    setInput("");
    setStreaming("");

    let buffer = "";
    try {
      for await (const chunk of streamChat(matchId, question)) {
        buffer += chunk;
        setStreaming(buffer);
      }
      setMessages((m) => [...m, { role: "assistant", content: buffer }]);
    } catch (e) {
      setMessages((m) => [
        ...m,
        { role: "assistant", content: `[chat error: ${e instanceof Error ? e.message : e}]` },
      ]);
    } finally {
      setStreaming("");
      setBusy(false);
    }
  }

  return (
    <section className="card flex flex-col gap-3">
      <div className="flex items-baseline justify-between">
        <span className="label">&gt; chat // qwen-turbo</span>
        {busy && <span className="label text-neon">█ streaming…</span>}
      </div>

      <div
        ref={scrollRef}
        className="flex flex-col gap-3 max-h-80 overflow-y-auto font-mono text-sm"
      >
        {messages.length === 0 && !streaming && (
          <p className="text-muted">Hỏi gì đó về trận này — hoặc bấm gợi ý bên dưới.</p>
        )}
        {messages.map((m, i) => (
          <div key={i} className={m.role === "user" ? "text-neon" : "text-secondary"}>
            <span className="mr-2 text-muted">{m.role === "user" ? "&gt; mày:" : "&gt; tao:"}</span>
            <span className="whitespace-pre-wrap">{m.content}</span>
          </div>
        ))}
        {streaming && (
          <div className="text-secondary">
            <span className="mr-2 text-muted">&gt; tao:</span>
            <span className="whitespace-pre-wrap">{streaming}</span>
          </div>
        )}
      </div>

      {prompts.length > 0 && messages.length === 0 && (
        <div className="flex flex-wrap gap-2">
          {prompts.map((p) => (
            <button
              key={p}
              onClick={() => send(p)}
              className="btn-ghost rounded-full border border-border px-3 py-1 text-xs hover:border-neon"
              disabled={busy}
            >
              {p}
            </button>
          ))}
        </div>
      )}

      <form
        onSubmit={(e) => {
          e.preventDefault();
          send(input);
        }}
        className="flex gap-2"
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Hỏi tao đi…"
          disabled={busy}
          className="flex-1 rounded-full bg-high px-4 py-2 font-mono text-sm text-primary
                     placeholder:text-muted border border-border focus:border-neon
                     focus:outline-none disabled:opacity-50"
        />
        <button type="submit" disabled={busy || !input.trim()} className="btn-primary disabled:opacity-50">
          Send
        </button>
      </form>
    </section>
  );
}
