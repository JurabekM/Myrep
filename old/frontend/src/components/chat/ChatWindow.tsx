"use client";

import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeHighlight from "rehype-highlight";
import { Send, Square, ShieldCheck, AlertTriangle } from "lucide-react";
import { useChat, type ChatMessage } from "@/hooks/useChat";

function ConfidenceBadge({ safety }: { safety: NonNullable<ChatMessage["safety"]> }) {
  const pct = Math.round(safety.confidence * 100);
  const ok = safety.confidence >= 0.6;
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs ${
        ok
          ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300"
          : "bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300"
      }`}
      title={`Kategoriya: ${safety.category}`}
    >
      {ok ? <ShieldCheck size={12} /> : <AlertTriangle size={12} />}
      Ishonch: {pct}%
    </span>
  );
}

function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === "user";
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[85%] rounded-2xl px-4 py-3 ${
          isUser
            ? "bg-primary text-primary-foreground"
            : "bg-muted text-foreground"
        }`}
      >
        {isUser ? (
          <p className="whitespace-pre-wrap">{message.content}</p>
        ) : (
          <div className="prose prose-sm dark:prose-invert max-w-none">
            <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeHighlight]}>
              {message.content || (message.streaming ? "…" : "")}
            </ReactMarkdown>
            {message.safety && !message.streaming && (
              <div className="mt-2 not-prose">
                <ConfidenceBadge safety={message.safety} />
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export function ChatWindow({ module = "chat" }: { module?: string }) {
  const { messages, send, stop, isStreaming, error } = useChat(module);
  const [input, setInput] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = input.trim();
    if (!trimmed || isStreaming) return;
    setInput("");
    void send(trimmed);
  };

  return (
    <div className="flex h-full flex-col">
      <div className="flex-1 space-y-4 overflow-y-auto p-4">
        {messages.length === 0 && (
          <div className="flex h-full items-center justify-center text-muted-foreground">
            <p>Biznesingiz haqida savol bering — strategiya, soliq, marketing, huquq…</p>
          </div>
        )}
        {messages.map((m) => (
          <MessageBubble key={m.id} message={m} />
        ))}
        {error && (
          <p className="rounded-lg bg-destructive/10 p-3 text-sm text-destructive">{error}</p>
        )}
        <div ref={bottomRef} />
      </div>

      <form onSubmit={handleSubmit} className="border-t p-4">
        <div className="flex items-end gap-2">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleSubmit(e);
              }
            }}
            rows={2}
            placeholder="Savolingizni yozing… (Enter — yuborish, Shift+Enter — yangi qator)"
            className="flex-1 resize-none rounded-xl border bg-background px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
            aria-label="Xabar matni"
          />
          {isStreaming ? (
            <button
              type="button"
              onClick={stop}
              className="rounded-xl bg-destructive p-3 text-destructive-foreground"
              aria-label="To'xtatish"
            >
              <Square size={18} />
            </button>
          ) : (
            <button
              type="submit"
              disabled={!input.trim()}
              className="rounded-xl bg-primary p-3 text-primary-foreground disabled:opacity-50"
              aria-label="Yuborish"
            >
              <Send size={18} />
            </button>
          )}
        </div>
      </form>
    </div>
  );
}
