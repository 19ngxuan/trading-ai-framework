export type ChartValueType = "currency" | "percent" | "number";

const currencyFormatter = new Intl.NumberFormat(undefined, {
  currency: "USD",
  maximumFractionDigits: 2,
  style: "currency",
});

const compactCurrencyFormatter = new Intl.NumberFormat(undefined, {
  currency: "USD",
  maximumFractionDigits: 0,
  notation: "compact",
  style: "currency",
});

const percentFormatter = new Intl.NumberFormat(undefined, {
  maximumFractionDigits: 2,
  style: "percent",
});

const compactNumberFormatter = new Intl.NumberFormat(undefined, {
  maximumFractionDigits: 2,
  notation: "compact",
});

const dateTimeFormatter = new Intl.DateTimeFormat(undefined, {
  day: "2-digit",
  hour: "2-digit",
  minute: "2-digit",
  month: "short",
  year: "numeric",
});

export function formatChartValue(value: number, valueType: ChartValueType) {
  if (valueType === "currency") return currencyFormatter.format(value);
  if (valueType === "percent") return percentFormatter.format(value);
  return compactNumberFormatter.format(value);
}

export function formatChartAxisValue(value: number, valueType: ChartValueType) {
  if (valueType === "currency") return compactCurrencyFormatter.format(value);
  return formatChartValue(value, valueType);
}

export function formatChartTime(timestampSeconds: number) {
  return dateTimeFormatter.format(new Date(timestampSeconds * 1000));
}

