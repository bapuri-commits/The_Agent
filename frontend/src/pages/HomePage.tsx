import { useEffect, useState } from "react"
import { useNavigate } from "react-router-dom"
import { Calendar, CheckSquare, Clock } from "lucide-react"
import ChatInput from "@/components/ChatInput"
import { apiGet } from "@/lib/api"
import { cn } from "@/lib/utils"

interface Task {
  id: number
  title: string
  deadline_at: string | null
  est_minutes: number
  importance: number
  status: string
  priority_score: number | null
  postpone_count: number
}

interface TasksResponse {
  tasks: Task[]
  total: number
}

function formatDeadline(deadline: string | null): string {
  if (!deadline) return "마감 없음"
  const d = new Date(deadline)
  const now = new Date()
  const diffH = (d.getTime() - now.getTime()) / (1000 * 60 * 60)
  if (diffH < 0) return "마감 지남"
  if (diffH < 24) return `${Math.round(diffH)}시간 남음`
  return `${Math.round(diffH / 24)}일 남음`
}

function urgencyColor(deadline: string | null): string {
  if (!deadline) return "text-muted-foreground"
  const diffH =
    (new Date(deadline).getTime() - Date.now()) / (1000 * 60 * 60)
  if (diffH < 0) return "text-destructive font-semibold"
  if (diffH < 24) return "text-red-500"
  if (diffH < 72) return "text-yellow-600"
  return "text-muted-foreground"
}

export default function HomePage() {
  const navigate = useNavigate()
  const [tasks, setTasks] = useState<Task[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    apiGet<TasksResponse>("/tasks?status=pending&limit=5")
      .then((data) => setTasks(data.tasks ?? []))
      .catch(() => setTasks([]))
      .finally(() => setLoading(false))
  }, [])

  function handleSend(message: string) {
    navigate("/chat", { state: { initialMessage: message } })
  }

  return (
    <div className="flex h-full flex-col">
      {/* Dashboard Content */}
      <div className="flex-1 overflow-auto p-6">
        <h1 className="mb-6 text-2xl font-bold">Good morning</h1>

        <div className="grid gap-6 md:grid-cols-2">
          {/* Today Schedule (placeholder — Step 2.4에서 실제 데이터 연결) */}
          <div className="rounded-lg border bg-card p-4">
            <div className="mb-3 flex items-center gap-2">
              <Calendar className="h-5 w-5 text-primary" />
              <h2 className="font-semibold">오늘의 일정</h2>
            </div>
            <div className="space-y-2 text-sm text-muted-foreground">
              <p className="flex items-center gap-2">
                <Clock className="h-4 w-4" />
                플랜을 생성하면 여기에 표시됩니다
              </p>
            </div>
          </div>

          {/* TODO List */}
          <div className="rounded-lg border bg-card p-4">
            <div className="mb-3 flex items-center gap-2">
              <CheckSquare className="h-5 w-5 text-primary" />
              <h2 className="font-semibold">할 일</h2>
              {tasks.length > 0 && (
                <span className="ml-auto text-xs text-muted-foreground">
                  {tasks.length}개
                </span>
              )}
            </div>

            {loading ? (
              <p className="text-sm text-muted-foreground">불러오는 중...</p>
            ) : tasks.length === 0 ? (
              <p className="text-sm text-muted-foreground">
                할 일이 없습니다. 아래에서 추가해보세요!
              </p>
            ) : (
              <ul className="space-y-2">
                {tasks.map((task) => (
                  <li
                    key={task.id}
                    className="flex items-center justify-between rounded-md border px-3 py-2 text-sm"
                  >
                    <span className="truncate font-medium">{task.title}</span>
                    <span className={cn("shrink-0 text-xs", urgencyColor(task.deadline_at))}>
                      {formatDeadline(task.deadline_at)}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      </div>

      {/* Chat Input — 전송 시 /chat으로 이동 */}
      <div className="border-t bg-card p-4">
        <ChatInput onSend={handleSend} />
      </div>
    </div>
  )
}
