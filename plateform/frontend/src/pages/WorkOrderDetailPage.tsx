import { useState } from "react";
import { Link, useLocation, useParams } from "react-router-dom";
import { motion, useReducedMotion } from "framer-motion";

import { MaintenancePriorityBadge, OverdueBadge, WorkOrderStatusBadge } from "../components/maintenance/MaintenanceBadges";
import {
  AssignDialog,
  CancelDialog,
  CompleteDialog,
  NoteDialog,
  RescheduleDialog,
  StartDialog,
} from "../components/maintenance/WorkOrderDialogs";
import { AssetTypeBadge } from "../components/assets/AssetTypeBadge";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { EmptyState } from "../components/ui/EmptyState";
import { ErrorState } from "../components/ui/ErrorState";
import { Skeleton } from "../components/ui/Skeleton";
import { useMaintenanceWorkflow } from "../hooks/useMaintenanceWorkflow";
import { useWorkOrderDetail } from "../hooks/useWorkOrderDetail";
import { formatDateTime } from "../lib/format";
import {
  COMPLETION_LABELS,
  EVENT_LABELS,
  MAINTENANCE_TYPE_LABELS,
  NO_PHYSICAL_ACTION,
} from "../lib/maintenance";
import type { WorkOrderDetail } from "../types/maintenance";

export function WorkOrderDetailPage() {
  const { workOrderId } = useParams();
  const location = useLocation();
  const { workOrder, loading, notFound, error, reload } = useWorkOrderDetail(workOrderId);
  const workflow = useMaintenanceWorkflow();
  const reduceMotion = useReducedMotion();
  const [dialog, setDialog] = useState<
    "assign" | "reschedule" | "start" | "note" | "complete" | "cancel" | null
  >(null);

  const back = `/maintenance${location.search}`;

  return (
    <div className="mx-auto flex w-full max-w-[1400px] flex-col gap-6">
      {loading ? <WorkOrderDetailSkeleton /> : null}
      {!loading && error ? <ErrorState message={error} onRetry={reload} /> : null}
      {!loading && notFound ? (
        <div className="card p-6">
          <Link to={back} className="text-sm font-medium text-teal hover:underline">
            Back to Maintenance Center
          </Link>
          <EmptyState
            title="Work order not found"
            description="This work-order ID is not in the current maintenance set. Return to the Maintenance Center and choose another record."
          />
        </div>
      ) : null}

      {!loading && workOrder ? (
        <motion.div
          className="flex flex-col gap-6"
          initial={reduceMotion ? false : { opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.28, ease: "easeOut" }}
        >
          <div>
            <Link to={back} className="text-sm font-medium text-teal hover:underline">
              Back to Maintenance Center
            </Link>
            <div className="mt-3 flex flex-wrap items-center gap-2">
              <h2 className="text-2xl font-semibold tracking-tight text-ink">{workOrder.public_id}</h2>
              <WorkOrderStatusBadge status={workOrder.status} />
              <MaintenancePriorityBadge priority={workOrder.priority} />
              {workOrder.overdue ? <OverdueBadge /> : null}
            </div>
            <p className="mt-1 text-sm text-ink-muted">{workOrder.title}</p>
          </div>

          <div className="grid grid-cols-1 gap-4 xl:grid-cols-[minmax(0,1.65fr)_minmax(20rem,1fr)]">
            <div className="flex min-w-0 flex-col gap-4">
              <Card className="min-w-0 p-5">
                <h3 className="text-base font-semibold text-ink">Work order</h3>
                <dl className="mt-4 grid grid-cols-1 gap-3 text-sm sm:grid-cols-2">
                  <Row label="Type" value={MAINTENANCE_TYPE_LABELS[workOrder.maintenance_type]} />
                  <Row label="Due" value={formatDateTime(workOrder.due_at)} />
                  <Row
                    label="Scheduled start"
                    value={workOrder.scheduled_start_at ? formatDateTime(workOrder.scheduled_start_at) : "—"}
                  />
                  <Row label="Assigned" value={workOrder.assigned_to ?? "Unassigned"} />
                  <Row
                    label="Started"
                    value={workOrder.started_at ? formatDateTime(workOrder.started_at) : "—"}
                  />
                  <Row
                    label="Completed"
                    value={
                      workOrder.completed_at
                        ? `${formatDateTime(workOrder.completed_at)} · ${workOrder.completed_by ?? "—"}`
                        : "—"
                    }
                  />
                </dl>
                {workOrder.description ? (
                  <p className="mt-4 text-sm text-ink-muted">{workOrder.description}</p>
                ) : null}
                {workOrder.instructions ? (
                  <div className="mt-4 rounded-2xl bg-page p-3">
                    <p className="text-xs font-medium uppercase tracking-wide text-ink-muted">Instructions</p>
                    <p className="mt-1 text-sm text-ink">{workOrder.instructions}</p>
                  </div>
                ) : null}
                {workOrder.completion_result ? (
                  <div className="mt-4 rounded-2xl border border-line p-3">
                    <p className="text-xs font-medium uppercase tracking-wide text-ink-muted">
                      Completion result
                    </p>
                    <p className="mt-1 text-sm font-medium text-ink">
                      {COMPLETION_LABELS[workOrder.completion_result]}
                    </p>
                    {workOrder.completion_summary ? (
                      <p className="mt-1 text-sm text-ink-muted">{workOrder.completion_summary}</p>
                    ) : null}
                  </div>
                ) : null}
                {workOrder.cancellation_reason ? (
                  <div className="mt-4 rounded-2xl border border-line p-3">
                    <p className="text-xs font-medium uppercase tracking-wide text-ink-muted">
                      Cancellation
                    </p>
                    <p className="mt-1 text-sm text-ink-muted">
                      {workOrder.cancelled_by ?? "—"}
                      {workOrder.cancelled_at ? ` · ${formatDateTime(workOrder.cancelled_at)}` : ""}
                    </p>
                    <p className="mt-1 text-sm text-ink">{workOrder.cancellation_reason}</p>
                  </div>
                ) : null}
              </Card>

              <HistoryList events={workOrder.history} reduceMotion={Boolean(reduceMotion)} />
            </div>

            <div className="flex min-w-0 flex-col gap-4">
              <Card className="min-w-0 p-5">
                <h3 className="text-base font-semibold text-ink">Asset and location</h3>
                <div className="mt-3 flex flex-wrap items-center gap-2">
                  <AssetTypeBadge type={workOrder.asset_type} />
                </div>
                <p className="mt-3 text-sm font-medium text-ink">{workOrder.asset_name}</p>
                <p className="text-sm text-ink-muted">{workOrder.asset_id}</p>
                <dl className="mt-4 space-y-2 text-sm">
                  <Row label="Zone" value={workOrder.zone} />
                  <Row label="Location" value={workOrder.location_label ?? "—"} />
                  <Row
                    label="Cellular identity"
                    value={
                      workOrder.has_cellular_identity
                        ? (workOrder.device_msisdn_masked ?? "Masked identity on file")
                        : "Not recorded"
                    }
                  />
                </dl>
                <div className="mt-4 flex flex-col gap-2">
                  <Link
                    to={`/assets/${encodeURIComponent(workOrder.asset_id)}`}
                    className="text-sm font-medium text-teal hover:underline"
                  >
                    Open asset details
                  </Link>
                  <Link
                    to={`/map?zone=${encodeURIComponent(workOrder.zone)}`}
                    className="text-sm font-medium text-teal hover:underline"
                  >
                    Open map location
                  </Link>
                  {workOrder.incident_id ? (
                    <Link
                      to={`/incidents/${encodeURIComponent(workOrder.incident_id)}`}
                      className="text-sm font-medium text-teal hover:underline"
                    >
                      Open incident {workOrder.incident_id}
                    </Link>
                  ) : null}
                </div>
              </Card>

              <WorkOrderActions
                workOrder={workOrder}
                busy={workflow.busy}
                error={workflow.error}
                onOpen={setDialog}
              />
            </div>
          </div>
        </motion.div>
      ) : null}

      {workOrder && dialog === "assign" ? (
        <AssignDialog
          workOrder={workOrder}
          busy={workflow.busy}
          error={workflow.error}
          onClose={() => {
            workflow.clearError();
            setDialog(null);
          }}
          onSubmit={async (actor, assignedTo, note) => after(workflow.assign(workOrder.public_id, actor, assignedTo, note), reload)}
        />
      ) : null}
      {workOrder && dialog === "reschedule" ? (
        <RescheduleDialog
          workOrder={workOrder}
          busy={workflow.busy}
          error={workflow.error}
          onClose={() => {
            workflow.clearError();
            setDialog(null);
          }}
          onSubmit={async (actor, dueAt, note) => after(workflow.reschedule(workOrder.public_id, actor, dueAt, note), reload)}
        />
      ) : null}
      {workOrder && dialog === "start" ? (
        <StartDialog
          workOrder={workOrder}
          busy={workflow.busy}
          error={workflow.error}
          onClose={() => {
            workflow.clearError();
            setDialog(null);
          }}
          onSubmit={async (actor, options) => after(workflow.start(workOrder.public_id, actor, options), reload)}
        />
      ) : null}
      {workOrder && dialog === "note" ? (
        <NoteDialog
          busy={workflow.busy}
          error={workflow.error}
          onClose={() => {
            workflow.clearError();
            setDialog(null);
          }}
          onSubmit={async (actor, note) => after(workflow.addNote(workOrder.public_id, actor, note), reload)}
        />
      ) : null}
      {workOrder && dialog === "complete" ? (
        <CompleteDialog
          workOrder={workOrder}
          busy={workflow.busy}
          error={workflow.error}
          onClose={() => {
            workflow.clearError();
            setDialog(null);
          }}
          onSubmit={async (actor, result, summary) =>
            after(workflow.complete(workOrder.public_id, actor, result, summary), reload)
          }
        />
      ) : null}
      {workOrder && dialog === "cancel" ? (
        <CancelDialog
          workOrder={workOrder}
          busy={workflow.busy}
          error={workflow.error}
          onClose={() => {
            workflow.clearError();
            setDialog(null);
          }}
          onSubmit={async (actor, reason) => after(workflow.cancel(workOrder.public_id, actor, reason), reload)}
        />
      ) : null}
    </div>
  );
}

async function after(result: unknown, reload: () => Promise<void> | void) {
  if (result) await reload();
  return result;
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-ink-muted">{label}</dt>
      <dd className="mt-0.5 font-medium text-ink">{value}</dd>
    </div>
  );
}

function WorkOrderActions({
  workOrder,
  busy,
  error,
  onOpen,
}: {
  workOrder: WorkOrderDetail;
  busy: boolean;
  error: string | null;
  onOpen: (dialog: "assign" | "reschedule" | "start" | "note" | "complete" | "cancel") => void;
}) {
  const actions = new Set(workOrder.allowed_actions);
  const terminal = workOrder.status === "completed" || workOrder.status === "cancelled";

  return (
    <Card className="min-w-0 p-5">
      <h3 className="text-base font-semibold text-ink">Actions</h3>
      <p className="mt-1 text-sm text-ink-muted">
        Actor name is a temporary development identity, not authentication. {NO_PHYSICAL_ACTION}
      </p>
      {error ? (
        <p className="mt-3 rounded-2xl bg-critical/10 px-3 py-2 text-sm text-critical" role="alert">
          {error}
        </p>
      ) : null}
      {terminal ? (
        <p className="mt-4 text-sm text-ink-muted">This work order is closed and can only be viewed.</p>
      ) : (
        <div className="mt-4 flex flex-col gap-2">
          {actions.has("assign") ? (
            <Button variant="secondary" disabled={busy} onClick={() => onOpen("assign")}>
              {workOrder.assigned_to ? "Reassign" : "Assign"}
            </Button>
          ) : null}
          {actions.has("reschedule") ? (
            <Button variant="secondary" disabled={busy} onClick={() => onOpen("reschedule")}>
              Reschedule
            </Button>
          ) : null}
          {actions.has("start") ? (
            <Button disabled={busy} onClick={() => onOpen("start")}>
              Start work
            </Button>
          ) : null}
          {actions.has("add_note") ? (
            <Button variant="secondary" disabled={busy} onClick={() => onOpen("note")}>
              Add note
            </Button>
          ) : null}
          {actions.has("complete") ? (
            <Button variant="secondary" disabled={busy} onClick={() => onOpen("complete")}>
              Complete
            </Button>
          ) : null}
          {actions.has("cancel") ? (
            <Button variant="danger" disabled={busy} onClick={() => onOpen("cancel")}>
              Cancel work order
            </Button>
          ) : null}
        </div>
      )}
    </Card>
  );
}

function HistoryList({
  events,
  reduceMotion,
}: {
  events: WorkOrderDetail["history"];
  reduceMotion: boolean;
}) {
  return (
    <Card className="min-w-0 p-5">
      <h3 className="text-base font-semibold text-ink">History</h3>
      <p className="mt-0.5 text-sm text-ink-muted">Append-only administrative trail</p>
      {events.length === 0 ? (
        <EmptyState title="No history yet" description="Actions on this work order will appear here." />
      ) : (
        <ol className="mt-5 space-y-0">
          {events.map((event, index) => (
            <motion.li
              key={event.public_id}
              className="flex gap-3"
              initial={reduceMotion ? false : { opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.24, delay: 0.04 * index, ease: "easeOut" }}
            >
              <div className="flex flex-col items-center">
                <span className="h-2.5 w-2.5 rounded-full bg-teal" aria-hidden="true" />
                {index < events.length - 1 ? (
                  <span className="min-h-[2.5rem] w-px flex-1 bg-line" aria-hidden="true" />
                ) : null}
              </div>
              <div className="min-w-0 pb-5">
                <p className="text-sm font-medium text-ink">
                  {EVENT_LABELS[event.event_type] ?? event.event_type}
                </p>
                <p className="mt-1 text-xs text-ink-muted">
                  {formatDateTime(event.created_at)} · {event.actor_name}
                  {event.from_status && event.to_status ? ` · ${event.from_status} → ${event.to_status}` : ""}
                </p>
                {event.note ? <p className="mt-1.5 text-sm text-ink-muted">{event.note}</p> : null}
              </div>
            </motion.li>
          ))}
        </ol>
      )}
    </Card>
  );
}

function WorkOrderDetailSkeleton() {
  return (
    <div className="flex flex-col gap-4" aria-hidden="true">
      <Skeleton className="h-8 w-48" />
      <Skeleton className="h-6 w-80" />
      <div className="grid grid-cols-1 gap-4 xl:grid-cols-[minmax(0,1.65fr)_minmax(20rem,1fr)]">
        <Skeleton className="h-64 w-full" />
        <Skeleton className="h-64 w-full" />
      </div>
    </div>
  );
}
