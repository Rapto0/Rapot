"use client";

import {
  LineChart,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  BarChart,
  Bar
} from "recharts";

import { performanceSeries } from "@/lib/mock-data";

const tooltipStyle = {
  backgroundColor: "#0e1117",
  border: "1px solid rgba(255,255,255,0.1)",
  borderRadius: 8
};

export function PerformanceChart() {
  return (
    <div className="grid gap-4 md:grid-cols-2">
      <div className="h-44">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={performanceSeries}>
            <XAxis dataKey="name" stroke="#5b6470" fontSize={10} />
            <YAxis stroke="#5b6470" fontSize={10} />
            <Tooltip contentStyle={tooltipStyle} />
            <Line type="monotone" dataKey="pnl" stroke="#2962ff" strokeWidth={2} />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <div className="h-44">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={performanceSeries}>
            <XAxis dataKey="name" stroke="#5b6470" fontSize={10} />
            <YAxis stroke="#5b6470" fontSize={10} />
            <Tooltip contentStyle={tooltipStyle} />
            <Bar dataKey="trades" fill="#00c853" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
