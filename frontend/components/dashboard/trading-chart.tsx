"use client";

import { useEffect, useRef } from "react";
import { createChart, type IChartApi, type CandlestickData } from "lightweight-charts";

const candleData: CandlestickData[] = [
  { time: "2024-07-15", open: 118, high: 132, low: 112, close: 128 },
  { time: "2024-07-16", open: 128, high: 135, low: 120, close: 126 },
  { time: "2024-07-17", open: 126, high: 139, low: 122, close: 136 },
  { time: "2024-07-18", open: 136, high: 142, low: 130, close: 134 },
  { time: "2024-07-19", open: 134, high: 148, low: 133, close: 145 },
  { time: "2024-07-20", open: 145, high: 150, low: 138, close: 140 },
  { time: "2024-07-21", open: 140, high: 158, low: 139, close: 154 }
];

export function TradingChart() {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<IChartApi | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    const chart = createChart(containerRef.current, {
      layout: {
        background: { color: "#161b22" },
        textColor: "#c9d1d9"
      },
      grid: {
        vertLines: { color: "rgba(255,255,255,0.05)" },
        horzLines: { color: "rgba(255,255,255,0.05)" }
      },
      width: containerRef.current.clientWidth,
      height: 320,
      timeScale: { borderColor: "rgba(255,255,255,0.1)" },
      rightPriceScale: { borderColor: "rgba(255,255,255,0.1)" }
    });

    const series = chart.addCandlestickSeries({
      upColor: "#00c853",
      downColor: "#ff3d00",
      borderUpColor: "#00c853",
      borderDownColor: "#ff3d00",
      wickUpColor: "#00c853",
      wickDownColor: "#ff3d00"
    });

    series.setData(candleData);

    series.setMarkers([
      {
        time: "2024-07-16",
        position: "belowBar",
        color: "#2962ff",
        shape: "arrowUp",
        text: "BUY"
      },
      {
        time: "2024-07-19",
        position: "aboveBar",
        color: "#ff3d00",
        shape: "arrowDown",
        text: "SELL"
      }
    ]);

    chart.timeScale().fitContent();
    chartRef.current = chart;

    const handleResize = () => {
      if (!containerRef.current) return;
      chart.applyOptions({ width: containerRef.current.clientWidth });
    };

    window.addEventListener("resize", handleResize);

    return () => {
      window.removeEventListener("resize", handleResize);
      chart.remove();
    };
  }, []);

  return <div ref={containerRef} className="h-[320px] w-full" />;
}
