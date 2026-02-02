"use client";

import React, { useEffect, useState } from "react";
import { Shell } from "../../components/Shell";
import { Card } from "../../components/ui/Card";
import { Button } from "../../components/ui/Button";

export default function SettingsPage() {
  const [key, setKey] = useState("");

  useEffect(() => {
    const k = localStorage.getItem("SENTIMETER_API_KEY") || "";
    setKey(k);
  }, []);

  const save = () => {
    localStorage.setItem("SENTIMETER_API_KEY", key.trim());
    alert("Saved API key to localStorage.");
  };

  const clear = () => {
    localStorage.removeItem("SENTIMETER_API_KEY");
    setKey("");
    alert("Cleared API key.");
  };

  return (
    <Shell>
      <Card title="Settings" subtitle="Local settings only. No analytics. No key logging.">
        <div className="grid gap-2 max-w-xl">
          <label className="text-sm opacity-80">API Key</label>
          <input
            className="w-full px-3 py-2 rounded-xl bg-black/20 border border-white/10 outline-none"
            placeholder="Paste api_key here"
            value={key}
            onChange={(e) => setKey(e.target.value)}
          />
          <div className="flex gap-2 mt-2">
            <Button onClick={save}>Save</Button>
            <Button variant="ghost" onClick={clear}>Clear</Button>
          </div>
          <p className="text-xs opacity-70 mt-3">
            Security: stored only in browser localStorage under key <code>SENTIMETER_API_KEY</code>.
            Never commit keys. Never log keys. No third-party analytics.
          </p>
        </div>
      </Card>
    </Shell>
  );
}
