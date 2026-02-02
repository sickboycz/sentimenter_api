"use client";

import React, { useState, useEffect } from "react";
import { useQueryClient } from "@tanstack/react-query";

const API_KEY_STORAGE = "sentiment_api_key";

export function Topbar() {
  const queryClient = useQueryClient();
  const [apiKey, setApiKeyState] = useState("");
  const [reveal, setReveal] = useState(false);

  useEffect(() => {
    if (typeof window !== "undefined") {
      setApiKeyState(localStorage.getItem(API_KEY_STORAGE) ?? "");
    }
  }, []);

  const handleKeyChange = (v: string) => {
    setApiKeyState(v);
    if (typeof window !== "undefined") {
      if (v) localStorage.setItem(API_KEY_STORAGE, v);
      else localStorage.removeItem(API_KEY_STORAGE);
    }
  };

  const handleApply = () => {
    queryClient.invalidateQueries();
  };

  return (
    <div className="glass p-3 flex items-center gap-3 flex-wrap">
      <div className="font-semibold">Sentimeter Dashboard</div>
      <div className="flex-1" />
      <form
        className="flex items-center gap-2 text-sm opacity-80"
        onSubmit={(e) => {
          e.preventDefault();
          handleApply();
        }}
      >
        <label htmlFor="topbar-api-key">API Key</label>
        <input
          id="topbar-api-key"
          type={reveal ? "text" : "password"}
          value={apiKey}
          onChange={(e) => handleKeyChange(e.target.value)}
          placeholder="Set for authenticated endpoints"
          autoComplete="off"
          className="w-48 px-3 py-1.5 rounded-lg bg-black/20 border border-white/10 outline-none text-sm"
        />
        <button
          type="button"
          onClick={() => setReveal(!reveal)}
          className="text-xs opacity-70 hover:opacity-100"
        >
          {reveal ? "Hide" : "Show"}
        </button>
        <button
          type="submit"
          className="px-2 py-1.5 rounded-lg bg-white/10 hover:bg-white/15 text-xs"
        >
          Apply
        </button>
      </form>
    </div>
  );
}
