import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  BarChart3,
  Newspaper,
  LineChart,
  Factory,
  Building2,
  Sparkles,
  Layers,
  Shield,
  Activity,
  Settings
} from "lucide-react";

const items = [
  { href: "/", label: "Overview", icon: BarChart3 },
  { href: "/news", label: "News", icon: Newspaper },
  { href: "/markets", label: "Markets", icon: LineChart },
  { href: "/sectors", label: "Sectors", icon: Factory },
  { href: "/tickers", label: "Tickers", icon: Building2 },
  { href: "/topics", label: "Topics", icon: Sparkles },
  { href: "/research", label: "Research", icon: Layers },
  { href: "/ops", label: "Ops", icon: Activity },
  { href: "/sources", label: "Sources", icon: Shield },
  { href: "/settings", label: "Settings", icon: Settings }
];

export function Sidebar() {
  const pathname = usePathname();
  return (
    <aside className="w-56 hidden lg:flex flex-col p-3 gap-3">
      <div className="glass-strong p-3 flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl glass flex items-center justify-center">
          <span className="text-lg font-bold">S</span>
        </div>
        <div>
          <div className="font-display font-semibold leading-none">Sentimeter</div>
          <div className="text-xs opacity-70">Market Cognition</div>
        </div>
      </div>

      <nav className="glass p-2">
        {items.map(({ href, label, icon: Icon }) => {
          const active = pathname === href || (href !== "/" && pathname.startsWith(href));
          return (
            <Link
              key={href}
              href={href}
              className={`flex items-center gap-2 px-2.5 py-2 rounded-xl border transition ${
                active ? "bg-white/10 border-white/20" : "border-transparent hover:bg-white/5 hover:border-white/10"
              }`}
            >
              <Icon size={18} />
              <span className="text-sm">{label}</span>
            </Link>
          );
        })}
      </nav>

      <div className="glass p-3 text-xs opacity-80">
        <div className="font-semibold mb-2">Quick Filters</div>
        <div className="flex flex-wrap gap-2">
          <span className="px-2 py-1 rounded-lg border border-white/10 bg-white/5">L3+ only</span>
          <span className="px-2 py-1 rounded-lg border border-white/10 bg-white/5">RiskOff</span>
          <span className="px-2 py-1 rounded-lg border border-white/10 bg-white/5">Geopolitics</span>
        </div>
      </div>
    </aside>
  );
}
