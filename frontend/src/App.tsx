import { BrowserRouter, Routes, Route } from "react-router-dom"
import Sidebar from "@/components/Sidebar"
import ErrorBoundary from "@/components/ErrorBoundary"
import HomePage from "@/pages/HomePage"
import ChatPage from "@/pages/ChatPage"
import TasksPage from "@/pages/TasksPage"
import CalendarPage from "@/pages/CalendarPage"
import SettingsPage from "@/pages/SettingsPage"

export default function App() {
  return (
    <BrowserRouter>
      <div className="flex h-screen overflow-hidden">
        <Sidebar />
        <main className="flex-1 overflow-hidden">
          <ErrorBoundary>
            <Routes>
              <Route path="/" element={<HomePage />} />
              <Route path="/chat" element={<ChatPage />} />
              <Route path="/tasks" element={<TasksPage />} />
              <Route path="/plan" element={<CalendarPage />} />
              <Route path="/settings" element={<SettingsPage />} />
            </Routes>
          </ErrorBoundary>
        </main>
      </div>
    </BrowserRouter>
  )
}
