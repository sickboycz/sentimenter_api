import React from "react";

export function Card({
  title,
  subtitle,
  right,
  children,
  className = ""
}: {
  title?: string;
  subtitle?: string;
  right?: React.ReactNode;
  children?: React.ReactNode;
  className?: string;
}) {
  return (
    <section className={`glass p-3 md:p-4 relative overflow-hidden ${className}`}>
      <div className="pointer-events-none absolute -top-24 -right-24 h-40 w-40 rounded-full bg-white/5 blur-3xl" />
      {(title || subtitle || right) && (
        <header className="flex items-start justify-between gap-3 mb-3">
          <div>
            {title && <div className="font-display text-sm md:text-base">{title}</div>}
            {subtitle && <div className="text-sm opacity-70">{subtitle}</div>}
          </div>
          {right}
        </header>
      )}
      {children}
    </section>
  );
}
