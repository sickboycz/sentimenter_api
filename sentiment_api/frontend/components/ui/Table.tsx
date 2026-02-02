import React from "react";

export function Table({ children }: { children: React.ReactNode }) {
  return (
    <div className="overflow-auto rounded-xl border border-white/10 bg-white/[0.02]">
      <table className="w-full text-sm">{children}</table>
    </div>
  );
}

export function THead({ children }: { children: React.ReactNode }) {
  return <thead className="bg-white/5 text-white/70 sticky top-0">{children}</thead>;
}
export function TBody({ children }: { children: React.ReactNode }) {
  return <tbody className="divide-y divide-white/10">{children}</tbody>;
}
export function TR({ children, hover = true }: { children: React.ReactNode; hover?: boolean }) {
  const base = "odd:bg-white/[0.02]";
  const hoverCls = hover ? "hover:bg-white/[0.06]" : "";
  return <tr className={`${base} ${hoverCls}`}>{children}</tr>;
}
export function TH({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return <th className={`text-left font-medium px-3 py-2 text-[11px] uppercase tracking-wider ${className}`}>{children}</th>;
}
export function TD({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return <td className={`px-3 py-2 ${className}`}>{children}</td>;
}
