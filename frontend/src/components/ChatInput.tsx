import { useState, type FormEvent } from "react"
import { Send } from "lucide-react"
import { Button } from "@/components/ui/button"

interface ChatInputProps {
  onSend: (message: string) => void
  placeholder?: string
  disabled?: boolean
}

export default function ChatInput({
  onSend,
  placeholder = "무엇을 도와드릴까요?",
  disabled = false,
}: ChatInputProps) {
  const [text, setText] = useState("")

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    const trimmed = text.trim()
    if (!trimmed) return
    onSend(trimmed)
    setText("")
  }

  return (
    <form onSubmit={handleSubmit} className="flex items-center gap-2">
      <input
        type="text"
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder={placeholder}
        disabled={disabled}
        className="flex-1 rounded-md border border-input bg-background px-4 py-2.5 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
      />
      <Button type="submit" size="icon" disabled={disabled || !text.trim()}>
        <Send className="h-4 w-4" />
      </Button>
    </form>
  )
}
