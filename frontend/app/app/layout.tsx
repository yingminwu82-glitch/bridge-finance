import { Navigation } from "@/components/Navigation";
import { BoundaryBanner } from "@/components/BoundaryBanner";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen">
      <Navigation role="enterprise" />
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-4">
        <BoundaryBanner compact />
      </div>
      <main className="max-w-7xl mx-auto px-4 sm:px-6 pb-12">{children}</main>
    </div>
  );
}
