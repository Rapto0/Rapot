'use client';

import { useEffect, useRef, memo } from 'react';
import { createChart, ColorType, type IChartApi, LineSeries } from 'lightweight-charts';

interface MiniSparklineProps {
    data: number[];
    trend?: 'up' | 'down' | 'neutral';
    width?: number;
    height?: number;
    className?: string;
}

export const MiniSparkline = memo(function MiniSparkline({
    data,
    trend = 'neutral',
    width = 100,
    height = 40,
    className,
}: MiniSparklineProps) {
    const chartContainerRef = useRef<HTMLDivElement>(null);
    const chartRef = useRef<IChartApi | null>(null);

    // Determine color based on trend
    const getColor = () => {
        switch (trend) {
            case 'up':
                return '#00c853'; // profit green
            case 'down':
                return '#ff3d00'; // loss red
            default:
                return '#8b949e'; // neutral gray
        }
    };

    useEffect(() => {
        if (!chartContainerRef.current || data.length === 0) return;

        // Create chart
        const chart = createChart(chartContainerRef.current, {
            width,
            height,
            layout: {
                background: { type: ColorType.Solid, color: 'transparent' },
                textColor: 'transparent',
            },
            grid: {
                vertLines: { visible: false },
                horzLines: { visible: false },
            },
            rightPriceScale: {
                visible: false,
            },
            timeScale: {
                visible: false,
            },
            handleScale: false,
            handleScroll: false,
            crosshair: {
                vertLine: { visible: false },
                horzLine: { visible: false },
            },
        });

        chartRef.current = chart;

        // Add line series
        const color = getColor();
        const lineSeries = chart.addSeries(LineSeries, {
            color,
            lineWidth: 2,
            priceLineVisible: false,
            lastValueVisible: false,
            crosshairMarkerVisible: false,
        });

        // Transform data to chart format
        const now = new Date();
        const chartData = data.map((value, index) => ({
            time: Math.floor(now.getTime() / 1000) - (data.length - index) * 3600,
            value,
        }));

        lineSeries.setData(chartData as any);

        // Fit content
        chart.timeScale().fitContent();

        // Cleanup
        return () => {
            chart.remove();
        };
    }, [data, trend, width, height]);

    if (data.length === 0) {
        return (
            <div
                className={className}
                style={{ width, height }}
            />
        );
    }

    return (
        <div
            ref={chartContainerRef}
            className={className}
            style={{ width, height }}
        />
    );
});

// Simple SVG-based sparkline as fallback (lighter weight)
export function SimpleSparkline({
    data,
    trend = 'neutral',
    width = 100,
    height = 40,
    className,
}: MiniSparklineProps) {
    if (data.length < 2) {
        return <div className={className} style={{ width, height }} />;
    }

    const min = Math.min(...data);
    const max = Math.max(...data);
    const range = max - min || 1;

    // Normalize data points
    const points = data.map((value, index) => {
        const x = (index / (data.length - 1)) * width;
        const y = height - ((value - min) / range) * height * 0.8 - height * 0.1;
        return `${x},${y}`;
    }).join(' ');

    const getColor = () => {
        switch (trend) {
            case 'up':
                return '#00c853';
            case 'down':
                return '#ff3d00';
            default:
                return '#8b949e';
        }
    };

    return (
        <svg
            width={width}
            height={height}
            className={className}
            viewBox={`0 0 ${width} ${height}`}
        >
            <polyline
                fill="none"
                stroke={getColor()}
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
                points={points}
            />
        </svg>
    );
}
