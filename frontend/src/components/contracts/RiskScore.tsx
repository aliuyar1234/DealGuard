'use client';

import { cn, getRiskLabel } from '@/lib/utils';

interface RiskScoreProps {
  score: number;
  level: 'low' | 'medium' | 'high' | 'critical';
  size?: 'sm' | 'md' | 'lg';
  showLabel?: boolean;
}

export function RiskScore({
  score,
  level,
  size = 'md',
  showLabel = true,
}: RiskScoreProps) {
  const getColor = () => {
    switch (level) {
      case 'low':
        return 'text-green-600';
      case 'medium':
        return 'text-yellow-600';
      case 'high':
        return 'text-orange-600';
      case 'critical':
        return 'text-red-600';
      default:
        return 'text-gray-600';
    }
  };

  const getBgColor = () => {
    switch (level) {
      case 'low':
        return 'bg-green-100';
      case 'medium':
        return 'bg-yellow-100';
      case 'high':
        return 'bg-orange-100';
      case 'critical':
        return 'bg-red-100';
      default:
        return 'bg-gray-100';
    }
  };

  const getStrokeColor = () => {
    switch (level) {
      case 'low':
        return '#22c55e';
      case 'medium':
        return '#eab308';
      case 'high':
        return '#f97316';
      case 'critical':
        return '#ef4444';
      default:
        return '#6b7280';
    }
  };

  const sizes = {
    sm: { width: 60, stroke: 4, fontSize: 'text-lg' },
    md: { width: 80, stroke: 6, fontSize: 'text-2xl' },
    lg: { width: 120, stroke: 8, fontSize: 'text-4xl' },
  };

  const { width, stroke, fontSize } = sizes[size];
  const radius = (width - stroke) / 2;
  const circumference = radius * 2 * Math.PI;
  const offset = circumference - (score / 100) * circumference;

  return (
    <div className="flex flex-col items-center">
      <div className="relative" style={{ width, height: width }}>
        {/* Background circle */}
        <svg className="w-full h-full -rotate-90">
          <circle
            cx={width / 2}
            cy={width / 2}
            r={radius}
            fill="none"
            stroke="#e5e7eb"
            strokeWidth={stroke}
          />
          {/* Progress circle */}
          <circle
            cx={width / 2}
            cy={width / 2}
            r={radius}
            fill="none"
            stroke={getStrokeColor()}
            strokeWidth={stroke}
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            strokeLinecap="round"
            className="transition-all duration-500"
          />
        </svg>
        {/* Score text */}
        <div
          className={cn(
            'absolute inset-0 flex items-center justify-center font-bold',
            fontSize,
            getColor()
          )}
        >
          {score}
        </div>
      </div>
      {showLabel && (
        <div
          className={cn(
            'mt-2 px-3 py-1 rounded-full text-sm font-medium',
            getBgColor(),
            getColor()
          )}
        >
          {getRiskLabel(level)}
        </div>
      )}
    </div>
  );
}
