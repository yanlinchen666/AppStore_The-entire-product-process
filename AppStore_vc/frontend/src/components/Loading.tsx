interface LoadingProps {
  text?: string;
  size?: "small" | "medium" | "large";
}

export const Loading = ({ text = "加载中...", size = "medium" }: LoadingProps) => {
  const sizeClasses = {
    small: "w-6 h-6",
    medium: "w-10 h-10",
    large: "w-16 h-16",
  };

  const textSizeClasses = {
    small: "text-sm",
    medium: "text-base",
    large: "text-lg",
  };

  return (
    <div className="flex flex-col items-center justify-center gap-4">
      <div className={`relative ${sizeClasses[size]}`}>
        <div className="absolute inset-0 rounded-full border-4 border-primary-200" />
        <div className="absolute inset-0 rounded-full border-4 border-primary-500 border-t-transparent animate-spin" />
        <div className="absolute inset-2 rounded-full border-4 border-secondary-200 border-t-transparent animate-spin" style={{ animationDirection: "reverse", animationDuration: "1.5s" }} />
      </div>
      <p className={`${textSizeClasses[size]} text-gray-500 font-medium`}>{text}</p>
    </div>
  );
};

export const LoadingSkeleton = () => (
  <div className="space-y-4">
    {[1, 2, 3].map((i) => (
      <div key={i} className="glass-card p-6">
        <div className="flex items-center justify-between">
          <div className="space-y-3">
            <div className="w-32 h-4 shimmer rounded-lg" />
            <div className="w-48 h-3 shimmer rounded-lg" />
          </div>
          <div className="w-12 h-12 shimmer rounded-xl" />
        </div>
      </div>
    ))}
  </div>
);
