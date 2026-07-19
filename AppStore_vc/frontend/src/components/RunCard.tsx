import { ArrowRight, Clock, Sparkles, CheckCircle2, AlertCircle } from "lucide-react";
import type { AnalysisRun } from "../api/types";

interface RunCardProps {
  run: AnalysisRun;
  onClick: () => void;
}

export const RunCard = ({ run, onClick }: RunCardProps) => {
  const getStatusIcon = () => {
    switch (run.status) {
      case "completed":
        return <CheckCircle2 className="text-green-500" size={16} />;
      case "running":
        return <Sparkles className="text-primary-500 animate-pulse" size={16} />;
      default:
        return <AlertCircle className="text-orange-500" size={16} />;
    }
  };

  const getStatusText = () => {
    switch (run.status) {
      case "completed":
        return "已完成";
      case "running":
        return "运行中";
      case "failed":
        return "失败";
      default:
        return "待处理";
    }
  };

  const getStatusColor = () => {
    switch (run.status) {
      case "completed":
        return "bg-green-100 text-green-600";
      case "running":
        return "bg-primary-100 text-primary-600";
      case "failed":
        return "bg-red-100 text-red-600";
      default:
        return "bg-gray-100 text-gray-600";
    }
  };

  return (
    <div
      onClick={onClick}
      className="glass-card p-5 hover:shadow-card transition-all duration-500 hover:-translate-y-1 cursor-pointer group"
    >
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2">
          {getStatusIcon()}
          <span className={`text-xs font-medium px-2 py-1 rounded-full ${getStatusColor()}`}>
            {getStatusText()}
          </span>
        </div>
        <div className="text-xs text-gray-400 flex items-center gap-1">
          <Clock size={12} />
          {new Date(run.started_at).toLocaleDateString("zh-CN")}
        </div>
      </div>

      <h3 className="font-semibold text-gray-800 mb-2 line-clamp-1 group-hover:text-primary-600 transition-colors">
        {run.app_name}
      </h3>

      <p className="text-sm text-gray-500 mb-4 line-clamp-2">
        {run.analysis_goal || "未设置分析目标"}
      </p>

      <div className="flex items-center justify-between">
        <div className="flex gap-4 text-sm">
          <span className="text-gray-500">
            <span className="font-medium text-gray-700">{run.total_reviews}</span> 评论
          </span>
          <span className="text-gray-500">
            <span className="font-medium text-gray-700">{run.cleaned_reviews}</span> 已清洗
          </span>
        </div>
        <ArrowRight className="text-gray-400 group-hover:text-primary-500 group-hover:translate-x-1 transition-all" size={18} />
      </div>
    </div>
  );
};
