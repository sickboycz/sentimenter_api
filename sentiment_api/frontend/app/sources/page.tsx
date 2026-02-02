"use client";

import React from "react";
import { useQuery } from "@tanstack/react-query";
import { Shell } from "../../components/Shell";
import { apiGet, getDefaultApiKey } from "../../lib/api";

export default function SourcesPage() {
  const apiKey = getDefaultApiKey();

  const sources = useQuery({
    queryKey: ["sources"],
    queryFn: () => apiGet<any>("/v1/sources?enabled_only=false", apiKey),
  });

  const list = sources.data?.data ?? [];

  return (
    <Shell>
      <div className="glass p-4">
        <div className="font-semibold">Sources</div>
        <div className="text-sm opacity-75">
          Source registry: enabled sources with credibility tier and license class.
        </div>
      </div>

      <div className="glass p-4 overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left opacity-80 border-b border-white/10">
              <th className="py-2 pr-4">source_id</th>
              <th className="py-2 pr-4">name</th>
              <th className="py-2 pr-4">type</th>
              <th className="py-2 pr-4">credibility_tier</th>
              <th className="py-2 pr-4">license_class</th>
            </tr>
          </thead>
          <tbody>
            {list.map((s: any) => (
              <tr key={s.source_id} className="border-b border-white/5">
                <td className="py-2 pr-4 font-mono text-xs">{s.source_id}</td>
                <td className="py-2 pr-4">{s.name}</td>
                <td className="py-2 pr-4">{s.type}</td>
                <td className="py-2 pr-4">{s.credibility_tier}</td>
                <td className="py-2 pr-4">{s.license_class}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Shell>
  );
}
