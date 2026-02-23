import { useState } from "react"
import { NavLink } from "react-router-dom"
import {
  Home,
  MessageSquare,
  CheckSquare,
  Calendar,
  Settings,
  PanelLeftClose,
  PanelLeftOpen,
} from "lucide-react"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"

const navItems = [
  { to: "/", icon: Home, label: "Home" },
  { to: "/chat", icon: MessageSquare, label: "Chat" },
  { to: "/tasks", icon: CheckSquare, label: "Todo" },
  { to: "/plan", icon: Calendar, label: "Plan" },
  { to: "/settings", icon: Settings, label: "Settings" },
]

export default function Sidebar() {
  const [collapsed, setCollapsed] = useState(false)

  return (
    <aside
      className={cn(
        "flex h-screen flex-col border-r bg-card transition-all duration-200",
        collapsed ? "w-[var(--sidebar-collapsed-width)]" : "w-[var(--sidebar-width)]",
      )}
    >
      <div className="flex h-14 items-center border-b px-3">
        {!collapsed && (
          <span className="text-lg font-semibold tracking-tight">
            The Agent
          </span>
        )}
        <Button
          variant="ghost"
          size="icon"
          className={cn("shrink-0", collapsed ? "mx-auto" : "ml-auto")}
          onClick={() => setCollapsed(!collapsed)}
        >
          {collapsed ? (
            <PanelLeftOpen className="h-5 w-5" />
          ) : (
            <PanelLeftClose className="h-5 w-5" />
          )}
        </Button>
      </div>

      <nav className="flex flex-1 flex-col gap-1 p-2">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === "/"}
            className={({ isActive }) =>
              cn(
                "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                "hover:bg-accent hover:text-accent-foreground",
                isActive
                  ? "bg-accent text-accent-foreground"
                  : "text-muted-foreground",
                collapsed && "justify-center px-2",
              )
            }
          >
            <item.icon className="h-5 w-5 shrink-0" />
            {!collapsed && <span>{item.label}</span>}
          </NavLink>
        ))}
      </nav>
    </aside>
  )
}
