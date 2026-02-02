import React from "react";

export function Card({
  title,
  subtitle,
  right,
  children,
}: {
  title?: string;
  subtitle?: string;
  right?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <div className="glass p-4">
      {(title || subtitle || right) && (
        <div className="flex items-start justify-between gap-3 mb-3">
          <div>
            {title && <div className="font-semibold">{title}</div>}
            {subtitle && <div className="text-sm opacity-70">{subtitle}</div>}
          </div>
          {right}
        </div>
      )}
      {children}
    </div>
  );
}
