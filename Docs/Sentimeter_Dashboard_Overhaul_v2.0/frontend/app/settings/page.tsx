"use client";

import React, { useEffect, useState } from "react";
import { Shell } from "@/components/Shell";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";

export default function SettingsPage() {
  const [apiKey, setApiKey] = useState("");
  const [demo, setDemo] = useState(false);

  useEffect(() => {
    setApiKey(localStorage.getItem("SENTIMETER_API_KEY") || "");
    setDemo(localStorage.getItem("SENTIMETER_DEMO_MODE") === "1");
  }, []);

  const save = () => {
    localStorage.setItem("SENTIMETER_API_KEY", apiKey.trim());
    localStorage.setItem("SENTIMETER_DEMO_MODE", demo ? "1" : "0");
    window.location.reload();
  };

  return (
    <Shell>
      <Card title="Settings" subtitle="Local settings. No analytics. No key logging.">
        <div className="grid gap-3 max-w-xl">
          <label className="text-sm opacity-80">API Key</label>
          <input
            className="w-full px-3 py-2 rounded-xl bg-black/20 border border-white/10 outline-none"
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            placeholder="Paste your api_key"
            type="password"
          />

          <label className="flex items-center gap-2 text-sm opacity-80 mt-2">
            <input type="checkbox" checked={demo} onChange={(e) => setDemo(e.target.checked)} />
            Demo mode (use built-in fixtures)
          </label>

          <div className="flex gap-2 mt-2">
            <Button onClick={save}>Save</Button>
            <Button
              variant="ghost"
              onClick={() => {
                localStorage.removeItem("SENTIMETER_API_KEY");
                localStorage.removeItem("SENTIMETER_DEMO_MODE");
                window.location.reload();
              }}
            >
             Clear
            </Button>
          </div>

          <p className="text-xs opacity-70 mt-2">
            Stored in localStorage: <code className="kbd">SENTIMETER_API_KEY</code> and <code className="kbd">SENTIMETER_DEMO_MODE</code>.
          </p>
        </div>
      </Card>
    </Shell>
  );
}
