import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { ArrowLeft, RefreshCw, MessageSquare, Lightbulb, FileCheck, GitBranch, Star, ThumbsUp, ThumbsDown } from "lucide-react";
import { Loading } from "../components/Loading";
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

  useEffect(() => {
    const fetchData = async () => {
      try {
        setIsLoading(true);
        const [runData, reviewsData] = await Promise.all([
          apiClient.getRunById(Number(id)),
          apiClient.getReviewsByRunId(Number(id)),
        ]);
        setRun(runData);
        setReviews(reviewsData);
      } catch (err) {
        console.error("Failed to fetch data:", err);
      } finally {
        setIsLoading(false);
      }
    };

    fetchData();
  }, [id]);

  useEffect(() => {
    if (run?.status === "completed") {
      fetchFindings();
      fetchRequirements();
      fetchTestCases();
    }
  }, [run?.status, id]);

  const fetchFindings = async () => {
    try {
      const response = await fetch(`http://localhost:8000/api/runs/${id}/findings`);
      if (response.ok) {
        setFindings(await response.json());
      }
    } catch (err) {
      console.error("Failed to fetch findings:", err);
    }
  };

  const fetchRequirements = async () => {
    try {
      const response = await fetch(`http://localhost:8000/api/runs/${id}/requirements`);
      if (response.ok) {
        setRequirements(await response.json());
      }
    } catch (err) {
      console.error("Failed to fetch requirements:", err);
    }
  };

  const fetchTestCases = async () => {
    try {
      const response = await fetch(`http://localhost:8000/api/runs/${id}/testcases`);
      if (response.ok) {
        setTestCases(await response.json());
      }
    } catch (err) {
      console.error("Failed to fetch test cases:", err);
    }
  };

  const filteredReviews = reviews.filter(
    (r) =>
      r.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      r.body.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const tabs = [
    { key: "summary", label: "概览", icon: MessageSquare },
    { key: "reviews", label: "评论", icon: Star },
    { key: "findings", label: "发现", icon: Lightbulb },
    { key: "prd", label: "PRD", icon: FileCheck },
    { key: "testcases", label: "测试用例", icon: GitBranch },
  ] as const;

  const getStatusColor = () => {
    switch (run?.status) {
      case "completed":
        return "bg-green-100 text-green-600";
      case "running":
        return "bg-primary-100 text-primary-600";
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

  const avgRating = reviews.length > 0
    ? reviews.reduce((sum, r) => sum + r.rating, 0) / reviews.length
    : 0;

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
            <p className="text-gray-500 text-sm">分析目标：{run.analysis_goal}</p>
          </div>
          <div className={`ml-auto px-3 py-1 rounded-full text-sm font-medium ${getStatusColor()}`}>
            {run.status === "completed" ? "已完成" : run.status === "running" ? "分析中..." : "待处理"}
          </div>
          {run.status === "running" && (
            <button onClick={() => window.location.reload()} className="p-2 rounded-xl hover:bg-white/50 transition-colors">
              <RefreshCw className="text-primary-500 animate-spin" size={20} />
            </button>
          )}
        </div>

        <div className="glass-card p-6 mb-6">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
            <div className="text-center">
              <p className="text-3xl font-bold text-primary-600">{run.total_reviews}</p>
              <p className="text-sm text-gray-500">总评论数</p>
            </div>
            <div className="text-center">
              <p className="text-3xl font-bold text-secondary-500">{run.cleaned_reviews}</p>
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
                  本次分析针对「{run.app_name}」进行了全面的用户评论分析。共采集 {run.total_reviews} 条评论，
                  经过清洗后得到 {run.cleaned_reviews} 条有效评论。AI 模型识别出 {findings.length} 个核心问题，
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
                        <span className="text-xs text-gray-500">{review.version}</span>
                      </div>
                      <span className={`text-xs px-2 py-1 rounded-full ${review.sentiment === "positive" ? "bg-green-100 text-green-600" : review.sentiment === "negative" ? "bg-red-100 text-red-600" : "bg-gray-100 text-gray-600"}`}>
                        {review.sentiment === "positive" ? "正面" : review.sentiment === "negative" ? "负面" : "中性"}
                      </span>
                    </div>
                    <h4 className="font-medium text-gray-800 mb-1">{review.title}</h4>
                    <p className="text-sm text-gray-600">{review.body}</p>
                    <div className="flex items-center justify-between mt-2">
                      <span className="text-xs text-gray-400">{review.author}</span>
                      <span className="text-xs text-gray-400">{new Date(review.date).toLocaleDateString("zh-CN")}</span>
                    </div>
                  </div>
                ))}
                {filteredReviews.length === 0 && (
                  <div className="text-center py-12 text-gray-500">
                    暂无评论数据
                  </div>
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
                            <span className="text-xs px-2 py-0.5 rounded-full bg-primary-100 text-primary-600">
                              置信度 {(finding.confidence * 100).toFixed(0)}%
                            </span>
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
                      </div>
                    </div>
                    <p className="text-gray-600">{finding.description}</p>
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
                        <h4 className="font-medium text-gray-800">{req.title}</h4>
                        <div className="flex items-center gap-2 mt-1">
                          <span className={`text-xs px-2 py-0.5 rounded-full ${req.priority === "high" ? "bg-red-100 text-red-600" : req.priority === "medium" ? "bg-yellow-100 text-yellow-600" : "bg-gray-100 text-gray-600"}`}>
                            {req.priority === "high" ? "高优先级" : req.priority === "medium" ? "中优先级" : "低优先级"}
                          </span>
                          <span className="text-xs px-2 py-0.5 rounded-full bg-primary-100 text-primary-600">
                            {req.version || "未分配版本"}
                          </span>
                        </div>
                      </div>
                    </div>
                    <p className="text-gray-600">{req.description}</p>
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
                      <h4 className="font-medium text-gray-800">{tc.title}</h4>
                      <span className="text-xs px-2 py-0.5 rounded-full bg-secondary-100 text-secondary-600">
                        TC #{tc.id}
                      </span>
                    </div>
                    <p className="text-gray-600 mb-3">{tc.description}</p>
                    <div className="p-3 rounded-lg bg-gray-50">
                      <p className="text-sm font-medium text-gray-700 mb-1">预期结果</p>
                      <p className="text-sm text-gray-600">{tc.expected_result}</p>
                    </div>
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
