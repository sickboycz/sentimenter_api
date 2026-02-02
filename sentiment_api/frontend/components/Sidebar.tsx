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
    <aside className="w-52 hidden lg:flex flex-col p-2.5 gap-2.5">
      <div className="glass-strong p-2.5 flex items-center gap-2">
        <div className="w-9 h-9 rounded-xl glass flex items-center justify-center">
          <span className="text-base font-bold">S</span>
        </div>
        <div>
          <div className="font-display font-semibold leading-none">Sentimeter</div>
          <div className="text-xs opacity-70">Market Cognition</div>
        </div>
      </div>

      <nav className="glass p-1.5">
        {items.map(({ href, label, icon: Icon }) => {
          const active = pathname === href || (href !== "/" && pathname.startsWith(href));
          return (
            <Link
              key={href}
              href={href}
              className={`flex items-center gap-2 px-2 py-1.5 rounded-xl border transition ${
                active ? "bg-white/10 border-white/20" : "border-transparent hover:bg-white/5 hover:border-white/10"
              }`}
            >
              <Icon size={16} />
              <span className="text-[13px]">{label}</span>
            </Link>
          );
        })}
      </nav>

      <div className="glass p-2.5 text-[11px] opacity-80">
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
