import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Search, Sparkles, ArrowRight, Info } from "lucide-react";
import { apiClient } from "../api/client";
import { Loading } from "../components/Loading";

export const Analyze = () => {
  const [appUrl, setAppUrl] = useState("");
  const [analysisGoal, setAnalysisGoal] = useState("");
  const [maxReviews, setMaxReviews] = useState(50);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    if (!appUrl) {
      setError("请输入 App Store 链接");
      return;
    }

    if (!analysisGoal) {
      setError("请输入分析目标");
      return;
    }

    setIsLoading(true);

    try {
      const response = await apiClient.analyze({
        app_url: appUrl,
        analysis_goal: analysisGoal,
        max_reviews: maxReviews,
      });

      navigate(`/runs/${response.run_id}`);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setIsLoading(false);
    }
  };

  const extractAppId = (url: string) => {
    const match = url.match(/id(\d+)/);
    return match ? match[1] : null;
  };

  return (
    <div className="min-h-screen p-8 animate-fade-in">
      <div className="max-w-3xl mx-auto">
        <div className="text-center mb-12">
          <div className="w-20 h-20 mx-auto mb-6 rounded-2xl bg-gradient-to-br from-primary-500 to-secondary-400 flex items-center justify-center animate-float">
            <Search className="text-white" size={32} />
          </div>
          <h1 className="text-3xl font-bold text-gray-800 mb-3">创建新分析</h1>
          <p className="text-gray-500">输入 App Store 链接，AI 将自动分析用户评论并生成产品需求</p>
        </div>

        <div className="glass-card p-8">
          <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                App Store 链接
              </label>
              <div className="relative">
                <span className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400">
                  <Info size={18} />
                </span>
                <input
                  type="url"
                  value={appUrl}
                  onChange={(e) => setAppUrl(e.target.value)}
                  placeholder="https://apps.apple.com/cn/app/xxx/id1234567890"
                  className="input-glass w-full pl-12"
                />
              </div>
              {appUrl && extractAppId(appUrl) && (
                <p className="text-xs text-green-500 mt-2">已识别 App ID: {extractAppId(appUrl)}</p>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                分析目标
              </label>
              <textarea
                value={analysisGoal}
                onChange={(e) => setAnalysisGoal(e.target.value)}
                placeholder="例如：分析评分下降的真实原因，重点关注订阅和功能可用性问题"
                rows={3}
                className="input-glass w-full resize-none"
              />
              <div className="flex gap-2 mt-2">
                {["订阅问题", "功能可用性", "性能问题", "UI/UX"].map((tag) => (
                  <button
                    key={tag}
                    type="button"
                    onClick={() => setAnalysisGoal((prev) => prev + (prev ? "，" : "") + tag)}
                    className="text-xs px-3 py-1 rounded-full bg-gray-100 text-gray-600 hover:bg-primary-50 hover:text-primary-600 transition-colors"
                  >
                    {tag}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                评论数量限制
              </label>
              <div className="flex items-center gap-4">
                <input
                  type="range"
                  min="10"
                  max="200"
                  value={maxReviews}
                  onChange={(e) => setMaxReviews(Number(e.target.value))}
                  className="flex-1 h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-primary-500"
                />
                <span className="text-sm font-medium text-gray-700 w-12 text-right">
                  {maxReviews}
                </span>
              </div>
              <p className="text-xs text-gray-400 mt-2">
                建议初始测试使用较少数量，完整分析使用 100+ 评论
              </p>
            </div>

            {error && (
              <div className="p-4 rounded-xl bg-red-50 text-red-600 text-sm">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={isLoading}
              className="w-full gradient-btn flex items-center justify-center gap-2"
            >
              {isLoading ? (
                <Loading text="" size="small" />
              ) : (
                <>
                  <Sparkles size={18} />
                  开始分析
                  <ArrowRight size={18} />
                </>
              )}
            </button>
          </form>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-8">
          {[
            {
              title: "数据采集",
              desc: "自动从 App Store RSS 获取真实用户评论",
            },
            {
              title: "智能分析",
              desc: "LLM 动态分类问题，识别核心用户痛点",
            },
            {
              title: "生成交付物",
              desc: "自动生成 PRD 和测试用例，支持版本规划",
            },
          ].map((item, index) => (
            <div
              key={index}
              className="glass-card p-6 text-center hover:shadow-card transition-all duration-300"
            >
              <div className="w-12 h-12 mx-auto mb-4 rounded-xl bg-gradient-to-br from-primary-50 to-secondary-50 flex items-center justify-center">
                <span className="text-primary-600 font-bold text-lg">{index + 1}</span>
              </div>
              <h4 className="font-semibold text-gray-800 mb-2">{item.title}</h4>
              <p className="text-sm text-gray-500">{item.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
