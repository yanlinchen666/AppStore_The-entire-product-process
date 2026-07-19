import { LucideIcon } from "lucide-react";
import { useEffect, useState } from "react";

interface StatCardProps {
  title: string;
  value: number;
  icon: LucideIcon;
  color: "primary" | "secondary" | "green" | "orange";
  suffix?: string;
}

export const StatCard = ({ title, value, icon: Icon, color, suffix = "" }: StatCardProps) => {
  const [displayValue, setDisplayValue] = useState(0);

  useEffect(() => {
    const duration = 1000;
    const steps = 60;
    const increment = value / steps;
    let current = 0;

    const timer = setInterval(() => {
      current += increment;
      if (current >= value) {
        setDisplayValue(value);
        clearInterval(timer);
      } else {
        setDisplayValue(Math.floor(current));
      }
    }, duration / steps);

    return () => clearInterval(timer);
  }, [value]);

  const colorClasses = {
    primary: {
      bg: "from-primary-500 to-primary-600",
      text: "text-primary-600",
      light: "bg-primary-50",
    },
    secondary: {
      bg: "from-secondary-400 to-secondary-500",
      text: "text-secondary-500",
      light: "bg-secondary-50",
    },
    green: {
      bg: "from-green-400 to-green-500",
      text: "text-green-500",
      light: "bg-green-50",
    },
    orange: {
      bg: "from-orange-400 to-orange-500",
      text: "text-orange-500",
      light: "bg-orange-50",
    },
  };

  const colors = colorClasses[color];

  return (
    <div className="glass-card p-6 hover:shadow-card transition-all duration-500 hover:-translate-y-1 group">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-gray-500 mb-1">{title}</p>
          <p className={`text-3xl font-bold ${colors.text}`}>
            {displayValue.toLocaleString()}{suffix}
          </p>
        </div>
        <div className={`w-14 h-14 rounded-2xl bg-gradient-to-br ${colors.bg} flex items-center justify-center shadow-lg group-hover:scale-110 transition-transform duration-300`}>
          <Icon className="text-white" size={24} />
        </div>
      </div>
    </div>
  );
};
