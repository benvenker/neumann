import TopNav from "@/components/top-nav"
import ProjectsSidebar from "@/components/projects-sidebar"
import ChatSection from "@/components/chat-section"
import ActivitySidebar from "@/components/activity-sidebar"

export default function HomePage() {
  return (
    <div className="flex h-screen flex-col bg-background">
      <TopNav />
      <div className="flex flex-1 overflow-hidden">
        <ProjectsSidebar />
        <ChatSection />
        <ActivitySidebar />
      </div>
    </div>
  )
}
