import { Outlet, Link, useLocation } from 'react-router';
import { Compass, History, BarChart2 } from 'lucide-react';

export function Root() {
  const location = useLocation();

  const isActive = (path: string) => {
    if (path === '/') {
      return location.pathname === '/';
    }
    return location.pathname.startsWith(path);
  };

  return (
    <div className="min-h-screen bg-[#f0fdf4] flex flex-col">
      <main className="flex-1 pb-20">
        <Outlet />
      </main>

      {/* Bottom Navigation */}
      <nav className="fixed bottom-0 left-0 right-0 bg-white/80 backdrop-blur-2xl border-t border-black/8 z-50">
        <div className="max-w-2xl mx-auto flex pb-safe">
          <Link
            to="/"
            className={`flex-1 flex flex-col items-center gap-1 py-3 transition-colors ${
              isActive('/') && !isActive('/history')
                ? 'text-[#16a34a]'
                : 'text-[#6e6e73] hover:text-[#16a34a]'
            }`}
          >
            <Compass className={`w-6 h-6 ${isActive('/') && !isActive('/history') ? 'stroke-[2.5]' : 'stroke-[1.5]'}`} />
            <span className="text-[10px] font-medium">发现</span>
          </Link>

          <Link
            to="/history"
            className={`flex-1 flex flex-col items-center gap-1 py-3 transition-colors ${
              isActive('/history')
                ? 'text-[#16a34a]'
                : 'text-[#6e6e73] hover:text-[#16a34a]'
            }`}
          >
            <History className={`w-6 h-6 ${isActive('/history') ? 'stroke-[2.5]' : 'stroke-[1.5]'}`} />
            <span className="text-[10px] font-medium">历史</span>
          </Link>

          <Link
            to="/dashboard"
            className={`flex-1 flex flex-col items-center gap-1 py-3 transition-colors ${
              isActive('/dashboard')
                ? 'text-[#16a34a]'
                : 'text-[#6e6e73] hover:text-[#16a34a]'
            }`}
          >
            <BarChart2 className={`w-6 h-6 ${isActive('/dashboard') ? 'stroke-[2.5]' : 'stroke-[1.5]'}`} />
            <span className="text-[10px] font-medium">看板</span>
          </Link>
        </div>
      </nav>
    </div>
  );
}
