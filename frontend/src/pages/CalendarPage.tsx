import { Calendar } from "lucide-react"

export default function CalendarPage() {
  return (
    <div className="flex h-full flex-col">
      <div className="flex h-14 items-center border-b px-6">
        <h1 className="text-lg font-semibold">Plan</h1>
      </div>
      <div className="flex flex-1 flex-col items-center justify-center gap-4 text-muted-foreground">
        <Calendar className="h-12 w-12" />
        <p className="text-sm">Step 2.4에서 구현됩니다</p>
        <p className="text-xs">Today Planner + Calendar View</p>
      </div>
    </div>
  )
}
