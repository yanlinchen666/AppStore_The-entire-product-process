import { LayoutDashboard, Search, BarChart3, GitBranch, Menu, X } from "lucide-react";
import { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

interface SidebarProps {
  collapsed?: boolean;
}

export const Sidebar = ({ collapsed = false }: SidebarProps) => {
  const [isOpen, setIsOpen] = useState(!collapsed);
  const location = useLocation();
  const navigate = useNavigate();

  const navItems = [
    { icon: LayoutDashboard, label: "仪表盘", path: "/" },
    { icon: Search, label: "创建分析", path: "/analyze" },
    { icon: BarChart3, label: "分析列表", path: "/runs" },
    { icon: GitBranch, label: "追溯链", path: "/traceability" },
  ];

  return (
    <>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="fixed top-4 left-4 z-50 p-2 rounded-xl bg-white/80 backdrop-blur-lg shadow-lg hover:bg-white transition-all duration-300 lg:hidden"
      >
        {isOpen ? <X size={24} /> : <Menu size={24} />}
      </button>

      <aside
        className={`fixed left-0 top-0 h-full glass-card z-40 transition-all duration-500 ease-in-out flex flex-col ${
          isOpen ? "w-64" : "w-0 overflow-hidden lg:w-64"
        }`}
      >
        <div className="p-6 border-b border-white/30">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-r from-primary-500 to-secondary-400 flex items-center justify-center">
              <BarChart3 className="text-white" size={20} />
            </div>
            <div className="flex flex-col">
              <span className="font-bold text-gray-800 text-lg">AppInsight</span>
              <span className="text-xs text-gray-500">AI 驱动分析</span>
            </div>
          </div>
        </div>

        <nav className="flex-1 p-4">
          <ul className="space-y-2">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = location.pathname === item.path;

              return (
                <li key={item.path}>
                  <button
                    onClick={() => {
                      navigate(item.path);
                      setIsOpen(false);
                    }}
                    className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-300 ${
                      isActive
                        ? "bg-gradient-to-r from-primary-500/20 to-secondary-400/20 text-primary-600 font-medium"
                        : "text-gray-600 hover:text-primary-600 hover:bg-white/50"
                    }`}
                  >
                    <Icon size={20} />
                    <span className="text-sm">{item.label}</span>
                  </button>
                </li>
              );
            })}
          </ul>
        </nav>

        <div className="p-4 border-t border-white/30">
          <div className="glass-card p-4">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-full bg-gradient-to-r from-primary-400 to-secondary-400 flex items-center justify-center">
                <span className="text-white text-sm font-medium">AI</span>
              </div>
              <div className="flex-1">
                <p className="text-sm font-medium text-gray-700">AI 分析引擎</p>
                <p className="text-xs text-green-500">已连接</p>
              </div>
            </div>
          </div>
        </div>
      </aside>
    </>
  );
};
