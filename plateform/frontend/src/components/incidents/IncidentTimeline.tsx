import { motion, useReducedMotion } from "framer-motion";
import { Bot, Radio, Shield, UserRound, Wifi } from "lucide-react";
import type { LucideIcon } from "lucide-react";

import { SOURCE_LABELS } from "../../lib/incidents";
import { formatDateTime } from "../../lib/format";
import type { IncidentTimelineEvent, TimelineSource } from "../../types/incidents";
import { Badge } from "../ui/Badge";
import { Card } from "../ui/Card";

const sourceIcons: Record<TimelineSource, LucideIcon> = {
  detector: Radio,
  agent: Bot,
  network: Wifi,
  operator: UserRound,
  system: Shield,
};

interface IncidentTimelineProps {
  events: IncidentTimelineEvent[];
}

export function IncidentTimeline({ events }: IncidentTimelineProps) {
  const reduceMotion = useReducedMotion();

  return (
    <Card className="min-w-0 p-5">
      <h3 className="text-base font-semibold text-ink">Incident timeline</h3>
      <p className="mt-0.5 text-sm text-ink-muted">Chronological investigation trail</p>
      <ol className="mt-5 space-y-0">
        {events.map((event, index) => {
          const Icon = sourceIcons[event.source];
          return (
            <motion.li
              key={event.id}
              className="flex gap-3"
              initial={reduceMotion ? false : { opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.24, delay: 0.04 * index, ease: "easeOut" }}
            >
              <div className="flex flex-col items-center">
                <span className="flex h-8 w-8 items-center justify-center rounded-full bg-teal-light text-teal">
                  <Icon size={14} aria-hidden="true" />
                </span>
                {index < events.length - 1 ? (
                  <span className="min-h-[2.5rem] w-px flex-1 bg-line" aria-hidden="true" />
                ) : null}
              </div>
              <div className="min-w-0 pb-5">
                <div className="flex flex-wrap items-center gap-2">
                  <p className="text-sm font-medium text-ink">{event.title}</p>
                  <Badge className="bg-page text-ink-muted">{SOURCE_LABELS[event.source]}</Badge>
                  <Badge className="bg-page text-ink-muted">{event.status}</Badge>
                </div>
                <p className="mt-1 text-xs text-ink-muted">
                  {formatDateTime(event.timestamp)}
                  {event.actor_name ? ` · ${event.actor_name}` : ""}
                  {event.response_task_id ? ` · ${event.response_task_id}` : ""}
                </p>
                <p className="mt-1.5 text-sm text-ink-muted">{event.description}</p>
              </div>
            </motion.li>
          );
        })}
      </ol>
    </Card>
  );
}
