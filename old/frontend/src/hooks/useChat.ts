"use client";

import { useCallback, useRef, useState } from "react";
import { streamChat, type StreamEvent } from "@/lib/api-client";

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  safety?: {
    confidence: number;
    category: string;
    disclaimer?: string | null;
  } | null;
  streaming?: boolean;
}

export function useChat(module = "chat") {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const send = useCallback(
    async (content: string, model?: string | null) => {
      setError(null);
      setIsStreaming(true);
      const tempAssistantId = `pending-${Date.now()}`;
      setMessages((prev) => [
        ...prev,
        { id: `user-${Date.now()}`, role: "user", content },
        { id: tempAssistantId, role: "assistant", content: "", streaming: true },
      ]);

      abortRef.current = new AbortController();
      try {
        await streamChat(
          { content, conversation_id: conversationId, module, model },
          (event: StreamEvent) => {
            if (event.type === "meta") {
              setConversationId(event.data.conversation_id as string);
            } else if (event.type === "delta") {
              const text = event.data.text as string;
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === tempAssistantId ? { ...m, content: m.content + text } : m,
                ),
              );
            } else if (event.type === "done") {
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === tempAssistantId
                    ? {
                        ...m,
                        id: event.data.message_id as string,
                        safety: event.data.safety as ChatMessage["safety"],
                        streaming: false,
                      }
                    : m,
                ),
              );
            } else if (event.type === "error") {
              setError((event.data.message as string) ?? "Xatolik yuz berdi");
            }
          },
          abortRef.current.signal,
        );
      } catch (e) {
        if ((e as Error).name !== "AbortError") {
          setError((e as Error).message);
          setMessages((prev) => prev.filter((m) => m.id !== tempAssistantId));
        }
      } finally {
        setIsStreaming(false);
      }
    },
    [conversationId, module],
  );

  const stop = useCallback(() => abortRef.current?.abort(), []);

  const reset = useCallback(() => {
    setMessages([]);
    setConversationId(null);
    setError(null);
  }, []);

  return { messages, send, stop, reset, isStreaming, error, conversationId };
}
