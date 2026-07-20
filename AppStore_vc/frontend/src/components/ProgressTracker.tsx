import { useEffect, useState, useRef } from "react";
import { CheckCircle2, Loader2, XCircle, Circle } from "lucide-react";
import { apiClient } from "../api/client";
import type { ProgressEvent } from "../api/types";

interface ProgressTrackerProps {
  runId: number;
  onComplete: () => void;
}

// Stage display configuration
const STAGE_LABELS: Record<string, { label: string; description: string }> = {
  collection: { label: "数据采集", description: "从 App Store 抓取评论" },
  cleaning: { label: "评论清洗", description: "去重、语言检测、情感分析" },
  vector_index: { label: "向量索引", description: "构建 BGE-M3 向量索引" },
  topic_extraction: { label: "主题发现", description: "LLM 动态提取主题" },
  finding_generation: { label: "问题发现", description: "LLM 生成发现" },
  evidence_validation: { label: "证据验证", description: "向量检索验证证据" },
  prd_generation: { label: "PRD 生成", description: "LLM 生成产品需求" },
  version_planning: { label: "版本规划", description: "需求拆分到版本" },
  testcase_generation: { label: "测试用例", description: "LLM 生成测试用例" },
  traceability: { label: "追溯链", description: "构建完整追溯链" },
};

// Ordered stages
const STAGE_ORDER = [
  "collection",
  "cleaning",
  "vector_index",
  "topic_extraction",
  "finding_generation",
  "evidence_validation",
  "prd_generation",
  "testcase_generation",
  "traceability",
];

export const ProgressTracker = ({ runId, onComplete }: ProgressTrackerProps) => {
  const [events, setEvents] = useState<ProgressEvent[]>([]);
  const [progress, setProgress] = useState(0);
  const [isDone, setIsDone] = useState(false);
  const [currentStage, setCurrentStage] = useState<string | null>(null);
  const pollRef = useRef<number | null>(null);

  useEffect(() => {
    let cancelled = false;

    const poll = async () => {
      try {
        const data = await apiClient.getAnalysisProgress(runId);
        if (cancelled) return;

        setEvents(data.events);
        setProgress(data.progress);
        setIsDone(data.is_completed);
        setCurrentStage(data.current_stage);

        if (data.is_completed) {
          if (pollRef.current) {
            window.clearInterval(pollRef.current);
            pollRef.current = null;
          }
          // Give a moment for the final state to render
          setTimeout(() => onComplete(), 800);
        }
      } catch (err) {
        console.error("Failed to poll progress:", err);
      }
    };

    poll();
    pollRef.current = window.setInterval(poll, 1500);

    return () => {
      cancelled = true;
      if (pollRef.current) {
        window.clearInterval(pollRef.current);
      }
    };
  }, [runId, onComplete]);

  // Compute status per stage
  const stageStatus = (stage: string): "pending" | "started" | "completed" | "failed" => {
    const stageEvents = events.filter((e) => e.stage === stage);
    if (stageEvents.length === 0) return "pending";
    const last = stageEvents[stageEvents.length - 1];
    return last.status as "started" | "completed" | "failed";
  };

  const lastEvent = events[events.length - 1];
  const hasFailure = events.some((e) => e.status === "failed");

  return (
    <div className="glass-card p-6 max-w-3xl mx-auto">
      <div className="mb-6">
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-lg font-semibold text-gray-800">分析进度</h3>
          <span className="text-sm font-medium text-primary-600">
            {(progress * 100).toFixed(0)}%
          </span>
        </div>
        <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
          <div
            className={`h-full transition-all duration-500 ${
              hasFailure
                ? "bg-gradient-to-r from-red-400 to-red-500"
                : "bg-gradient-to-r from-primary-500 to-secondary-400"
            }`}
            style={{ width: `${progress * 100}%` }}
          />
        </div>
      </div>

      <div className="space-y-3">
        {STAGE_ORDER.map((stage) => {
          const status = stageStatus(stage);
          const config = STAGE_LABELS[stage] || { label: stage, description: "" };
          const stageEvents = events.filter((e) => e.stage === stage);
          const lastStageEvent = stageEvents[stageEvents.length - 1];

          return (
            <div
              key={stage}
              className={`flex items-start gap-3 p-3 rounded-xl transition-all ${
                status === "completed"
                  ? "bg-green-50"
                  : status === "failed"
                  ? "bg-red-50"
                  : status === "started"
                  ? "bg-primary-50"
                  : "bg-gray-50 opacity-60"
              }`}
            >
              <div className="mt-0.5">
                {status === "completed" ? (
                  <CheckCircle2 className="text-green-500" size={20} />
                ) : status === "failed" ? (
                  <XCircle className="text-red-500" size={20} />
                ) : status === "started" ? (
                  <Loader2 className="text-primary-500 animate-spin" size={20} />
                ) : (
                  <Circle className="text-gray-400" size={20} />
                )}
              </div>
              <div className="flex-1">
                <div className="flex items-center justify-between">
                  <span className="font-medium text-gray-800">{config.label}</span>
                  <span className="text-xs text-gray-500">{stage}</span>
                </div>
                <p className="text-sm text-gray-500 mt-0.5">{config.description}</p>
                {lastStageEvent?.message && (
                  <p
                    className={`text-xs mt-1 ${
                      status === "failed" ? "text-red-600" : "text-gray-600"
                    }`}
                  >
                    {lastStageEvent.message}
                  </p>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {isDone && !hasFailure && (
        <div className="mt-6 p-4 rounded-xl bg-green-50 text-green-700 text-sm text-center">
          ✅ 分析完成！正在加载结果...
        </div>
      )}
      {hasFailure && (
        <div className="mt-6 p-4 rounded-xl bg-red-50 text-red-700 text-sm">
          ❌ 分析过程中出现错误。{lastEvent?.message}
        </div>
      )}
    </div>
  );
};
