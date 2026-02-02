import React from "react";
import { cn } from "@/lib/cn";

export function Button({
  children,
  onClick,
  variant = "primary",
  type = "button",
  className = "",
  disabled = false
}: {
  children: React.ReactNode;
  onClick?: () => void;
  variant?: "primary" | "ghost";
  type?: "button" | "submit";
  className?: string;
  disabled?: boolean;
}) {
  const base = "px-2.5 py-1.5 rounded-xl border text-sm font-medium transition-all";
  const cls =
    variant === "primary"
      ? `${base} bg-white/10 hover:bg-white/15 border-white/20 shadow-sm`
      : `${base} bg-transparent hover:bg-white/10 border-white/10`;
  const disabledCls = disabled ? "opacity-60 cursor-not-allowed pointer-events-none" : "";
  return (
    <button type={type} onClick={onClick} className={cn(cls, disabledCls, className)} disabled={disabled}>
      {children}
    </button>
  );
}
