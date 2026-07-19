import { Activity, FileText, Lightbulb, Target } from "lucide-react";
import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { StatCard } from "../components/StatCard";
import { RunCard } from "../components/RunCard";
import { Loading, LoadingSkeleton } from "../components/Loading";
import { useAnalysisStore } from "../store/analysisStore";

export const Dashboard = () => {
  const { runs, isLoading, fetchRuns } = useAnalysisStore();
  const navigate = useNavigate();

  useEffect(() => {
    fetchRuns();
  }, [fetchRuns]);

  const totalReviews = runs.reduce((sum, run) => sum + run.total_reviews, 0);
  const completedRuns = runs.filter((run) => run.status === "completed").length;
  const avgReviews = runs.length > 0 ? Math.round(totalReviews / runs.length) : 0;

  const recentRuns = runs.slice(0, 5);

  return (
    <div className="min-h-screen p-8 animate-fade-in">
      <div className="max-w-7xl mx-auto">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-800 mb-2">仪表盘</h1>
          <p className="text-gray-500">欢迎回来！查看您的分析概览</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <StatCard
            title="分析任务"
            value={runs.length}
            icon={Activity}
            color="primary"
          />
          <StatCard
            title="总评论数"
            value={totalReviews}
            icon={FileText}
            color="secondary"
          />
          <StatCard
            title="已完成"
            value={completedRuns}
            icon={Lightbulb}
            color="green"
          />
          <StatCard
            title="平均评论"
            value={avgReviews}
            icon={Target}
            color="orange"
          />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          <div className="lg:col-span-2">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-semibold text-gray-800">最近分析任务</h2>
              <button
                onClick={() => navigate("/runs")}
                className="text-sm text-primary-600 hover:text-primary-700 font-medium"
              >
                查看全部 →
              </button>
            </div>

            {isLoading ? (
              <LoadingSkeleton />
            ) : recentRuns.length > 0 ? (
              <div className="space-y-4">
                {recentRuns.map((run) => (
                  <RunCard
                    key={run.id}
                    run={run}
                    onClick={() => navigate(`/runs/${run.id}`)}
                  />
                ))}
              </div>
            ) : (
              <div className="glass-card p-12 text-center">
                <div className="w-20 h-20 mx-auto mb-4 rounded-full bg-gray-100 flex items-center justify-center">
                  <Activity className="text-gray-400" size={32} />
                </div>
                <h3 className="text-lg font-semibold text-gray-700 mb-2">暂无分析任务</h3>
                <p className="text-gray-500 mb-4">开始创建第一个分析任务吧！</p>
                <button
                  onClick={() => navigate("/analyze")}
                  className="gradient-btn"
                >
                  创建分析
                </button>
              </div>
            )}
          </div>

          <div className="glass-card p-6">
            <h3 className="text-lg font-semibold text-gray-800 mb-4">快速开始</h3>
            <div className="space-y-3">
              <button
                onClick={() => navigate("/analyze")}
                className="w-full flex items-center gap-3 p-4 rounded-xl bg-gradient-to-r from-primary-500 to-secondary-400 text-white hover:from-primary-600 hover:to-secondary-500 transition-all duration-300"
              >
                <div className="w-10 h-10 rounded-lg bg-white/20 flex items-center justify-center">
                  <Lightbulb size={20} />
                </div>
                <div className="text-left">
                  <p className="font-medium">创建新分析</p>
                  <p className="text-xs text-white/80">输入 App Store 链接开始分析</p>
                </div>
              </button>

              <div className="p-4 rounded-xl bg-gray-50">
                <h4 className="font-medium text-gray-700 mb-2">使用提示</h4>
                <ul className="space-y-2 text-sm text-gray-500">
                  <li className="flex items-start gap-2">
                    <span className="w-1.5 h-1.5 rounded-full bg-primary-500 mt-1.5" />
                    输入 App Store 链接自动采集评论
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="w-1.5 h-1.5 rounded-full bg-secondary-400 mt-1.5" />
                    设置分析目标聚焦特定问题
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="w-1.5 h-1.5 rounded-full bg-green-400 mt-1.5" />
                    AI 自动生成 PRD 和测试用例
                  </li>
                </ul>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
