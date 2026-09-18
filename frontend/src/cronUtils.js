// Friendly schedule <-> cron conversion for the common cases the UI offers.
// Anything the user builds through the picker maps to a valid 5-field cron string.

export function buildCron({ frequency, time, weekday }) {
  if (frequency === "manual") return "";

  const [hh, mm] = (time || "00:00").split(":").map(Number);

  if (frequency === "hourly") return `${mm} * * * *`;
  if (frequency === "daily") return `${mm} ${hh} * * *`;
  if (frequency === "weekly") return `${mm} ${hh} * * ${weekday ?? 0}`;
  return "";
}

// Best-effort parse back into the picker's shape; falls back to "custom" mode
// (raw cron shown as-is) for anything that doesn't match one of the presets above.
export function parseCron(cron) {
  if (!cron) return { frequency: "manual", time: "00:00", weekday: 0 };

  const parts = cron.trim().split(/\s+/);
  if (parts.length !== 5) return { frequency: "custom", raw: cron };

  const [min, hour, dom, month, dow] = parts;

  if (dom === "*" && month === "*" && dow === "*" && hour === "*") {
    return {
      frequency: "hourly",
      time: `00:${min.padStart(2, "0")}`,
      weekday: 0,
    };
  }
  if (dom === "*" && month === "*" && dow === "*") {
    return {
      frequency: "daily",
      time: `${hour.padStart(2, "0")}:${min.padStart(2, "0")}`,
      weekday: 0,
    };
  }
  if (dom === "*" && month === "*" && dow !== "*") {
    return {
      frequency: "weekly",
      time: `${hour.padStart(2, "0")}:${min.padStart(2, "0")}`,
      weekday: Number(dow),
    };
  }
  return { frequency: "custom", raw: cron };
}

export const WEEKDAYS = [
  "Sunday",
  "Monday",
  "Tuesday",
  "Wednesday",
  "Thursday",
  "Friday",
  "Saturday",
];
