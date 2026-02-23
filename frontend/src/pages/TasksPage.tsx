import { useEffect, useState } from "react"
import { CheckCircle2, Clock, RotateCcw } from "lucide-react"
import { Button } from "@/components/ui/button"
import { apiGet, apiPost } from "@/lib/api"
import { cn } from "@/lib/utils"

interface Task {
  id: number
  title: string
  deadline_at: string | null
  est_minutes: number
  energy: number
  importance: number
  status: string
  next_action: string | null
  postpone_count: number
  priority_score: number | null
  created_at: string
}

interface TasksResponse {
  tasks: Task[]
  total: number
}

type StatusFilter = "pending" | "in_progress" | "done" | "all"

const statusFilters: { value: StatusFilter; label: string }[] = [
  { value: "all", label: "전체" },
  { value: "pending", label: "대기" },
  { value: "in_progress", label: "진행 중" },
  { value: "done", label: "완료" },
]

function formatDeadline(deadline: string | null): string {
  if (!deadline) return ""
  const d = new Date(deadline)
  const diffH = (d.getTime() - Date.now()) / (1000 * 60 * 60)
  if (diffH < 0) return "마감 지남"
  if (diffH < 24) return `${Math.round(diffH)}h`
  return `${Math.round(diffH / 24)}d`
}

function urgencyColor(deadline: string | null): string {
  if (!deadline) return ""
  const diffH =
    (new Date(deadline).getTime() - Date.now()) / (1000 * 60 * 60)
  if (diffH < 0) return "border-l-destructive"
  if (diffH < 24) return "border-l-red-500"
  if (diffH < 72) return "border-l-yellow-500"
  return "border-l-green-500"
}

export default function TasksPage() {
  const [tasks, setTasks] = useState<Task[]>([])
  const [filter, setFilter] = useState<StatusFilter>("pending")
  const [loading, setLoading] = useState(true)

  function fetchTasks() {
    setLoading(true)
    const query = filter === "all" ? "" : `?status=${filter}`
    apiGet<TasksResponse>(`/tasks${query}`)
      .then((data) => setTasks(data.tasks ?? []))
      .catch(() => setTasks([]))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    fetchTasks()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filter])

  async function handleComplete(taskId: number) {
    await apiPost(`/tasks/${taskId}/complete`)
    fetchTasks()
  }

  async function handlePostpone(taskId: number) {
    await apiPost(`/tasks/${taskId}/postpone`)
    fetchTasks()
  }

  return (
    <div className="flex h-full flex-col">
      <div className="flex h-14 items-center justify-between border-b px-6">
        <h1 className="text-lg font-semibold">Todo</h1>
      </div>

      {/* Filters */}
      <div className="flex gap-2 border-b px-6 py-2">
        {statusFilters.map((sf) => (
          <Button
            key={sf.value}
            variant={filter === sf.value ? "default" : "ghost"}
            size="sm"
            onClick={() => setFilter(sf.value)}
          >
            {sf.label}
          </Button>
        ))}
      </div>

      {/* Task List */}
      <div className="flex-1 overflow-auto p-6">
        {loading ? (
          <p className="text-sm text-muted-foreground">불러오는 중...</p>
        ) : tasks.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            {filter === "pending"
              ? "대기 중인 할 일이 없습니다."
              : "표시할 항목이 없습니다."}
          </p>
        ) : (
          <div className="space-y-3">
            {tasks.map((task) => (
              <div
                key={task.id}
                className={cn(
                  "flex items-start gap-4 rounded-lg border border-l-4 bg-card p-4",
                  urgencyColor(task.deadline_at),
                )}
              >
                <div className="flex-1 min-w-0">
                  <p className="font-medium">{task.title}</p>
                  {task.next_action && (
                    <p className="mt-1 text-sm text-muted-foreground">
                      다음: {task.next_action}
                    </p>
                  )}
                  <div className="mt-2 flex flex-wrap gap-3 text-xs text-muted-foreground">
                    {task.deadline_at && (
                      <span className="flex items-center gap-1">
                        <Clock className="h-3 w-3" />
                        {formatDeadline(task.deadline_at)}
                      </span>
                    )}
                    <span>예상 {task.est_minutes}분</span>
                    <span>중요도 {task.importance}/5</span>
                    <span>에너지 {task.energy}/5</span>
                    {task.postpone_count > 0 && (
                      <span className="text-yellow-600">
                        미루기 {task.postpone_count}회
                      </span>
                    )}
                  </div>
                </div>

                {task.status !== "done" && (
                  <div className="flex shrink-0 gap-1">
                    <Button
                      variant="ghost"
                      size="icon"
                      title="완료"
                      onClick={() => handleComplete(task.id)}
                    >
                      <CheckCircle2 className="h-5 w-5 text-green-600" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      title="미루기"
                      onClick={() => handlePostpone(task.id)}
                    >
                      <RotateCcw className="h-5 w-5 text-yellow-600" />
                    </Button>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
