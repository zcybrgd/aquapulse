export function formatNumber(value: number, fractionDigits = 0): string {
  return new Intl.NumberFormat("en-GB", {
    minimumFractionDigits: fractionDigits,
    maximumFractionDigits: fractionDigits,
  }).format(value);
}

export function formatPercent(value: number, fractionDigits = 1): string {
  return `${formatNumber(value, fractionDigits)}%`;
}

export function formatChartTime(timestamp: string): string {
  return new Intl.DateTimeFormat("en-GB", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(new Date(timestamp));
}

export function formatChartBucket(timestamp: string, range: string): string {
  const date = new Date(timestamp);
  if (range === "30d") {
    return new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "short" }).format(date);
  }
  if (range === "7d") {
    return new Intl.DateTimeFormat("en-GB", {
      day: "numeric",
      month: "short",
      hour: "2-digit",
      hour12: false,
    }).format(date);
  }
  return formatChartTime(timestamp);
}

export function formatDisplayDate(date: Date): string {
  return new Intl.DateTimeFormat("en-GB", {
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
  }).format(date);
}

export function greetingForHour(hour: number): string {
  if (hour < 12) {
    return "Good morning";
  }
  if (hour < 18) {
    return "Good afternoon";
  }
  return "Good evening";
}

export function formatDisplayDay(timestamp: string): string {
  return new Intl.DateTimeFormat("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
  }).format(new Date(timestamp));
}

export function formatDateTime(timestamp: string): string {
  return new Intl.DateTimeFormat("en-GB", {
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(new Date(timestamp));
}

export function formatSignedNumber(value: number, fractionDigits = 1, unit = ""): string {
  const formatted = formatNumber(Math.abs(value), fractionDigits);
  const sign = value > 0 ? "+" : value < 0 ? "−" : "";
  return `${sign}${formatted}${unit ? ` ${unit}` : ""}`;
}

export function formatRelativeTime(timestamp: string | null, now = new Date()): string {
  if (!timestamp) {
    return "never";
  }
  const deltaMs = now.getTime() - new Date(timestamp).getTime();
  const seconds = Math.max(0, Math.round(deltaMs / 1000));
  if (seconds < 60) {
    return "just now";
  }
  const minutes = Math.round(seconds / 60);
  if (minutes < 60) {
    return `${minutes} min ago`;
  }
  const hours = Math.round(minutes / 60);
  if (hours < 48) {
    return `${hours} h ago`;
  }
  return formatDateTime(timestamp);
}

export function isSameLocalDay(timestamp: string, now = new Date()): boolean {
  const date = new Date(timestamp);
  return (
    date.getFullYear() === now.getFullYear() &&
    date.getMonth() === now.getMonth() &&
    date.getDate() === now.getDate()
  );
}
