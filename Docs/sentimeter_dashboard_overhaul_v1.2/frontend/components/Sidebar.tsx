import Link from "next/link";
import {
  BarChart3,
  Newspaper,
  Layers,
  Activity,
  Shield,
  Building2,
  Factory,
  LineChart,
  Settings,
  Sparkles,
} from "lucide-react";

const items = [
  { href: "/", label: "Overview", icon: BarChart3 },
  { href: "/news", label: "News Feed", icon: Newspaper },
  { href: "/markets", label: "Markets", icon: LineChart },
  { href: "/sectors", label: "Sectors", icon: Factory },
  { href: "/tickers", label: "Tickers", icon: Building2 },
  { href: "/topics", label: "Topics", icon: Sparkles },
  { href: "/research", label: "Research", icon: Layers },
  { href: "/sources", label: "Sources", icon: Shield },
  { href: "/ops", label: "Ops", icon: Activity },
  { href: "/settings", label: "Settings", icon: Settings },
];

export function Sidebar() {
  return (
    <aside className="w-64 hidden md:flex flex-col p-4 gap-3">
      <div className="glass p-3 flex items-center gap-2">
        <div className="w-9 h-9 rounded-xl glass flex items-center justify-center">
          <span className="text-lg font-bold">S</span>
        </div>
        <div>
          <div className="font-semibold">Sentimeter</div>
          <div className="text-xs opacity-70">Market Cognition</div>
        </div>
      </div>

      <nav className="glass p-2">
        {items.map(({ href, label, icon: Icon }) => (
          <Link
            key={href}
            href={href}
            className="flex items-center gap-2 px-3 py-2 rounded-xl hover:bg-white/5"
          >
            <Icon size={18} />
            <span className="text-sm">{label}</span>
          </Link>
        ))}
      </nav>

      <div className="glass p-3 text-xs opacity-80">
        <div className="font-semibold mb-2">Quick</div>
        <div>• L3+ only</div>
        <div>• RiskOff drivers</div>
        <div>• Geopolitics</div>
      </div>
    </aside>
  );
}
