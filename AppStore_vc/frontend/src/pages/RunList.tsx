import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Activity, ArrowRight } from "lucide-react";
import { RunCard } from "../components/RunCard";
import { Loading, LoadingSkeleton } from "../components/Loading";
import { useAnalysisStore } from "../store/analysisStore";

export const RunList = () => {
  const { runs, isLoading, fetchRuns } = useAnalysisStore();
  const navigate = useNavigate();

  useEffect(() => {
    fetchRuns();
  }, [fetchRuns]);

  return (
    <div className="min-h-screen p-8 animate-fade-in">
      <div className="max-w-5xl mx-auto">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold text-gray-800 mb-2">分析任务列表</h1>
            <p className="text-gray-500">查看和管理所有分析任务</p>
          </div>
          <button onClick={() => navigate("/analyze")} className="gradient-btn">
            创建新分析
          </button>
        </div>

        {isLoading ? (
          <LoadingSkeleton />
        ) : runs.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {runs.map((run) => (
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
            <button onClick={() => navigate("/analyze")} className="gradient-btn">
              创建分析
            </button>
          </div>
        )}

        {runs.length > 0 && (
          <div className="mt-8 glass-card p-6">
            <h3 className="font-semibold text-gray-800 mb-4">任务统计</h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="text-center p-4 rounded-xl bg-gray-50">
                <p className="text-2xl font-bold text-gray-800">{runs.length}</p>
                <p className="text-sm text-gray-500">总任务数</p>
              </div>
              <div className="text-center p-4 rounded-xl bg-green-50">
                <p className="text-2xl font-bold text-green-600">
                  {runs.filter((r) => r.status === "completed").length}
                </p>
                <p className="text-sm text-gray-500">已完成</p>
              </div>
              <div className="text-center p-4 rounded-xl bg-primary-50">
                <p className="text-2xl font-bold text-primary-600">
                  {runs.filter((r) => r.status === "running").length}
                </p>
                <p className="text-sm text-gray-500">运行中</p>
              </div>
              <div className="text-center p-4 rounded-xl bg-red-50">
                <p className="text-2xl font-bold text-red-600">
                  {runs.filter((r) => r.status === "failed").length}
                </p>
                <p className="text-sm text-gray-500">失败</p>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
