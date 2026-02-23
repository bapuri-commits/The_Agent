import { Settings } from "lucide-react"

export default function SettingsPage() {
  return (
    <div className="flex h-full flex-col">
      <div className="flex h-14 items-center border-b px-6">
        <h1 className="text-lg font-semibold">Settings</h1>
      </div>
      <div className="flex flex-1 flex-col items-center justify-center gap-4 text-muted-foreground">
        <Settings className="h-12 w-12" />
        <p className="text-sm">설정 페이지 (추후 구현)</p>
        <p className="text-xs">테마, 알림, 프로필 설정 등</p>
      </div>
    </div>
  )
}
