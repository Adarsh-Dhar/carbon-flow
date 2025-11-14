import Header from '@/components/header'
import Sidebar from '@/components/sidebar'
import DashboardOverview from '@/components/pages/dashboard-overview'

export default function Home() {
  return (
    <div className="flex h-screen bg-slate-950">
      <Sidebar />
      <main className="flex-1 flex flex-col overflow-hidden">
        <Header />
        <div className="flex-1 overflow-auto">
          <DashboardOverview />
        </div>
      </main>
    </div>
  )
}
