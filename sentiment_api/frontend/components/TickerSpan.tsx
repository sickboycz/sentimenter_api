"use client";

import React from "react";
import { useTickerDetail } from "../contexts/TickerDetailContext";

/** Renders a ticker symbol with hover tooltip (company name). Click opens Yahoo Finance–style detail modal. */
export function TickerSpan({
  symbol,
  name,
  children,
  className,
  onClick,
  ...rest
}: {
  symbol: string;
  name?: string | null;
  children?: React.ReactNode;
  className?: string;
  onClick?: (symbol: string, name?: string | null) => void;
  [key: string]: unknown;
}) {
  const ctx = useTickerDetail();
  const display = children ?? symbol;
  const title = name && name.trim() ? name : symbol;
  const openDetail = onClick ?? ctx?.openTickerDetail;
  const handleClick = openDetail && symbol ? () => openDetail(symbol, name) : undefined;

  return (
    <span
      role={handleClick ? "button" : undefined}
      tabIndex={handleClick ? 0 : undefined}
      className={[className, handleClick ? "cursor-pointer" : ""].filter(Boolean).join(" ")}
      title={handleClick ? `${title} — Click for details` : title}
      onClick={handleClick}
      onKeyDown={handleClick ? (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); handleClick(); } } : undefined}
      {...rest}
    >
      {display}
    </span>
  );
}
