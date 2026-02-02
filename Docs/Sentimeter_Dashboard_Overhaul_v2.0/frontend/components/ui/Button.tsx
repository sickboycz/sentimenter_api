import React from "react";
import { cn } from "@/lib/cn";

export function Button({
  children,
  onClick,
  variant = "primary",
  type = "button",
  className = ""
}: {
  children: React.ReactNode;
  onClick?: () => void;
  variant?: "primary" | "ghost";
  type?: "button" | "submit";
  className?: string;
}) {
  const base = "px-3 py-2 rounded-xl border text-sm transition-colors";
  const cls =
    variant === "primary"
      ? `${base} bg-white/10 hover:bg-white/15 border-white/10`
      : `${base} bg-transparent hover:bg-white/10 border-white/10`;
  return (
    <button type={type} onClick={onClick} className={cn(cls, className)}>
      {children}
    </button>
  );
}
