import { useCallback, useEffect, useRef, useState } from "react"
import { useLocation, useNavigate } from "react-router-dom"
import { ArrowLeft, Bot, User, Loader2, AlertTriangle, Pencil, X } from "lucide-react"
import ChatInput from "@/components/ChatInput"
import { Button } from "@/components/ui/button"
import { apiPost, fetchChatHistory, saveChatMessages } from "@/lib/api"
import type { ChatMessageDTO } from "@/lib/api"
import { cn } from "@/lib/utils"

interface TaskCard {
  id: number
  title: string
  deadline_at: string | null
  est_minutes: number
  importance: number
  energy: number
}

interface CorrectionFields {
  title: string
  est_minutes: number
  importance: number
  energy: number
}

interface InboxResponse {
  action: string
  task?: TaskCard
  parsed_preview?: Record<string, unknown>
  clarification?: string
  inbox_log_id?: number
  message?: string
}

interface DisplayMessage {
  id: string
  dbId?: number
  role: "user" | "assistant" | "system"
  content: string
  metadata: Record<string, unknown> | null
  created_at: string
}

function toDisplayMessage(dto: ChatMessageDTO): DisplayMessage {
  return {
    id: `db-${dto.id}`,
    dbId: dto.id,
    role: dto.role,
    content: dto.content,
    metadata: dto.metadata,
    created_at: dto.created_at,
  }
}

function formatDateLabel(dateStr: string): string {
  const d = new Date(dateStr)
  const days = ["일", "월", "화", "수", "목", "금", "토"]
  return `${d.getFullYear()}년 ${d.getMonth() + 1}월 ${d.getDate()}일 (${days[d.getDay()]})`
}

function getDateKey(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString("ko-KR")
}

export default function ChatPage() {
  const location = useLocation()
  const navigate = useNavigate()
  const scrollRef = useRef<HTMLDivElement>(null)
  const initialProcessed = useRef(false)
  const topSentinelRef = useRef<HTMLDivElement>(null)

  const [messages, setMessages] = useState<DisplayMessage[]>([])
  const [sending, setSending] = useState(false)
  const [loadingHistory, setLoadingHistory] = useState(true)
  const [hasMore, setHasMore] = useState(false)
  const [oldestTimestamp, setOldestTimestamp] = useState<string | null>(null)

  // 히스토리 로드 + resolved 스캔
  const loadHistory = useCallback(async (before?: string) => {
    try {
      const data = await fetchChatHistory(before)
      setHasMore(data.has_more)

      if (data.messages.length > 0) {
        setOldestTimestamp(data.messages[0].created_at)
        const newMsgs = data.messages.map(toDisplayMessage)

        setMessages((prev) => {
          const existingIds = new Set(prev.map((m) => m.id))
          const unique = newMsgs.filter((m) => !existingIds.has(m.id))
          const merged = [...unique, ...prev]

          // resolved 스캔: resolvedInboxLogId를 수집하여 과거 needsConfirm 버튼 숨김
          const resolvedIds = new Set<number>()
          for (const m of merged) {
            const rid = m.metadata?.resolvedInboxLogId
            if (typeof rid === "number") resolvedIds.add(rid)
          }
          if (resolvedIds.size === 0) return merged

          return merged.map((m) => {
            if (
              m.metadata?.needsConfirm &&
              typeof m.metadata?.inboxLogId === "number" &&
              resolvedIds.has(m.metadata.inboxLogId as number)
            ) {
              return {
                ...m,
                metadata: { ...m.metadata, needsConfirm: false, resolved: true },
              }
            }
            return m
          })
        })
      }
    } catch {
      // 서버 연결 실패 시 빈 상태로 시작
    }
  }, [])

  // 초기 로드
  useEffect(() => {
    setLoadingHistory(true)
    loadHistory().finally(() => setLoadingHistory(false))
  }, [loadHistory])

  // HomePage에서 전달된 초기 메시지
  useEffect(() => {
    if (initialProcessed.current) return
    const initial = (location.state as { initialMessage?: string })
      ?.initialMessage
    if (initial) {
      initialProcessed.current = true
      handleSend(initial)
      navigate(location.pathname, { replace: true, state: {} })
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // 새 메시지 시 스크롤
  useEffect(() => {
    if (!loadingHistory) {
      scrollRef.current?.scrollTo({
        top: scrollRef.current.scrollHeight,
        behavior: "smooth",
      })
    }
  }, [messages.length, loadingHistory])

  // 위로 스크롤 감지 (점진 로드)
  useEffect(() => {
    const sentinel = topSentinelRef.current
    if (!sentinel || !scrollRef.current) return

    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting && hasMore && !loadingHistory && oldestTimestamp) {
          setLoadingHistory(true)
          loadHistory(oldestTimestamp).finally(() => setLoadingHistory(false))
        }
      },
      { root: scrollRef.current, threshold: 0.1 },
    )
    observer.observe(sentinel)
    return () => observer.disconnect()
  }, [hasMore, loadingHistory, oldestTimestamp, loadHistory])

  async function handleSend(text: string) {
    const now = new Date().toISOString()
    const userMsg: DisplayMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content: text,
      metadata: null,
      created_at: now,
    }
    setMessages((prev) => [...prev, userMsg])
    setSending(true)

    try {
      const data = await apiPost<InboxResponse>("/inbox", { text })

      let content = ""
      let metadata: Record<string, unknown> = {}

      try {
        const action = data?.action ?? "unknown"
        metadata.action = action

        switch (action) {
          case "saved_auto":
            content = data.message ?? "task를 생성했어요. 수정할 부분 있나요?"
            if (data.task) metadata.taskCard = data.task
            break
          case "saved_fallback":
            content =
              data.message ?? "LLM 연결이 불안정해서 기본값으로 저장했어요."
            if (data.task) metadata.taskCard = data.task
            metadata.warning = true
            break
          case "needs_confirmation":
            content = data.message ?? "이렇게 파싱했는데, 맞나요?"
            if (data.parsed_preview) metadata.parsedPreview = data.parsed_preview
            if (data.inbox_log_id) metadata.inboxLogId = data.inbox_log_id
            metadata.needsConfirm = true
            break
          case "needs_clarification":
            content = data.clarification ?? "좀 더 자세히 말씀해주세요."
            if (data.inbox_log_id) metadata.inboxLogId = data.inbox_log_id
            metadata.needsClarify = true
            break
          default:
            content = data.message ?? "처리 완료!"
        }
      } catch {
        content = "응답 처리 중 오류가 발생했어요. 다시 시도해주세요."
        metadata = { action: "error" }
      }

      const assistantMsg: DisplayMessage = {
        id: crypto.randomUUID(),
        role: "assistant",
        content,
        metadata,
        created_at: new Date().toISOString(),
      }
      setMessages((prev) => [...prev, assistantMsg])

      // DB에 저장
      saveChatMessages([
        { role: "user", content: text },
        { role: "assistant", content, metadata },
      ]).catch(() => {})
    } catch {
      const errMsg: DisplayMessage = {
        id: crypto.randomUUID(),
        role: "system",
        content: "서버에 연결할 수 없습니다. 백엔드가 실행 중인지 확인해주세요.",
        metadata: null,
        created_at: new Date().toISOString(),
      }
      setMessages((prev) => [...prev, errMsg])
    } finally {
      setSending(false)
    }
  }

  function markResolved(inboxLogId: number) {
    setMessages((prev) =>
      prev.map((m) => {
        if (m.metadata?.inboxLogId === inboxLogId && m.metadata?.needsConfirm) {
          return {
            ...m,
            metadata: { ...m.metadata, needsConfirm: false, resolved: true },
          }
        }
        return m
      }),
    )
  }

  async function handleConfirm(inboxLogId: number) {
    setSending(true)
    try {
      const data = await apiPost<{ action: string; task?: TaskCard; message?: string }>(
        `/inbox/${inboxLogId}/confirm`,
      )
      markResolved(inboxLogId)
      const msg: DisplayMessage = {
        id: crypto.randomUUID(),
        role: "assistant",
        content: data.message ?? "저장 완료!",
        metadata: data.task
          ? { taskCard: data.task, action: data.action, resolvedInboxLogId: inboxLogId }
          : { resolvedInboxLogId: inboxLogId },
        created_at: new Date().toISOString(),
      }
      setMessages((prev) => [...prev, msg])
      saveChatMessages([
        { role: "assistant", content: msg.content, metadata: msg.metadata },
      ]).catch(() => {})
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          role: "system",
          content: "확인 처리에 실패했습니다.",
          metadata: null,
          created_at: new Date().toISOString(),
        },
      ])
    } finally {
      setSending(false)
    }
  }

  async function handleCorrect(inboxLogId: number, corrections: CorrectionFields) {
    setSending(true)
    try {
      const data = await apiPost<{ action: string; task?: TaskCard; message?: string }>(
        `/inbox/${inboxLogId}/confirm`,
        { corrections },
      )
      markResolved(inboxLogId)
      const msg: DisplayMessage = {
        id: crypto.randomUUID(),
        role: "assistant",
        content: data.message ?? "수정 사항을 반영해서 저장했어요!",
        metadata: data.task
          ? { taskCard: data.task, action: data.action, resolvedInboxLogId: inboxLogId }
          : { resolvedInboxLogId: inboxLogId },
        created_at: new Date().toISOString(),
      }
      setMessages((prev) => [...prev, msg])
      saveChatMessages([
        { role: "assistant", content: msg.content, metadata: msg.metadata },
      ]).catch(() => {})
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          role: "system",
          content: "수정 처리에 실패했습니다.",
          metadata: null,
          created_at: new Date().toISOString(),
        },
      ])
    } finally {
      setSending(false)
    }
  }

  function handleDismiss(msgId: string) {
    setMessages((prev) =>
      prev.map((m) =>
        m.id === msgId
          ? { ...m, metadata: { ...m.metadata, needsConfirm: false, resolved: true, dismissed: true } }
          : m,
      ),
    )
  }

  // 날짜 구분선 삽입을 위한 렌더링
  let lastDateKey = ""

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="flex h-14 items-center gap-2 border-b px-4">
        <Button variant="ghost" size="icon" onClick={() => navigate("/")}>
          <ArrowLeft className="h-5 w-5" />
        </Button>
        <h1 className="font-semibold">Chat</h1>
      </div>

      {/* Messages */}
      <div ref={scrollRef} className="flex-1 overflow-auto p-4">
        <div className="mx-auto max-w-2xl space-y-4">
          {/* 점진 로드 감지용 sentinel */}
          <div ref={topSentinelRef} className="h-1" />

          {loadingHistory && messages.length > 0 && (
            <div className="flex justify-center py-2">
              <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
            </div>
          )}

          {loadingHistory && messages.length === 0 ? (
            <div className="flex justify-center py-8">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
          ) : messages.length === 0 ? (
            <div className="py-8 text-center text-sm text-muted-foreground">
              대화를 시작해보세요!
            </div>
          ) : (
            messages.map((msg) => {
              const dateKey = getDateKey(msg.created_at)
              const showDateSep = dateKey !== lastDateKey
              lastDateKey = dateKey

              return (
                <div key={msg.id}>
                  {/* 날짜 구분선 */}
                  {showDateSep && (
                    <div className="flex items-center gap-3 py-3">
                      <div className="h-px flex-1 bg-border" />
                      <span className="text-xs font-medium text-muted-foreground">
                        {formatDateLabel(msg.created_at)}
                      </span>
                      <div className="h-px flex-1 bg-border" />
                    </div>
                  )}

                  {/* 메시지 */}
                  <MessageBubble
                    msg={msg}
                    onConfirm={handleConfirm}
                    onCorrect={handleCorrect}
                    onDismiss={handleDismiss}
                    sending={sending}
                  />
                </div>
              )
            })
          )}

          {/* 타이핑 인디케이터 */}
          {sending && (
            <div className="flex gap-3">
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-secondary text-secondary-foreground">
                <Bot className="h-4 w-4" />
              </div>
              <div className="flex items-center gap-1 rounded-lg bg-secondary px-4 py-2.5">
                <span className="h-2 w-2 animate-bounce rounded-full bg-muted-foreground [animation-delay:0ms]" />
                <span className="h-2 w-2 animate-bounce rounded-full bg-muted-foreground [animation-delay:150ms]" />
                <span className="h-2 w-2 animate-bounce rounded-full bg-muted-foreground [animation-delay:300ms]" />
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Input */}
      <div className="border-t bg-card p-4">
        <div className="mx-auto max-w-2xl">
          <ChatInput onSend={handleSend} disabled={sending} />
        </div>
      </div>
    </div>
  )
}

// ─── 메시지 버블 컴포넌트 ─────────────────────────────────

function MessageBubble({
  msg,
  onConfirm,
  onCorrect,
  onDismiss,
  sending,
}: {
  msg: DisplayMessage
  onConfirm: (id: number) => void
  onCorrect: (id: number, corrections: CorrectionFields) => void
  onDismiss: (msgId: string) => void
  sending: boolean
}) {
  const taskCard = msg.metadata?.taskCard as TaskCard | undefined
  const parsedPreview = msg.metadata?.parsedPreview as Record<string, unknown> | undefined
  const needsConfirm = msg.metadata?.needsConfirm as boolean | undefined
  const isResolved = msg.metadata?.resolved as boolean | undefined
  const isWarning = msg.metadata?.warning as boolean | undefined
  const inboxLogId = msg.metadata?.inboxLogId as number | undefined

  const [editing, setEditing] = useState(false)
  const [editFields, setEditFields] = useState<CorrectionFields>({
    title: String(parsedPreview?.title ?? ""),
    est_minutes: Number(parsedPreview?.est_minutes ?? 60),
    importance: Number(parsedPreview?.importance ?? 3),
    energy: Number(parsedPreview?.energy ?? 3),
  })

  function handleSaveCorrection() {
    if (!inboxLogId) return
    onCorrect(inboxLogId, editFields)
    setEditing(false)
  }

  return (
    <div
      className={cn(
        "flex gap-3",
        msg.role === "user" && "flex-row-reverse",
      )}
    >
      {/* Avatar */}
      <div
        className={cn(
          "flex h-8 w-8 shrink-0 items-center justify-center rounded-full",
          msg.role === "user"
            ? "bg-primary text-primary-foreground"
            : msg.role === "assistant"
              ? "bg-secondary text-secondary-foreground"
              : "bg-destructive/10 text-destructive",
        )}
      >
        {msg.role === "user" ? (
          <User className="h-4 w-4" />
        ) : (
          <Bot className="h-4 w-4" />
        )}
      </div>

      {/* Content */}
      <div
        className={cn(
          "max-w-[75%] space-y-2 rounded-lg px-4 py-2.5 text-sm",
          msg.role === "user"
            ? "bg-primary text-primary-foreground"
            : "bg-secondary",
        )}
      >
        {/* 경고 배지 (fallback) */}
        {isWarning && (
          <div className="flex items-center gap-1.5 text-xs text-yellow-600">
            <AlertTriangle className="h-3.5 w-3.5" />
            <span>LLM fallback — 기본값으로 저장됨</span>
          </div>
        )}

        <p>{msg.content}</p>

        {/* Task 카드 */}
        {taskCard && <TaskCardView card={taskCard} />}

        {/* 파싱 프리뷰 (needs_confirmation) — 보기 모드 */}
        {parsedPreview && !taskCard && !editing && (
          <div className="rounded-md border bg-card p-3 text-card-foreground">
            <p className="mb-1 text-xs font-medium text-muted-foreground">파싱 결과 프리뷰</p>
            {parsedPreview.title && (
              <p className="font-semibold">{String(parsedPreview.title)}</p>
            )}
            <div className="mt-1 grid grid-cols-2 gap-1 text-xs text-muted-foreground">
              {parsedPreview.est_minutes && (
                <span>예상: {String(parsedPreview.est_minutes)}분</span>
              )}
              {parsedPreview.importance && (
                <span>중요도: {String(parsedPreview.importance)}/5</span>
              )}
              {parsedPreview.energy && (
                <span>에너지: {String(parsedPreview.energy)}/5</span>
              )}
            </div>
          </div>
        )}

        {/* 인라인 편집 폼 */}
        {editing && (
          <div className="space-y-2 rounded-md border bg-card p-3 text-card-foreground">
            <div className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
              <Pencil className="h-3.5 w-3.5" />
              <span>수정하기</span>
            </div>
            <div className="space-y-1.5">
              <label className="block">
                <span className="text-xs text-muted-foreground">제목</span>
                <input
                  type="text"
                  value={editFields.title}
                  onChange={(e) => setEditFields((f) => ({ ...f, title: e.target.value }))}
                  className="mt-0.5 w-full rounded border border-input bg-background px-2 py-1 text-sm"
                />
              </label>
              <div className="grid grid-cols-3 gap-2">
                <label className="block">
                  <span className="text-xs text-muted-foreground">예상(분)</span>
                  <input
                    type="number"
                    min={5}
                    max={480}
                    value={editFields.est_minutes}
                    onChange={(e) => setEditFields((f) => ({ ...f, est_minutes: Number(e.target.value) }))}
                    className="mt-0.5 w-full rounded border border-input bg-background px-2 py-1 text-sm"
                  />
                </label>
                <label className="block">
                  <span className="text-xs text-muted-foreground">중요도</span>
                  <select
                    value={editFields.importance}
                    onChange={(e) => setEditFields((f) => ({ ...f, importance: Number(e.target.value) }))}
                    className="mt-0.5 w-full rounded border border-input bg-background px-2 py-1 text-sm"
                  >
                    {[1, 2, 3, 4, 5].map((v) => (
                      <option key={v} value={v}>{v}</option>
                    ))}
                  </select>
                </label>
                <label className="block">
                  <span className="text-xs text-muted-foreground">에너지</span>
                  <select
                    value={editFields.energy}
                    onChange={(e) => setEditFields((f) => ({ ...f, energy: Number(e.target.value) }))}
                    className="mt-0.5 w-full rounded border border-input bg-background px-2 py-1 text-sm"
                  >
                    {[1, 2, 3, 4, 5].map((v) => (
                      <option key={v} value={v}>{v}</option>
                    ))}
                  </select>
                </label>
              </div>
            </div>
            <div className="flex gap-2 pt-1">
              <Button size="sm" disabled={sending} onClick={handleSaveCorrection}>
                저장
              </Button>
              <Button size="sm" variant="ghost" onClick={() => setEditing(false)}>
                취소
              </Button>
            </div>
          </div>
        )}

        {/* resolved 표시 */}
        {isResolved && !msg.metadata?.dismissed && (
          <p className="text-xs text-green-600">✅ 확인됨</p>
        )}
        {msg.metadata?.dismissed && (
          <p className="text-xs text-muted-foreground">무시됨</p>
        )}

        {/* 확인/수정/무시 버튼 (needs_confirmation) */}
        {needsConfirm && inboxLogId && !editing && (
          <div className="flex gap-2 pt-1">
            <Button
              size="sm"
              variant="default"
              disabled={sending}
              onClick={() => onConfirm(inboxLogId)}
            >
              맞아요
            </Button>
            <Button
              size="sm"
              variant="outline"
              disabled={sending}
              onClick={() => setEditing(true)}
            >
              수정할게요
            </Button>
            <Button
              size="sm"
              variant="ghost"
              disabled={sending}
              onClick={() => onDismiss(msg.id)}
              className="text-muted-foreground"
            >
              무시
            </Button>
          </div>
        )}
      </div>
    </div>
  )
}

function TaskCardView({ card }: { card: TaskCard }) {
  const [cancelled, setCancelled] = useState(false)
  const [cancelling, setCancelling] = useState(false)

  async function handleCancel() {
    setCancelling(true)
    try {
      await apiPost(`/tasks/${card.id}/cancel`)
      setCancelled(true)
    } catch {
      // 실패 시 무시
    } finally {
      setCancelling(false)
    }
  }

  if (cancelled) {
    return (
      <div className="rounded-md border border-dashed bg-card p-3 text-card-foreground opacity-60">
        <p className="font-semibold line-through">{card.title}</p>
        <p className="mt-1 text-xs text-muted-foreground">취소됨</p>
      </div>
    )
  }

  return (
    <div className="rounded-md border bg-card p-3 text-card-foreground">
      <div className="flex items-start justify-between">
        <p className="font-semibold">{card.title}</p>
        <button
          onClick={handleCancel}
          disabled={cancelling}
          title="취소"
          className="ml-2 shrink-0 rounded p-0.5 text-muted-foreground hover:bg-destructive/10 hover:text-destructive"
        >
          <X className="h-4 w-4" />
        </button>
      </div>
      <div className="mt-1 grid grid-cols-2 gap-1 text-xs text-muted-foreground">
        <span>
          마감:{" "}
          {card.deadline_at
            ? new Date(card.deadline_at).toLocaleString("ko-KR")
            : "없음"}
        </span>
        <span>예상: {card.est_minutes}분</span>
        <span>중요도: {card.importance}/5</span>
        <span>에너지: {card.energy}/5</span>
      </div>
    </div>
  )
}
