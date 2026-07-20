import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Upload, FileJson, FileText, Play, Info, ArrowLeft } from "lucide-react";
import { apiClient } from "../api/client";
import { Loading } from "../components/Loading";

export const Import = () => {
  const navigate = useNavigate();
  const [file, setFile] = useState<File | null>(null);
  const [format, setFormat] = useState<"json" | "csv">("json");
  const [appId, setAppId] = useState("");
  const [importedAppId, setImportedAppId] = useState<string | null>(null);
  const [importedAppName, setImportedAppName] = useState<string>("");
  const [analysisGoal, setAnalysisGoal] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [importResult, setImportResult] = useState<{ count: number; appId: string; appName: string } | null>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = e.target.files?.[0];
    if (selected) {
      setFile(selected);
      // Auto-detect format from extension
      if (selected.name.endsWith(".csv")) {
        setFormat("csv");
      } else if (selected.name.endsWith(".json")) {
        setFormat("json");
      }
    }
  };

  const handleImport = async () => {
    if (!file) {
      setError("请选择文件");
      return;
    }
    setError("");
    setIsLoading(true);
    try {
      const result = await apiClient.importReviews(file, format, appId || undefined);
      setImportResult({
        count: result.reviews_imported,
        appId: result.app_id,
        appName: result.app_name,
      });
      setImportedAppId(result.app_id);
      setImportedAppName(result.app_name);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setIsLoading(false);
    }
  };

  const handleAnalyze = async () => {
    if (!importedAppId) {
      setError("请先导入数据");
      return;
    }
    setError("");
    setIsLoading(true);
    try {
      const response = await apiClient.analyzeImported(
        importedAppId,
        importedAppName || "Imported App",
        analysisGoal
      );
      navigate(`/runs/${response.run_id}`);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setIsLoading(false);
    }
  };

  const downloadSampleJson = () => {
    const sample = [
      {
        app_id: "1234567890",
        app_name: "Sample App",
        author: "User1",
        rating: 2,
        title: "Crashes on launch",
        content: "The app keeps crashing when I try to open it on iOS 17. Please fix.",
        review_date: "2024-01-15T10:30:00",
        app_version: "1.2.3",
      },
      {
        app_id: "1234567890",
        app_name: "Sample App",
        author: "User2",
        rating: 1,
        title: "Subscription scam",
        content: "Was charged for a subscription I never signed up for. Want a refund.",
        review_date: "2024-01-14T15:45:00",
        app_version: "1.2.3",
      },
    ];
    const blob = new Blob([JSON.stringify(sample, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "sample_reviews.json";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const downloadSampleCsv = () => {
    const sample = `app_id,app_name,author,rating,title,content,review_date,app_version
1234567890,Sample App,User1,2,Crashes on launch,"The app keeps crashing when I try to open it on iOS 17. Please fix.",2024-01-15T10:30:00,1.2.3
1234567890,Sample App,User2,1,Subscription scam,"Was charged for a subscription I never signed up for. Want a refund.",2024-01-14T15:45:00,1.2.3`;
    const blob = new Blob([sample], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "sample_reviews.csv";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="min-h-screen p-8 animate-fade-in">
      <div className="max-w-3xl mx-auto">
        <div className="flex items-center gap-4 mb-8">
          <button
            onClick={() => navigate("/")}
            className="p-2 rounded-xl hover:bg-white/50 transition-colors"
          >
            <ArrowLeft className="text-gray-600" size={20} />
          </button>
          <div>
            <h1 className="text-2xl font-bold text-gray-800">导入评论数据</h1>
            <p className="text-gray-500 text-sm">支持 JSON / CSV 格式的外部评论数据集</p>
          </div>
        </div>

        {/* Format documentation */}
        <div className="glass-card p-6 mb-6">
          <div className="flex items-start gap-3">
            <Info className="text-primary-500 mt-0.5" size={20} />
            <div className="flex-1">
              <h3 className="font-medium text-gray-800 mb-2">支持的格式</h3>
              <p className="text-sm text-gray-600 mb-3">
                文件必须包含以下字段（字段名兼容大小写和下划线/驼峰）：
              </p>
              <div className="grid grid-cols-2 gap-2 text-xs">
                <code className="p-2 rounded bg-gray-100 text-gray-700">app_id (必填)</code>
                <code className="p-2 rounded bg-gray-100 text-gray-700">author</code>
                <code className="p-2 rounded bg-gray-100 text-gray-700">rating (0-5)</code>
                <code className="p-2 rounded bg-gray-100 text-gray-700">title</code>
                <code className="p-2 rounded bg-gray-100 text-gray-700">content (必填)</code>
                <code className="p-2 rounded bg-gray-100 text-gray-700">review_date</code>
                <code className="p-2 rounded bg-gray-100 text-gray-700">app_version</code>
                <code className="p-2 rounded bg-gray-100 text-gray-700">app_name</code>
              </div>
              <div className="mt-3 flex gap-2">
                <button
                  onClick={downloadSampleJson}
                  className="text-xs px-3 py-1 rounded-lg bg-blue-50 text-blue-600 hover:bg-blue-100 flex items-center gap-1"
                >
                  <FileJson size={12} />
                  下载 JSON 示例
                </button>
                <button
                  onClick={downloadSampleCsv}
                  className="text-xs px-3 py-1 rounded-lg bg-green-50 text-green-600 hover:bg-green-100 flex items-center gap-1"
                >
                  <FileText size={12} />
                  下载 CSV 示例
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Import form */}
        <div className="glass-card p-6 mb-6">
          <h3 className="font-medium text-gray-800 mb-4">上传文件</h3>

          <div className="space-y-4">
            <div
              className="border-2 border-dashed border-gray-300 rounded-xl p-8 text-center hover:border-primary-400 transition-colors cursor-pointer"
              onClick={() => document.getElementById("file-input")?.click()}
            >
              <Upload className="mx-auto text-gray-400 mb-2" size={32} />
              <p className="text-sm text-gray-600">
                {file ? (
                  <span className="text-primary-600 font-medium">{file.name}</span>
                ) : (
                  "点击或拖拽文件到此处"
                )}
              </p>
              <p className="text-xs text-gray-400 mt-1">支持 .json 和 .csv 文件</p>
              <input
                id="file-input"
                type="file"
                accept=".json,.csv"
                onChange={handleFileChange}
                className="hidden"
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">文件格式</label>
                <select
                  value={format}
                  onChange={(e) => setFormat(e.target.value as "json" | "csv")}
                  className="input-glass w-full"
                >
                  <option value="json">JSON</option>
                  <option value="csv">CSV</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  App ID (可选，覆盖文件中的值)
                </label>
                <input
                  type="text"
                  value={appId}
                  onChange={(e) => setAppId(e.target.value)}
                  placeholder="例如: 839285684"
                  className="input-glass w-full"
                />
              </div>
            </div>

            {error && (
              <div className="p-3 rounded-xl bg-red-50 text-red-600 text-sm">{error}</div>
            )}

            <button
              onClick={handleImport}
              disabled={!file || isLoading}
              className="w-full gradient-btn flex items-center justify-center gap-2"
            >
              {isLoading ? (
                <Loading key="loading" text="" size="small" />
              ) : (
                <span key="normal" className="flex items-center justify-center gap-2">
                  <Upload size={16} />
                  导入数据
                </span>
              )}
            </button>
          </div>
        </div>

        {/* Import result & analysis trigger */}
        {importResult && (
          <div className="glass-card p-6">
            <div className={`p-4 rounded-xl mb-4 ${importResult.count > 0 ? "bg-green-50" : "bg-blue-50"}`}>
              <p className={`font-medium ${importResult.count > 0 ? "text-green-700" : "text-blue-700"}`}>
                {importResult.count > 0 ? "✓ 导入成功" : "ℹ 评论已存在"}
              </p>
              <p className="text-sm text-gray-600 mt-1">
                {importResult.count > 0 ? (
                  <>
                    共导入 <strong>{importResult.count}</strong> 条评论
                    （App: {importResult.appName}, ID: {importResult.appId}）
                  </>
                ) : (
                  <>
                    文件中的评论已存在，无需重复导入。可直接启动分析。
                    （App: {importResult.appName}, ID: {importResult.appId}）
                  </>
                )}
              </p>
            </div>

            <h3 className="font-medium text-gray-800 mb-3">开始分析（可选）</h3>
            <div className="space-y-3">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">分析目标</label>
                <textarea
                  value={analysisGoal}
                  onChange={(e) => setAnalysisGoal(e.target.value)}
                  placeholder="例如：分析订阅问题和功能可用性"
                  rows={2}
                  className="input-glass w-full resize-none"
                />
              </div>
              <button
                onClick={handleAnalyze}
                disabled={isLoading}
                className="w-full gradient-btn flex items-center justify-center gap-2"
              >
                {isLoading ? (
                  <Loading key="loading" text="" size="small" />
                ) : (
                  <span key="normal" className="flex items-center justify-center gap-2">
                    <Play size={16} />
                    开始分析导入的数据
                  </span>
                )}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
