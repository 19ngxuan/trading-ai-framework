import { useId } from "react";

export type ChartPoint = {
  label: string;
  value: number;
};

export type ChartSeries = {
  id: string | number;
  name: string;
  color: string;
  points: ChartPoint[];
};

type SvgLineChartProps = {
  series: ChartSeries[];
  valueFormat: "currency" | "percent" | "number";
  emptyMessage: string;
  className?: string;
  height?: number;
  xAxisLabel?: string;
  yAxisLabel?: string;
  xTickFormat?: (label: string, points: ChartPoint[]) => string;
  yTickFormat?: (value: number) => string;
};

const width = 1000;
const defaultHeight = 460;
const defaultMargins = {
  top: 24,
  right: 24,
  bottom: 72,
  left: 112,
};

type ChartLayout = {
  chartHeight: number;
  plotHeight: number;
  plotWidth: number;
};

function layoutForHeight(chartHeight: number): ChartLayout {
  return {
    chartHeight,
    plotHeight: chartHeight - defaultMargins.top - defaultMargins.bottom,
    plotWidth: width - defaultMargins.left - defaultMargins.right,
  };
}

const dateFormatter = new Intl.DateTimeFormat(undefined, {
  month: "short",
  day: "2-digit",
  year: "numeric",
});
const monthYearFormatter = new Intl.DateTimeFormat(undefined, {
  month: "short",
  year: "numeric",
});
const currencyFormatter = new Intl.NumberFormat(undefined, {
  currency: "USD",
  maximumFractionDigits: 0,
  style: "currency",
});
const compactFormatter = new Intl.NumberFormat(undefined, {
  maximumFractionDigits: 2,
  notation: "compact",
});
const percentFormatter = new Intl.NumberFormat(undefined, {
  maximumFractionDigits: 2,
  style: "percent",
});

function formatValue(value: number, valueFormat: SvgLineChartProps["valueFormat"]) {
  if (valueFormat === "currency") return currencyFormatter.format(value);
  if (valueFormat === "percent") return percentFormatter.format(value);
  return compactFormatter.format(value);
}

function formatDateLabel(label: string, points: ChartPoint[]) {
  const parsed = new Date(label);
  if (!Number.isNaN(parsed.getTime())) {
    const parsedPoints = points
      .map((point) => new Date(point.label))
      .filter((date) => !Number.isNaN(date.getTime()));
    const sameMonth =
      parsedPoints.length > 0 &&
      parsedPoints.every(
        (date) =>
          date.getUTCFullYear() === parsed.getUTCFullYear() &&
          date.getUTCMonth() === parsed.getUTCMonth(),
      );
    return sameMonth
      ? dateFormatter.format(parsed)
      : monthYearFormatter.format(parsed);
  }
  return label.length > 10 ? label.slice(0, 10) : label;
}

function yDomain(values: number[]) {
  if (values.length === 0) return { min: 0, max: 1 };
  const min = Math.min(...values);
  const max = Math.max(...values);
  if (min === max) {
    const padding = Math.max(Math.abs(min) * 0.05, 1);
    return { min: min - padding, max: max + padding };
  }
  const padding = (max - min) * 0.08;
  return { min: min - padding, max: max + padding };
}

function yTicks(min: number, max: number) {
  const count = 5;
  return Array.from({ length: count }, (_, index) => {
    return min + ((max - min) / (count - 1)) * index;
  });
}

function xTicks(points: ChartPoint[], layout: ChartLayout) {
  if (points.length === 0) return [];
  const maxTicks = 6;
  if (points.length === 1) {
    return [
      {
        x: defaultMargins.left + layout.plotWidth / 2,
        label: points[0].label,
        index: 0,
      },
    ];
  }
  const tickCount = Math.min(maxTicks, Math.max(2, points.length));
  const indexes = new Set<number>();
  for (let tickIndex = 0; tickIndex < tickCount; tickIndex += 1) {
    indexes.add(
      Math.round((tickIndex / (tickCount - 1)) * (points.length - 1)),
    );
  }
  return Array.from(indexes)
    .sort((a, b) => a - b)
    .map((index) => ({
      x: pointX(index, points.length, layout),
      label: points[index].label,
      index,
    }));
}

function pointX(index: number, pointCount: number, layout: ChartLayout) {
  if (pointCount === 1) return defaultMargins.left + layout.plotWidth / 2;
  return defaultMargins.left + (index / (pointCount - 1)) * layout.plotWidth;
}

function pointY(value: number, min: number, max: number, layout: ChartLayout) {
  return (
    defaultMargins.top +
    layout.plotHeight -
    ((value - min) / (max - min)) * layout.plotHeight
  );
}

function buildPath(
  points: ChartPoint[],
  min: number,
  max: number,
  layout: ChartLayout,
) {
  return points
    .map((point, index) => {
      const x = pointX(index, points.length, layout);
      const y = pointY(point.value, min, max, layout);
      return `${index === 0 ? "M" : "L"} ${x.toFixed(2)} ${y.toFixed(2)}`;
    })
    .join(" ");
}

export function SvgLineChart({
  series,
  valueFormat,
  emptyMessage,
  className = "",
  height = defaultHeight,
  xAxisLabel = "Date",
  yAxisLabel,
  xTickFormat,
  yTickFormat,
}: SvgLineChartProps) {
  const layout = layoutForHeight(height);
  const clipId = useId();
  const drawableSeries = series.filter((item) => item.points.length > 0);
  const values = drawableSeries.flatMap((item) =>
    item.points.map((point) => point.value),
  );
  const { min, max } = yDomain(values);
  const longestSeries =
    drawableSeries
      .slice()
      .sort((a, b) => b.points.length - a.points.length)[0]?.points ?? [];

  return (
    <div className={`chart-shell ${className}`}>
      <svg
        className="line-chart"
        preserveAspectRatio="xMidYMid meet"
        role="img"
        style={{ aspectRatio: `${width} / ${layout.chartHeight}` }}
        viewBox={`0 0 ${width} ${layout.chartHeight}`}
      >
        <defs>
          <clipPath id={clipId}>
            <rect
              height={layout.plotHeight}
              width={layout.plotWidth}
              x={defaultMargins.left}
              y={defaultMargins.top}
            />
          </clipPath>
        </defs>

        <line
          className="chart-axis"
          x1={defaultMargins.left}
          x2={defaultMargins.left}
          y1={defaultMargins.top}
          y2={defaultMargins.top + layout.plotHeight}
        />
        <line
          className="chart-axis"
          x1={defaultMargins.left}
          x2={defaultMargins.left + layout.plotWidth}
          y1={defaultMargins.top + layout.plotHeight}
          y2={defaultMargins.top + layout.plotHeight}
        />

        {yTicks(min, max).map((tick) => {
          const y = pointY(tick, min, max, layout);
          return (
            <g key={tick}>
              <line
                className="chart-grid"
                x1={defaultMargins.left}
                x2={defaultMargins.left + layout.plotWidth}
                y1={y}
                y2={y}
              />
              <line
                className="chart-tick"
                x1={defaultMargins.left - 5}
                x2={defaultMargins.left}
                y1={y}
                y2={y}
              />
              <text
                className="chart-label"
                textAnchor="end"
                x={defaultMargins.left - 10}
                y={y + 4}
              >
                {yTickFormat ? yTickFormat(tick) : formatValue(tick, valueFormat)}
              </text>
            </g>
          );
        })}

        {xTicks(longestSeries, layout).map((tick) => (
          <g key={`${tick.label}-${tick.index}`}>
            <line
              className="chart-tick"
              x1={tick.x}
              x2={tick.x}
              y1={defaultMargins.top + layout.plotHeight}
              y2={defaultMargins.top + layout.plotHeight + 5}
            />
            <text
              className="chart-label"
              textAnchor={
                tick.index === 0
                  ? "start"
                  : tick.index === longestSeries.length - 1
                    ? "end"
                    : "middle"
              }
              x={tick.x}
              y={defaultMargins.top + layout.plotHeight + 24}
            >
              {xTickFormat
                ? xTickFormat(tick.label, longestSeries)
                : formatDateLabel(tick.label, longestSeries)}
            </text>
          </g>
        ))}

        <text
          className="chart-axis-title"
          textAnchor="middle"
          x={defaultMargins.left + layout.plotWidth / 2}
          y={layout.chartHeight - 18}
        >
          {xAxisLabel}
        </text>
        {yAxisLabel && (
          <text
            className="chart-axis-title"
            textAnchor="middle"
            transform={`translate(20 ${
              defaultMargins.top + layout.plotHeight / 2
            }) rotate(-90)`}
          >
            {yAxisLabel}
          </text>
        )}

        <g clipPath={`url(#${clipId})`}>
          {drawableSeries.map((item) => (
            <path
              key={item.id}
              d={buildPath(item.points, min, max, layout)}
              fill="none"
              stroke={item.color}
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth="3"
            />
          ))}
        </g>
      </svg>
      {drawableSeries.length === 0 && (
        <div className="chart-empty overlay-empty">{emptyMessage}</div>
      )}
    </div>
  );
}
