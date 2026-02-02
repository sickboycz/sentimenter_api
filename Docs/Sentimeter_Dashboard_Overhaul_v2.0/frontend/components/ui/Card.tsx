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
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <section className={`glass p-4 ${className}`}>
      {(title || subtitle || right) && (
        <header className="flex items-start justify-between gap-3 mb-3">
          <div>
            {title && <div className="font-semibold">{title}</div>}
            {subtitle && <div className="text-sm opacity-70">{subtitle}</div>}
          </div>
          {right}
        </header>
      )}
      {children}
    </section>
  );
}
