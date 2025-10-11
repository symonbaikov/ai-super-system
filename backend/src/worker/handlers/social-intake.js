import { bus } from "../../server/sse.js";
import { METRICS } from "../../monitoring/prometheus.js";
import { postAlert } from "../alerts.js";

export async function handleSocialIntake(job) {
  const data = job.data || {};
  const events = Array.isArray(data.events) ? data.events : [];
  const candidateIds = Array.isArray(data.candidate_ids)
    ? data.candidate_ids
    : [];
  const source = data.source || "social";

  let emitted = 0;
  for (const raw of events) {
    const item = typeof raw === "object" && raw !== null ? raw : { value: raw };
    bus.emit("signal", {
      kind: "social_signal",
      t: Math.floor(Date.now() / 1000),
      meta: {
        source,
        candidate_ids: candidateIds,
        event: item,
      },
    });
    emitted++;
  }

  if (events.length === 0) {
    bus.emit("signal", {
      kind: "social_signal",
      t: Math.floor(Date.now() / 1000),
      meta: {
        source,
        candidate_ids: candidateIds,
        event: { notice: "empty-social-intake" },
      },
    });
  }

  METRICS.ingested.inc(emitted || 1);

  if (data.alert) {
    await postAlert({
      title: data.alert.title || "Social intake event",
      severity: data.alert.severity || "info",
      source: data.alert.source || source,
      message: data.alert.message || "New social intake job processed",
      payload: { candidate_ids: candidateIds, events: events.slice(0, 3) },
    });
  }

  return {
    ok: true,
    emitted,
    candidates: candidateIds.length,
  };
}
