import { useEffect, useState } from "react";
import { GitBranch, MessageSquare, Lightbulb, FileCheck, TestTube, ArrowRight, Search } from "lucide-react";
import { apiClient } from "../api/client";
import type { AnalysisRun, Review, Finding, Requirement, TestCase } from "../api/types";
import { Loading } from "../components/Loading";
import { useAnalysisStore } from "../store/analysisStore";

interface TraceNode {
  type: "review" | "finding" | "requirement" | "testcase";
  id: number;
  title: string;
  content: string;
  children?: TraceNode[];
}

export const Traceability = () => {
  const { runs, fetchRuns } = useAnalysisStore();
  const [selectedRun, setSelectedRun] = useState<AnalysisRun | null>(null);
  const [traceNodes, setTraceNodes] = useState<TraceNode[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");

  useEffect(() => {
    fetchRuns();
  }, [fetchRuns]);

  useEffect(() => {
    if (selectedRun) {
      fetchTraceabilityData(selectedRun.id);
    }
  }, [selectedRun]);

  const fetchTraceabilityData = async (runId: number) => {
    try {
      setIsLoading(true);
      const [reviews, findings, requirements, testCases] = await Promise.all([
        apiClient.getReviewsByRunId(runId),
        fetch(`http://localhost:8000/api/runs/${runId}/findings`).then((r) => r.ok ? r.json() : []),
        fetch(`http://localhost:8000/api/runs/${runId}/requirements`).then((r) => r.ok ? r.json() : []),
        fetch(`http://localhost:8000/api/runs/${runId}/testcases`).then((r) => r.ok ? r.json() : []),
      ]);

      const nodes = reviews.slice(0, 10).map((review: Review) => ({
        type: "review" as const,
        id: review.id,
        title: review.title,
        content: review.body.substring(0, 100) + "...",
        children: findings
          .slice(0, 3)
          .map((finding: Finding) => ({
            type: "finding" as const,
            id: finding.id,
            title: `发现 ${finding.id}`,
            content: finding.description.substring(0, 80) + "...",
            children: requirements
              .filter((req: Requirement) => req.finding_id === finding.id)
              .slice(0, 2)
              .map((req: Requirement) => ({
                type: "requirement" as const,
                id: req.id,
                title: req.title,
                content: req.description.substring(0, 80) + "...",
                children: testCases
                  .filter((tc: TestCase) => tc.requirement_id === req.id)
                  .slice(0, 2)
                  .map((tc: TestCase) => ({
                    type: "testcase" as const,
                    id: tc.id,
                    title: tc.title,
                    content: tc.description.substring(0, 60) + "...",
                  })),
              })),
          })),
      }));

      setTraceNodes(nodes);
    } catch (err) {
      console.error("Failed to fetch traceability data:", err);
    } finally {
      setIsLoading(false);
    }
  };

  const getNodeStyle = (type: TraceNode["type"]) => {
    const styles = {
      review: {
        bg: "bg-blue-50",
        border: "border-blue-200",
        icon: MessageSquare,
        iconBg: "bg-blue-500",
        label: "评论",
      },
      finding: {
        bg: "bg-purple-50",
        border: "border-purple-200",
        icon: Lightbulb,
        iconBg: "bg-purple-500",
        label: "发现",
      },
      requirement: {
        bg: "bg-green-50",
        border: "border-green-200",
        icon: FileCheck,
        iconBg: "bg-green-500",
        label: "需求",
      },
      testcase: {
        bg: "bg-orange-50",
        border: "border-orange-200",
        icon: TestTube,
        iconBg: "bg-orange-500",
        label: "测试用例",
      },
    };
    return styles[type];
  };

  const renderNode = (node: TraceNode, level: number = 0) => {
    const style = getNodeStyle(node.type);
    const Icon = style.icon;

    return (
      <div key={`${node.type}-${node.id}`} className="relative">
        <div
          className={`p-4 rounded-xl ${style.bg} border ${style.border} hover:shadow-md transition-all duration-300`}
          style={{ marginLeft: `${level * 32}px` }}
        >
          <div className="flex items-start gap-3">
            <div className={`w-8 h-8 rounded-lg ${style.iconBg} flex items-center justify-center flex-shrink-0`}>
              <Icon className="text-white" size={14} />
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="text-xs px-2 py-0.5 rounded-full bg-white/60 text-gray-600">
                  {style.label}
                </span>
              </div>
              <h4 className="font-medium text-gray-800 mt-1 truncate">{node.title}</h4>
              <p className="text-sm text-gray-600 mt-1 line-clamp-2">{node.content}</p>
            </div>
          </div>
        </div>

        {node.children && node.children.length > 0 && (
          <div className="mt-2">
            {node.children.map((child, index) => (
              <div key={`${child.type}-${child.id}`}>
                {index > 0 && (
                  <div className="absolute left-[28px] top-0 bottom-0 w-0.5 bg-gray-200" style={{ marginLeft: `${(level) * 32}px` }} />
                )}
                <div className="flex items-center" style={{ marginLeft: `${level * 32}px` }}>
                  <div className="w-4 h-0.5 bg-gray-300" />
                  <ArrowRight className="text-gray-400" size={14} />
                </div>
                {renderNode(child, level + 1)}
              </div>
            ))}
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="min-h-screen p-8 animate-fade-in">
      <div className="max-w-6xl mx-auto">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-800 mb-2">追溯链</h1>
          <p className="text-gray-500">查看评论 → 发现 → 需求 → 测试用例的完整追溯链路</p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-1">
            <div className="glass-card p-6">
              <h3 className="font-semibold text-gray-800 mb-4">选择分析任务</h3>
              {runs.length > 0 ? (
                <div className="space-y-2">
                  {runs.map((run) => (
                    <button
                      key={run.id}
                      onClick={() => setSelectedRun(run)}
                      className={`w-full p-3 rounded-xl text-left transition-all duration-300 ${
                        selectedRun?.id === run.id
                          ? "bg-gradient-to-r from-primary-500/20 to-secondary-400/20 border border-primary-200"
                          : "bg-white/50 hover:bg-white/70"
                      }`}
                    >
                      <p className="font-medium text-gray-800 truncate">{run.app_name}</p>
                      <p className="text-xs text-gray-500">{run.analysis_goal.substring(0, 30)}...</p>
                    </button>
                  ))}
                </div>
              ) : (
                <div className="text-center py-8 text-gray-500">
                  暂无分析任务
                </div>
              )}
            </div>
          </div>

          <div className="lg:col-span-2">
            <div className="glass-card p-6">
              <div className="flex items-center justify-between mb-6">
                <div className="flex items-center gap-2">
                  <GitBranch className="text-primary-500" size={20} />
                  <h3 className="font-semibold text-gray-800">追溯链可视化</h3>
                </div>
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={16} />
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="搜索节点..."
                    className="input-glass pl-10 w-64"
                  />
                </div>
              </div>

              <div className="flex items-center gap-4 mb-6 p-4 rounded-xl bg-gray-50">
                {[
                  { type: "review", label: "评论", color: "bg-blue-500" },
                  { type: "finding", label: "发现", color: "bg-purple-500" },
                  { type: "requirement", label: "需求", color: "bg-green-500" },
                  { type: "testcase", label: "测试用例", color: "bg-orange-500" },
                ].map((item) => (
                  <div key={item.type} className="flex items-center gap-2">
                    <div className={`w-3 h-3 rounded-full ${item.color}`} />
                    <span className="text-sm text-gray-600">{item.label}</span>
                  </div>
                ))}
              </div>

              {isLoading ? (
                <div className="flex items-center justify-center py-16">
                  <Loading text="加载追溯链数据..." />
                </div>
              ) : selectedRun ? (
                <div className="space-y-4 max-h-[600px] overflow-y-auto pr-2">
                  {traceNodes.length > 0 ? (
                    traceNodes.map((node) => renderNode(node))
                  ) : (
                    <div className="text-center py-16 text-gray-500">
                      <GitBranch className="mx-auto mb-4 text-gray-300" size={48} />
                      <p>暂无追溯链数据</p>
                      <p className="text-sm mt-1">请先完成分析任务</p>
                    </div>
                  )}
                </div>
              ) : (
                <div className="text-center py-16 text-gray-500">
                  <GitBranch className="mx-auto mb-4 text-gray-300" size={48} />
                  <p>请从左侧选择一个分析任务</p>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
