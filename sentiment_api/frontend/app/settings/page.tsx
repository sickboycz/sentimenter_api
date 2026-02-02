"use client";

import React, { useState, useEffect } from "react";
import { Shell } from "../../components/Shell";
import { useQueryClient } from "@tanstack/react-query";

const API_KEY_STORAGE = "sentiment_api_key";

export default function SettingsPage() {
  const queryClient = useQueryClient();
  const [apiKey, setApiKey] = useState("");
  const [reveal, setReveal] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (typeof window !== "undefined") {
      setApiKey(localStorage.getItem(API_KEY_STORAGE) ?? "");
    }
  }, []);

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    if (typeof window !== "undefined") {
      if (apiKey.trim()) {
        localStorage.setItem(API_KEY_STORAGE, apiKey.trim());
      } else {
        localStorage.removeItem(API_KEY_STORAGE);
      }
      queryClient.invalidateQueries();
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    }
  };

  return (
    <Shell>
      <div className="glass p-4">
        <div className="font-semibold">Settings</div>
        <div className="text-sm opacity-75">API key and preferences.</div>
      </div>

      <form onSubmit={handleSave} className="glass p-4 space-y-4 max-w-lg">
        <div>
          <label htmlFor="settings-api-key" className="block font-medium mb-2">
            API Key
          </label>
          <p className="text-sm opacity-75 mb-3">
            Used for authenticated endpoints (mood, impacts, news, research, etc.). Store locally; never sent to our servers except to the API.
          </p>
          <div className="flex gap-2 items-center">
            <input
              id="settings-api-key"
              type={reveal ? "text" : "password"}
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder="Enter API key"
              autoComplete="off"
              className="flex-1 px-3 py-2 rounded-lg bg-black/20 border border-white/10 outline-none text-sm focus:border-white/20"
            />
            <button
              type="button"
              onClick={() => setReveal(!reveal)}
              className="text-xs opacity-70 hover:opacity-100 px-2 py-1"
            >
              {reveal ? "Hide" : "Show"}
            </button>
          </div>
        </div>
        <div className="flex gap-3">
          <button
            type="submit"
            className="px-4 py-2 rounded-lg bg-white/10 hover:bg-white/15 text-sm font-medium"
          >
            Save
          </button>
          {saved && (
            <span className="text-sm text-[var(--good)] py-2">Saved.</span>
          )}
        </div>
      </form>
    </Shell>
  );
}
