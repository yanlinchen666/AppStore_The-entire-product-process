import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { ArrowLeft, RefreshCw, MessageSquare, Lightbulb, FileCheck, GitBranch, Star, ThumbsUp, ThumbsDown, AlertTriangle } from "lucide-react";
import { Loading } from "../components/Loading";
import { ProgressTracker } from "../components/ProgressTracker";
import { apiClient } from "../api/client";
import type { AnalysisRun, Review, Finding, Requirement, TestCase } from "../api/types";

type TabType = "summary" | "reviews" | "findings" | "prd" | "testcases";

export const RunDetail = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [run, setRun] = useState<AnalysisRun | null>(null);
  const [reviews, setReviews] = useState<Review[]>([]);
  const [findings, setFindings] = useState<Finding[]>([]);
  const [requirements, setRequirements] = useState<Requirement[]>([]);
  const [testCases, setTestCases] = useState<TestCase[]>([]);
  const [activeTab, setActiveTab] = useState<TabType>("summary");
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");

  const loadRun = async () => {
    if (!id) return;
    try {
      const runData = await apiClient.getRunById(Number(id));
      setRun(runData);
    } catch (err) {
      console.error("Failed to fetch run:", err);
    }
  };

  useEffect(() => {
    const init = async () => {
      setIsLoading(true);
      await loadRun();
      setIsLoading(false);
    };
    init();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  // Fetch reviews immediately (they may exist before analysis completes)
  useEffect(() => {
    if (!id || !run) return;
    apiClient.getReviewsByRunId(Number(id))
      .then(setReviews)
      .catch((err) => console.error("Failed to fetch reviews:", err));
  }, [id, run]);

  // When run is completed, fetch findings/requirements/testcases
  const loadResults = async () => {
    if (!id) return;
    try {
      const [findingsData, requirementsData, testCasesData] = await Promise.all([
        apiClient.getFindingsByRunId(Number(id)).catch(() => []),
        apiClient.getRequirementsByRunId(Number(id)).catch(() => []),
        apiClient.getTestCasesByRunId(Number(id)).catch(() => []),
      ]);
      setFindings(findingsData);
      setRequirements(requirementsData);
      setTestCases(testCasesData);
    } catch (err) {
      console.error("Failed to fetch results:", err);
    }
  };

  useEffect(() => {
    if (run?.status === "completed") {
      loadResults();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [run?.status, id]);

  const handleProgressComplete = () => {
    loadRun();
    loadResults();
  };

  const filteredReviews = reviews.filter(
    (r) =>
      (r.title || "").toLowerCase().includes(searchQuery.toLowerCase()) ||
      (r.content || "").toLowerCase().includes(searchQuery.toLowerCase())
  );

  const tabs = [
    { key: "summary", label: "概览", icon: MessageSquare },
    { key: "reviews", label: `评论 (${reviews.length})`, icon: Star },
    { key: "findings", label: `发现 (${findings.length})`, icon: Lightbulb },
    { key: "prd", label: `PRD (${requirements.length})`, icon: FileCheck },
    { key: "testcases", label: `测试用例 (${testCases.length})`, icon: GitBranch },
  ] as const;

  const getStatusColor = () => {
    switch (run?.status) {
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

  if (isLoading) {
    return (
      <div className="min-h-screen p-8 flex items-center justify-center">
        <Loading text="加载分析结果..." />
      </div>
    );
  }

  if (!run) {
    return (
      <div className="min-h-screen p-8 flex items-center justify-center">
        <div className="text-center">
          <p className="text-gray-500">分析任务不存在</p>
          <button onClick={() => navigate("/")} className="gradient-btn mt-4">
            返回首页
          </button>
        </div>
      </div>
    );
  }

  // Show progress tracker while running
  const isRunning = run.status === "running";

  const avgRating = reviews.length > 0
    ? reviews.reduce((sum, r) => sum + r.rating, 0) / reviews.length
    : 0;

  const assumptionCount = findings.filter((f) => f.is_assumption).length;
  const conflictCount = findings.filter((f) => f.has_conflict).length;

  return (
    <div className="min-h-screen p-8 animate-fade-in">
      <div className="max-w-6xl mx-auto">
        <div className="flex items-center gap-4 mb-8">
          <button
            onClick={() => navigate("/")}
            className="p-2 rounded-xl hover:bg-white/50 transition-colors"
          >
            <ArrowLeft className="text-gray-600" size={20} />
          </button>
          <div>
            <h1 className="text-2xl font-bold text-gray-800">{run.app_name}</h1>
            <p className="text-gray-500 text-sm">分析目标：{run.analysis_goal || "未指定"}</p>
          </div>
          <div className={`ml-auto px-3 py-1 rounded-full text-sm font-medium ${getStatusColor()}`}>
            {run.status === "completed" ? "已完成" : run.status === "running" ? "分析中..." : run.status === "failed" ? "失败" : "待处理"}
          </div>
          {isRunning && (
            <button onClick={loadRun} className="p-2 rounded-xl hover:bg-white/50 transition-colors">
              <RefreshCw className="text-primary-500 animate-spin" size={20} />
            </button>
          )}
        </div>

        {/* Progress tracker while running */}
        {isRunning && (
          <div className="mb-6">
            <ProgressTracker runId={run.id} onComplete={handleProgressComplete} />
          </div>
        )}

        {/* Error message */}
        {run.status === "failed" && run.error_message && (
          <div className="glass-card p-4 mb-6 bg-red-50">
            <div className="flex items-start gap-2 text-red-700">
              <AlertTriangle size={18} className="mt-0.5 flex-shrink-0" />
              <div>
                <p className="font-medium">分析失败</p>
                <p className="text-sm mt-1">{run.error_message}</p>
              </div>
            </div>
          </div>
        )}

        {/* Stats cards */}
        <div className="glass-card p-6 mb-6">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
            <div className="text-center">
              <p className="text-3xl font-bold text-primary-600">{run.total_reviews || reviews.length}</p>
              <p className="text-sm text-gray-500">总评论数</p>
            </div>
            <div className="text-center">
              <p className="text-3xl font-bold text-secondary-500">{run.cleaned_reviews || reviews.length}</p>
              <p className="text-sm text-gray-500">已清洗</p>
            </div>
            <div className="text-center">
              <p className="text-3xl font-bold text-green-500">{avgRating.toFixed(1)}</p>
              <p className="text-sm text-gray-500">平均评分</p>
            </div>
            <div className="text-center">
              <p className="text-3xl font-bold text-orange-500">{findings.length}</p>
              <p className="text-sm text-gray-500">问题发现</p>
            </div>
          </div>
          {findings.length > 0 && (assumptionCount > 0 || conflictCount > 0) && (
            <div className="mt-4 pt-4 border-t border-gray-100 flex justify-center gap-6 text-sm">
              {assumptionCount > 0 && (
                <span className="text-yellow-600 flex items-center gap-1">
                  <AlertTriangle size={14} />
                  {assumptionCount} 项标记为假设
                </span>
              )}
              {conflictCount > 0 && (
                <span className="text-red-500 flex items-center gap-1">
                  <ThumbsDown size={14} />
                  {conflictCount} 项存在冲突证据
                </span>
              )}
            </div>
          )}
        </div>

        <div className="flex gap-2 mb-6 overflow-x-auto pb-2">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            return (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key)}
                className={`flex items-center gap-2 px-4 py-2 rounded-xl whitespace-nowrap transition-all duration-300 ${
                  activeTab === tab.key
                    ? "bg-gradient-to-r from-primary-500 to-secondary-400 text-white shadow-lg"
                    : "bg-white/50 text-gray-600 hover:bg-white/70"
                }`}
              >
                <Icon size={16} />
                {tab.label}
              </button>
            );
          })}
        </div>

        <div className="glass-card p-6 min-h-[400px]">
          {activeTab === "summary" && (
            <div className="space-y-6">
              <div>
                <h3 className="text-lg font-semibold text-gray-800 mb-4">分析摘要</h3>
                <p className="text-gray-600 leading-relaxed">
                  本次分析针对「{run.app_name}」进行了全面的用户评论分析。共采集 {run.total_reviews || reviews.length} 条评论，
                  经过清洗后得到 {run.cleaned_reviews || reviews.length} 条有效评论。AI 模型识别出 {findings.length} 个核心问题，
                  并生成了 {requirements.length} 条产品需求和 {testCases.length} 条测试用例。
                </p>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="p-4 rounded-xl bg-primary-50">
                  <h4 className="font-medium text-primary-700 mb-2">下一步建议</h4>
                  <ul className="text-sm text-gray-600 space-y-2">
                    <li>• 查看「发现」标签页了解具体问题</li>
                    <li>• 验证每条发现的证据支持度</li>
                    <li>• 评审生成的 PRD 需求</li>
                    <li>• 确认测试用例覆盖范围</li>
                  </ul>
                </div>
                <div className="p-4 rounded-xl bg-secondary-50">
                  <h4 className="font-medium text-secondary-700 mb-2">数据概览</h4>
                  <ul className="text-sm text-gray-600 space-y-2">
                    <li>• 开始时间：{new Date(run.started_at).toLocaleString("zh-CN")}</li>
                    <li>• 完成时间：{run.completed_at ? new Date(run.completed_at).toLocaleString("zh-CN") : "未完成"}</li>
                    <li>• App ID：{run.app_id}</li>
                    <li>• 分析状态：{run.status === "completed" ? "已完成" : "进行中"}</li>
                  </ul>
                </div>
              </div>
            </div>
          )}

          {activeTab === "reviews" && (
            <div>
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-gray-800">评论列表</h3>
                <div className="relative">
                  <Star className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={16} />
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="搜索评论..."
                    className="input-glass pl-10 w-64"
                  />
                </div>
              </div>
              <div className="space-y-4">
                {filteredReviews.map((review) => (
                  <div key={review.id} className="p-4 rounded-xl bg-white/50 border border-white/50">
                    <div className="flex items-start justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <div className="flex">
                          {[1, 2, 3, 4, 5].map((star) => (
                            <Star
                              key={star}
                              size={14}
                              className={star <= review.rating ? "text-yellow-400 fill-yellow-400" : "text-gray-300"}
                            />
                          ))}
                        </div>
                        {review.version && (
                          <span className="text-xs text-gray-500">v{review.version}</span>
                        )}
                      </div>
                    </div>
                    {review.title && (
                      <h4 className="font-medium text-gray-800 mb-1">{review.title}</h4>
                    )}
                    <p className="text-sm text-gray-600">{review.content}</p>
                    <div className="flex items-center justify-between mt-2">
                      <span className="text-xs text-gray-400">{review.author}</span>
                      {review.date && (
                        <span className="text-xs text-gray-400">{new Date(review.date).toLocaleDateString("zh-CN")}</span>
                      )}
                    </div>
                  </div>
                ))}
                {filteredReviews.length === 0 && (
                  <div className="text-center py-12 text-gray-500">暂无评论数据</div>
                )}
              </div>
            </div>
          )}

          {activeTab === "findings" && (
            <div className="space-y-4">
              <h3 className="text-lg font-semibold text-gray-800 mb-4">问题发现</h3>
              {findings.length > 0 ? (
                findings.map((finding) => (
                  <div key={finding.id} className="p-5 rounded-xl bg-white/50 border border-white/50">
                    <div className="flex items-start justify-between mb-3">
                      <div className="flex items-center gap-2">
                        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary-500 to-secondary-400 flex items-center justify-center">
                          <Lightbulb className="text-white" size={16} />
                        </div>
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="font-medium text-gray-800">发现 #{finding.id}</span>
                            {finding.finding_type && (
                              <span className="text-xs px-2 py-0.5 rounded-full bg-blue-100 text-blue-600">
                                {finding.finding_type}
                              </span>
                            )}
                            {finding.is_assumption && (
                              <span className="text-xs px-2 py-0.5 rounded-full bg-yellow-100 text-yellow-700 flex items-center gap-1">
                                <AlertTriangle size={10} />
                                假设
                              </span>
                            )}
                            {finding.has_conflict && (
                              <span className="text-xs px-2 py-0.5 rounded-full bg-red-100 text-red-600">
                                存在冲突
                              </span>
                            )}
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center gap-4 text-sm">
                        <div className="flex items-center gap-1 text-green-600">
                          <ThumbsUp size={14} />
                          {finding.supporting_count}
                        </div>
                        <div className="flex items-center gap-1 text-red-500">
                          <ThumbsDown size={14} />
                          {finding.conflicting_count}
                        </div>
                        <span className="text-xs px-2 py-0.5 rounded-full bg-primary-100 text-primary-600">
                          置信度 {((finding.confidence || 0) * 100).toFixed(0)}%
                        </span>
                      </div>
                    </div>
                    <p className="text-gray-600">{finding.finding_text}</p>
                    {finding.evidence_review_ids && finding.evidence_review_ids.length > 0 && (
                      <div className="mt-3 pt-3 border-t border-gray-100">
                        <p className="text-xs text-gray-500 mb-1">证据评论 ID：</p>
                        <div className="flex flex-wrap gap-1">
                          {finding.evidence_review_ids.slice(0, 10).map((rid) => (
                            <span key={rid} className="text-xs px-2 py-0.5 rounded bg-gray-100 text-gray-600">
                              #{rid}
                            </span>
                          ))}
                          {finding.evidence_review_ids.length > 10 && (
                            <span className="text-xs text-gray-400">
                              +{finding.evidence_review_ids.length - 10} 更多
                            </span>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                ))
              ) : (
                <div className="text-center py-12 text-gray-500">
                  {run.status === "completed" ? "暂无发现数据" : "分析进行中，待完成后显示发现结果"}
                </div>
              )}
            </div>
          )}

          {activeTab === "prd" && (
            <div className="space-y-4">
              <h3 className="text-lg font-semibold text-gray-800 mb-4">产品需求文档</h3>
              {requirements.length > 0 ? (
                requirements.map((req) => (
                  <div key={req.id} className="p-5 rounded-xl bg-white/50 border border-white/50">
                    <div className="flex items-start justify-between mb-3">
                      <div>
                        <h4 className="font-medium text-gray-800">{req.requirement_text}</h4>
                        <div className="flex items-center gap-2 mt-1 flex-wrap">
                          {req.priority && (
                            <span className={`text-xs px-2 py-0.5 rounded-full ${
                              req.priority === "high" ? "bg-red-100 text-red-600"
                              : req.priority === "medium" ? "bg-yellow-100 text-yellow-600"
                              : "bg-gray-100 text-gray-600"
                            }`}>
                              {req.priority === "high" ? "高优先级" : req.priority === "medium" ? "中优先级" : "低优先级"}
                            </span>
                          )}
                          {req.requirement_type && (
                            <span className="text-xs px-2 py-0.5 rounded-full bg-blue-100 text-blue-600">
                              {req.requirement_type}
                            </span>
                          )}
                          <span className="text-xs px-2 py-0.5 rounded-full bg-primary-100 text-primary-600">
                            {req.version || "未分配版本"}
                          </span>
                          {req.finding_id && (
                            <span className="text-xs text-gray-500">来源发现 #{req.finding_id}</span>
                          )}
                        </div>
                      </div>
                    </div>
                    {req.description && (
                      <p className="text-gray-600 mt-2">{req.description}</p>
                    )}
                    {req.user_value && (
                      <div className="mt-2 text-sm">
                        <span className="text-gray-500">用户价值：</span>
                        <span className="text-gray-700">{req.user_value}</span>
                      </div>
                    )}
                  </div>
                ))
              ) : (
                <div className="text-center py-12 text-gray-500">
                  {run.status === "completed" ? "暂无 PRD 数据" : "分析进行中，待完成后显示 PRD"}
                </div>
              )}
            </div>
          )}

          {activeTab === "testcases" && (
            <div className="space-y-4">
              <h3 className="text-lg font-semibold text-gray-800 mb-4">测试用例</h3>
              {testCases.length > 0 ? (
                testCases.map((tc) => (
                  <div key={tc.id} className="p-5 rounded-xl bg-white/50 border border-white/50">
                    <div className="flex items-start justify-between mb-3">
                      <h4 className="font-medium text-gray-800">{tc.case_title}</h4>
                      <div className="flex items-center gap-2">
                        {tc.test_type && (
                          <span className="text-xs px-2 py-0.5 rounded-full bg-secondary-100 text-secondary-600">
                            {tc.test_type}
                          </span>
                        )}
                        <span className="text-xs px-2 py-0.5 rounded-full bg-gray-100 text-gray-600">
                          TC #{tc.id}
                        </span>
                      </div>
                    </div>
                    {tc.case_description && (
                      <p className="text-gray-600 mb-3">{tc.case_description}</p>
                    )}
                    {tc.test_steps && tc.test_steps.length > 0 && (
                      <div className="p-3 rounded-lg bg-gray-50 mb-3">
                        <p className="text-sm font-medium text-gray-700 mb-1">测试步骤</p>
                        <ol className="text-sm text-gray-600 list-decimal list-inside space-y-1">
                          {tc.test_steps.map((step, i) => (
                            <li key={i}>{step}</li>
                          ))}
                        </ol>
                      </div>
                    )}
                    <div className="p-3 rounded-lg bg-green-50">
                      <p className="text-sm font-medium text-gray-700 mb-1">预期结果</p>
                      <p className="text-sm text-gray-600">{tc.expected_result}</p>
                    </div>
                    {tc.requirement_id && (
                      <div className="mt-2 text-xs text-gray-500">
                        验证需求 #{tc.requirement_id}
                      </div>
                    )}
                  </div>
                ))
              ) : (
                <div className="text-center py-12 text-gray-500">
                  {run.status === "completed" ? "暂无测试用例数据" : "分析进行中，待完成后显示测试用例"}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
