"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef } from "react";
import { API_BASE, getDefaultApiKey } from "./api";

const RECONNECT_DELAY_MS = 3000;

/**
 * SSE hook: subscribes to /v1/stream/events, invalidates queries on mood/impacts/topics updates.
 * Auto-reconnect on disconnect. v1.2 spec.
 */
export function useSSE(enabled = true) {
  const queryClient = useQueryClient();
  const retryRef = useRef<number | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    if (!enabled || typeof window === "undefined") return;

    const apiKey = getDefaultApiKey();
    const url = `${API_BASE}/v1/stream/events${apiKey ? `?api_key=${encodeURIComponent(apiKey)}` : ""}`;

    function connect() {
      abortRef.current = new AbortController();
      fetch(url, {
        signal: abortRef.current.signal,
        headers: apiKey ? { "X-API-Key": apiKey } : undefined,
      })
        .then((res) => {
          if (!res.ok || !res.body) return;
          const reader = res.body.getReader();
          const decoder = new TextDecoder();
          let buf = "";

          function pump(): Promise<void> {
            return reader.read().then(({ done, value }) => {
              if (done) return;
              buf += decoder.decode(value, { stream: true });
              const lines = buf.split("\n\n");
              buf = lines.pop() ?? "";
              for (const block of lines) {
                if (!block.trim()) continue;
                const eventMatch = block.match(/event:\s*(\S+)/);
                const dataMatch = block.match(/data:\s*(.+)/s);
                const event = eventMatch?.[1];
                const dataStr = dataMatch?.[1]?.trim();
                if (!event || !dataStr) continue;
                try {
                  JSON.parse(dataStr);
                  if (event === "mood_updated") {
                    queryClient.invalidateQueries({ queryKey: ["moodNow"] });
                  } else if (event === "impacts_updated") {
                    queryClient.invalidateQueries({ queryKey: ["impactsLatest"] });
                  } else if (event === "topics_updated") {
                    queryClient.invalidateQueries({ queryKey: ["topicsIndex"] });
                  } else if (event === "cluster_updated") {
                    queryClient.invalidateQueries({ queryKey: ["newsClusters"] });
                  }
                } catch {
                  /* ignore parse errors */
                }
              }
              return pump();
            });
          }
          return pump();
        })
        .catch((err: unknown) => {
          if ((err as { name?: string })?.name === "AbortError") return;
          retryRef.current = window.setTimeout(() => connect(), RECONNECT_DELAY_MS);
        });
    }

    connect();
    return () => {
      if (retryRef.current != null) window.clearTimeout(retryRef.current);
      abortRef.current?.abort();
    };
  }, [enabled, queryClient]);
}
