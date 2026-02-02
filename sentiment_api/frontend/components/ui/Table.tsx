import React from "react";

export function Table({ children }: { children: React.ReactNode }) {
  return (
    <div className="overflow-auto rounded-xl border border-white/10">
      <table className="w-full text-sm">{children}</table>
    </div>
  );
}

export function THead({ children }: { children: React.ReactNode }) {
  return <thead className="bg-white/5 text-white/70">{children}</thead>;
}
export function TBody({ children }: { children: React.ReactNode }) {
  return <tbody className="divide-y divide-white/10">{children}</tbody>;
}
export function TR({ children, hover = true }: { children: React.ReactNode; hover?: boolean }) {
  return <tr className={hover ? "hover:bg-white/5" : ""}>{children}</tr>;
}
export function TH({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return <th className={`text-left font-medium px-3 py-2 ${className}`}>{children}</th>;
}
export function TD({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return <td className={`px-3 py-2 ${className}`}>{children}</td>;
}
