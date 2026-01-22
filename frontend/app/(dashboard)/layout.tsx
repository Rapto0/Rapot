import { Sidebar } from "@/components/dashboard/sidebar";
import { TopHeader } from "@/components/dashboard/top-header";

export default function DashboardLayout({
  children
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex min-h-screen bg-background text-white">
      <Sidebar />
      <div className="flex flex-1 flex-col">
        <TopHeader />
        <main className="flex-1 p-6">{children}</main>
      </div>
    </div>
  );
}
