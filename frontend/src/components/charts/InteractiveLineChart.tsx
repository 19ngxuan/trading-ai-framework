import { useEffect, useMemo, useRef } from "react";
import {
  ColorType,
  CrosshairMode,
  LineSeries,
  createChart,
  type LineData,
  type Time,
  type UTCTimestamp,
} from "lightweight-charts";

import {
  type ChartValueType,
  formatChartAxisValue,
  formatChartTime,
} from "./chartFormatters";

export type InteractiveChartPoint = {
  timestamp: string;
  value: number;
};

export type InteractiveChartSeries = {
  id: string | number;
  name: string;
  color: string;
  points: InteractiveChartPoint[];
};

type InteractiveLineChartProps = {
  series: InteractiveChartSeries[];
  valueType: ChartValueType;
  emptyMessage: string;
  className?: string;
  height?: number;
  loading?: boolean;
  error?: unknown;
  showLegend?: boolean;
};

type NormalizedSeries = {
  id: string | number;
  name: string;
  color: string;
  data: LineData<Time>[];
};

function timestampToTime(timestamp: string): UTCTimestamp | null {
  const parsed = Date.parse(timestamp);
  if (Number.isNaN(parsed)) return null;
  return Math.floor(parsed / 1000) as UTCTimestamp;
}

function normalizeSeries(series: InteractiveChartSeries[]): NormalizedSeries[] {
  return series
    .map((item) => {
      const byTimestamp = new Map<number, LineData<Time>>();
      for (const point of item.points) {
        if (!Number.isFinite(point.value)) continue;
        const time = timestampToTime(point.timestamp);
        if (time === null) continue;
        byTimestamp.set(time, { time, value: point.value });
      }
      return {
        id: item.id,
        name: item.name,
        color: item.color,
        data: Array.from(byTimestamp.entries())
          .sort(([left], [right]) => left - right)
          .map(([, dataPoint]) => dataPoint),
      };
    })
    .filter((item) => item.data.length > 0);
}

function errorMessage(error: unknown) {
  if (!error) return null;
  if (error instanceof Error) return error.message;
  return "Chart data could not be loaded.";
}

export function InteractiveLineChart({
  series,
  valueType,
  emptyMessage,
  className = "",
  height = 480,
  loading = false,
  error,
  showLegend = true,
}: InteractiveLineChartProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<HTMLDivElement | null>(null);
  const normalizedSeries = useMemo(() => normalizeSeries(series), [series]);
  const message = errorMessage(error);

  useEffect(() => {
    const container = chartRef.current;
    if (!container) return;

    const chart = createChart(container, {
      autoSize: true,
      height,
      layout: {
        background: { color: "#ffffff", type: ColorType.Solid },
        fontFamily:
          'Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
        textColor: "#405069",
      },
      grid: {
        horzLines: { color: "#e6ebf2" },
        vertLines: { color: "#edf1f6" },
      },
      crosshair: {
        mode: CrosshairMode.Normal,
      },
      localization: {
        priceFormatter: (value: number) => formatChartAxisValue(value, valueType),
        timeFormatter: (time: Time) => {
          if (typeof time === "number") return formatChartTime(time);
          return String(time);
        },
      },
      rightPriceScale: {
        borderColor: "#d8dee8",
      },
      timeScale: {
        borderColor: "#d8dee8",
        fixLeftEdge: false,
        fixRightEdge: false,
        rightOffset: 4,
        timeVisible: true,
      },
      handleScale: true,
      handleScroll: true,
    });

    for (const item of normalizedSeries) {
      const lineSeries = chart.addSeries(LineSeries, {
        color: item.color,
        lastValueVisible: false,
        lineWidth: 2,
        priceLineVisible: false,
        title: item.name,
      });
      lineSeries.setData(item.data);
    }

    chart.timeScale().fitContent();

    return () => {
      chart.remove();
    };
  }, [height, normalizedSeries, valueType]);

  return (
    <div className={`interactive-chart-shell ${className}`} ref={containerRef}>
      <div
        aria-label="Interactive time-series chart"
        className="interactive-chart"
        ref={chartRef}
        style={{ height }}
      />
      {(loading || message || normalizedSeries.length === 0) && (
        <div className="chart-empty overlay-empty">
          {loading ? "Loading chart data..." : message ?? emptyMessage}
        </div>
      )}
      {showLegend && normalizedSeries.length > 0 && (
        <div className="legend-row">
          {normalizedSeries.map((item) => (
            <span key={item.id}>
              <i style={{ background: item.color }} />
              {item.name}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
