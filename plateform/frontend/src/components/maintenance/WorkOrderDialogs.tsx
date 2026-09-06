import { useState } from "react";

import { useActorName } from "../../hooks/useActorName";
import {
  ALL_COMPLETION_RESULTS,
  ALL_MAINTENANCE_TYPES,
  ALL_PRIORITIES,
  COMPLETION_LABELS,
  MAINTENANCE_TYPE_LABELS,
  NO_PHYSICAL_ACTION,
  PRIORITY_LABELS,
  fromDateTimeLocal,
  toDateTimeLocal,
} from "../../lib/maintenance";
import type { CompletionResult, MaintenancePriority, MaintenanceType, WorkOrderDetail } from "../../types/maintenance";
import { Button } from "../ui/Button";
import { Modal } from "../ui/Modal";

function ActorField({
  raw,
  onChange,
}: {
  raw: string;
  onChange: (value: string) => void;
}) {
  return (
    <label className="flex flex-col gap-1 text-xs font-medium text-ink-muted">
      Actor name (temporary)
      <input
        value={raw}
        onChange={(event) => onChange(event.target.value)}
        className="h-10 rounded-xl border border-line px-3 text-sm font-normal text-ink"
        maxLength={120}
        required
      />
    </label>
  );
}

function FieldError({ message }: { message: string | null }) {
  if (!message) return null;
  return (
    <p className="rounded-2xl bg-critical/10 px-3 py-2 text-sm text-critical" role="alert">
      {message}
    </p>
  );
}

export function AssignDialog({
  workOrder,
  busy,
  error,
  onClose,
  onSubmit,
}: {
  workOrder: WorkOrderDetail;
  busy: boolean;
  error: string | null;
  onClose: () => void;
  onSubmit: (actorName: string, assignedTo: string, note?: string) => Promise<unknown>;
}) {
  const { actorName, setActorName, raw } = useActorName();
  const [assignedTo, setAssignedTo] = useState(workOrder.assigned_to ?? "");
  const [note, setNote] = useState("");

  return (
    <Modal
      title={workOrder.assigned_to ? "Reassign work order" : "Assign work order"}
      onClose={onClose}
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button
            disabled={busy || !assignedTo.trim()}
            onClick={async () => {
              const result = await onSubmit(actorName, assignedTo.trim(), note.trim() || undefined);
              if (result) onClose();
            }}
          >
            {workOrder.assigned_to ? "Reassign" : "Assign"}
          </Button>
        </>
      }
    >
      <div className="flex flex-col gap-3">
        <p className="text-sm text-ink-muted">{workOrder.public_id} · {workOrder.title}</p>
        <FieldError message={error} />
        <label className="flex flex-col gap-1 text-xs font-medium text-ink-muted">
          Assigned technician
          <input
            value={assignedTo}
            onChange={(event) => setAssignedTo(event.target.value)}
            className="h-10 rounded-xl border border-line px-3 text-sm font-normal text-ink"
            required
          />
        </label>
        <label className="flex flex-col gap-1 text-xs font-medium text-ink-muted">
          Note (optional)
          <textarea
            value={note}
            onChange={(event) => setNote(event.target.value)}
            rows={3}
            className="rounded-xl border border-line px-3 py-2 text-sm font-normal text-ink"
          />
        </label>
        <ActorField raw={raw} onChange={setActorName} />
      </div>
    </Modal>
  );
}

export function RescheduleDialog({
  workOrder,
  busy,
  error,
  onClose,
  onSubmit,
}: {
  workOrder: WorkOrderDetail;
  busy: boolean;
  error: string | null;
  onClose: () => void;
  onSubmit: (actorName: string, dueAt: string, note?: string) => Promise<unknown>;
}) {
  const { actorName, setActorName, raw } = useActorName();
  const [dueAt, setDueAt] = useState(toDateTimeLocal(workOrder.due_at));
  const [note, setNote] = useState("");

  return (
    <Modal
      title="Reschedule work order"
      onClose={onClose}
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button
            disabled={busy || !dueAt}
            onClick={async () => {
              const result = await onSubmit(actorName, fromDateTimeLocal(dueAt), note.trim() || undefined);
              if (result) onClose();
            }}
          >
            Reschedule
          </Button>
        </>
      }
    >
      <div className="flex flex-col gap-3">
        <FieldError message={error} />
        <label className="flex flex-col gap-1 text-xs font-medium text-ink-muted">
          Due date
          <input
            type="datetime-local"
            value={dueAt}
            onChange={(event) => setDueAt(event.target.value)}
            className="h-10 rounded-xl border border-line px-3 text-sm font-normal text-ink"
            required
          />
        </label>
        <label className="flex flex-col gap-1 text-xs font-medium text-ink-muted">
          Note (optional)
          <textarea
            value={note}
            onChange={(event) => setNote(event.target.value)}
            rows={3}
            className="rounded-xl border border-line px-3 py-2 text-sm font-normal text-ink"
          />
        </label>
        <ActorField raw={raw} onChange={setActorName} />
      </div>
    </Modal>
  );
}

export function StartDialog({
  workOrder,
  busy,
  error,
  onClose,
  onSubmit,
}: {
  workOrder: WorkOrderDetail;
  busy: boolean;
  error: string | null;
  onClose: () => void;
  onSubmit: (
    actorName: string,
    options?: { assignedTo?: string; confirmUnassigned?: boolean; note?: string },
  ) => Promise<unknown>;
}) {
  const { actorName, setActorName, raw } = useActorName();
  const [assignedTo, setAssignedTo] = useState(workOrder.assigned_to ?? "");
  const [confirmUnassigned, setConfirmUnassigned] = useState(false);
  const [note, setNote] = useState("");
  const unassigned = !assignedTo.trim() && !workOrder.assigned_to;

  return (
    <Modal
      title="Start work"
      onClose={onClose}
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button
            disabled={busy || (unassigned && !confirmUnassigned)}
            onClick={async () => {
              const result = await onSubmit(actorName, {
                assignedTo: assignedTo.trim() || undefined,
                confirmUnassigned: unassigned ? confirmUnassigned : undefined,
                note: note.trim() || undefined,
              });
              if (result) onClose();
            }}
          >
            Start work
          </Button>
        </>
      }
    >
      <div className="flex flex-col gap-3">
        <p className="text-sm text-ink-muted">
          Starting records that work began. It does not send a device command.
        </p>
        <FieldError message={error} />
        <label className="flex flex-col gap-1 text-xs font-medium text-ink-muted">
          Assigned technician
          <input
            value={assignedTo}
            onChange={(event) => setAssignedTo(event.target.value)}
            className="h-10 rounded-xl border border-line px-3 text-sm font-normal text-ink"
            placeholder={workOrder.assigned_to ?? "Optional if you confirm unassigned start"}
          />
        </label>
        {unassigned ? (
          <label className="flex items-start gap-2 text-sm text-ink">
            <input
              type="checkbox"
              checked={confirmUnassigned}
              onChange={(event) => setConfirmUnassigned(event.target.checked)}
              className="mt-1 h-4 w-4 rounded border-line"
            />
            Confirm start without assignment
          </label>
        ) : null}
        <label className="flex flex-col gap-1 text-xs font-medium text-ink-muted">
          Note (optional)
          <textarea
            value={note}
            onChange={(event) => setNote(event.target.value)}
            rows={3}
            className="rounded-xl border border-line px-3 py-2 text-sm font-normal text-ink"
          />
        </label>
        <ActorField raw={raw} onChange={setActorName} />
      </div>
    </Modal>
  );
}

export function NoteDialog({
  busy,
  error,
  onClose,
  onSubmit,
}: {
  busy: boolean;
  error: string | null;
  onClose: () => void;
  onSubmit: (actorName: string, note: string) => Promise<unknown>;
}) {
  const { actorName, setActorName, raw } = useActorName();
  const [note, setNote] = useState("");

  return (
    <Modal
      title="Add note"
      onClose={onClose}
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button
            disabled={busy || !note.trim()}
            onClick={async () => {
              const result = await onSubmit(actorName, note.trim());
              if (result) onClose();
            }}
          >
            Add note
          </Button>
        </>
      }
    >
      <div className="flex flex-col gap-3">
        <p className="text-sm text-ink-muted">Notes do not change work-order status.</p>
        <FieldError message={error} />
        <label className="flex flex-col gap-1 text-xs font-medium text-ink-muted">
          Note
          <textarea
            value={note}
            onChange={(event) => setNote(event.target.value)}
            rows={4}
            className="rounded-xl border border-line px-3 py-2 text-sm font-normal text-ink"
            required
          />
        </label>
        <ActorField raw={raw} onChange={setActorName} />
      </div>
    </Modal>
  );
}

export function CompleteDialog({
  workOrder,
  busy,
  error,
  onClose,
  onSubmit,
}: {
  workOrder: WorkOrderDetail;
  busy: boolean;
  error: string | null;
  onClose: () => void;
  onSubmit: (actorName: string, result: string, summary: string) => Promise<unknown>;
}) {
  const { actorName, setActorName, raw } = useActorName();
  const [result, setResult] = useState<CompletionResult>("completed_successfully");
  const [summary, setSummary] = useState("");
  const [confirm, setConfirm] = useState(false);

  return (
    <Modal
      title="Complete work order"
      onClose={onClose}
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button
            disabled={busy || !summary.trim() || !confirm}
            onClick={async () => {
              const payload = await onSubmit(actorName, result, summary.trim());
              if (payload) onClose();
            }}
          >
            Complete record
          </Button>
        </>
      }
    >
      <div className="flex flex-col gap-3">
        <p className="rounded-2xl bg-warning/10 px-3 py-2 text-sm text-ink">{NO_PHYSICAL_ACTION}</p>
        <p className="text-sm text-ink-muted">
          {workOrder.public_id}. Completion is an administrative record. It does not change asset
          operational status, valve position or incident status automatically.
        </p>
        <FieldError message={error} />
        <label className="flex flex-col gap-1 text-xs font-medium text-ink-muted">
          Completion result
          <select
            value={result}
            onChange={(event) => setResult(event.target.value as CompletionResult)}
            className="h-10 rounded-xl border border-line bg-white px-3 text-sm font-normal text-ink"
          >
            {ALL_COMPLETION_RESULTS.map((value) => (
              <option key={value} value={value}>
                {COMPLETION_LABELS[value]}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1 text-xs font-medium text-ink-muted">
          Completion summary
          <textarea
            value={summary}
            onChange={(event) => setSummary(event.target.value)}
            rows={4}
            className="rounded-xl border border-line px-3 py-2 text-sm font-normal text-ink"
            required
          />
        </label>
        <ActorField raw={raw} onChange={setActorName} />
        <label className="flex items-start gap-2 text-sm text-ink">
          <input
            type="checkbox"
            checked={confirm}
            onChange={(event) => setConfirm(event.target.checked)}
            className="mt-1 h-4 w-4 rounded border-line"
          />
          I confirm this administrative completion. No physical device command will be executed.
        </label>
      </div>
    </Modal>
  );
}

export function CancelDialog({
  workOrder,
  busy,
  error,
  onClose,
  onSubmit,
}: {
  workOrder: WorkOrderDetail;
  busy: boolean;
  error: string | null;
  onClose: () => void;
  onSubmit: (actorName: string, reason: string) => Promise<unknown>;
}) {
  const { actorName, setActorName, raw } = useActorName();
  const [reason, setReason] = useState("");
  const [confirm, setConfirm] = useState(false);

  return (
    <Modal
      title="Cancel work order"
      onClose={onClose}
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>
            Keep open
          </Button>
          <Button
            variant="danger"
            disabled={busy || !reason.trim() || !confirm}
            onClick={async () => {
              const result = await onSubmit(actorName, reason.trim());
              if (result) onClose();
            }}
          >
            Cancel work order
          </Button>
        </>
      }
    >
      <div className="flex flex-col gap-3">
        <p className="text-sm text-ink-muted">
          Cancelling {workOrder.public_id} is an administrative close. A reason is required.
        </p>
        <FieldError message={error} />
        <label className="flex flex-col gap-1 text-xs font-medium text-ink-muted">
          Cancellation reason
          <textarea
            value={reason}
            onChange={(event) => setReason(event.target.value)}
            rows={4}
            className="rounded-xl border border-line px-3 py-2 text-sm font-normal text-ink"
            required
          />
        </label>
        <ActorField raw={raw} onChange={setActorName} />
        <label className="flex items-start gap-2 text-sm text-ink">
          <input
            type="checkbox"
            checked={confirm}
            onChange={(event) => setConfirm(event.target.checked)}
            className="mt-1 h-4 w-4 rounded border-line"
          />
          I confirm cancellation of this administrative record.
        </label>
      </div>
    </Modal>
  );
}

export function CreateWorkOrderDialog({
  busy,
  error,
  defaultAssetId,
  onClose,
  onSubmit,
}: {
  busy: boolean;
  error: string | null;
  defaultAssetId?: string;
  onClose: () => void;
  onSubmit: (payload: Record<string, unknown>) => Promise<unknown>;
}) {
  const { actorName, setActorName, raw } = useActorName();
  const [assetId, setAssetId] = useState(defaultAssetId ?? "");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [maintenanceType, setMaintenanceType] = useState<MaintenanceType>("preventive");
  const [priority, setPriority] = useState<MaintenancePriority>("medium");
  const [assignedTo, setAssignedTo] = useState("");
  const [incidentId, setIncidentId] = useState("");
  const [dueAt, setDueAt] = useState("");

  return (
    <Modal
      title="Create work order"
      onClose={onClose}
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button
            disabled={busy || !assetId.trim() || !title.trim() || !dueAt}
            onClick={async () => {
              const result = await onSubmit({
                actor_name: actorName,
                asset_id: assetId.trim(),
                title: title.trim(),
                description: description.trim() || null,
                maintenance_type: maintenanceType,
                priority,
                assigned_to: assignedTo.trim() || null,
                incident_id: incidentId.trim() || null,
                due_at: fromDateTimeLocal(dueAt),
              });
              if (result) onClose();
            }}
          >
            Create work order
          </Button>
        </>
      }
    >
      <div className="flex flex-col gap-3">
        <p className="text-sm text-ink-muted">
          Administrative record only. Creating a work order does not command a device.
        </p>
        <FieldError message={error} />
        <label className="flex flex-col gap-1 text-xs font-medium text-ink-muted">
          Asset ID
          <input
            value={assetId}
            onChange={(event) => setAssetId(event.target.value)}
            className="h-10 rounded-xl border border-line px-3 text-sm font-normal text-ink"
            placeholder="SNS-HBR-007"
            required
          />
        </label>
        <label className="flex flex-col gap-1 text-xs font-medium text-ink-muted">
          Title
          <input
            value={title}
            onChange={(event) => setTitle(event.target.value)}
            className="h-10 rounded-xl border border-line px-3 text-sm font-normal text-ink"
            required
          />
        </label>
        <label className="flex flex-col gap-1 text-xs font-medium text-ink-muted">
          Description (optional)
          <textarea
            value={description}
            onChange={(event) => setDescription(event.target.value)}
            rows={3}
            className="rounded-xl border border-line px-3 py-2 text-sm font-normal text-ink"
          />
        </label>
        <label className="flex flex-col gap-1 text-xs font-medium text-ink-muted">
          Maintenance type
          <select
            value={maintenanceType}
            onChange={(event) => setMaintenanceType(event.target.value as MaintenanceType)}
            className="h-10 rounded-xl border border-line bg-white px-3 text-sm font-normal text-ink"
          >
            {ALL_MAINTENANCE_TYPES.map((value) => (
              <option key={value} value={value}>
                {MAINTENANCE_TYPE_LABELS[value]}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1 text-xs font-medium text-ink-muted">
          Priority
          <select
            value={priority}
            onChange={(event) => setPriority(event.target.value as MaintenancePriority)}
            className="h-10 rounded-xl border border-line bg-white px-3 text-sm font-normal text-ink"
          >
            {ALL_PRIORITIES.map((value) => (
              <option key={value} value={value}>
                {PRIORITY_LABELS[value]}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1 text-xs font-medium text-ink-muted">
          Due date
          <input
            type="datetime-local"
            value={dueAt}
            onChange={(event) => setDueAt(event.target.value)}
            className="h-10 rounded-xl border border-line px-3 text-sm font-normal text-ink"
            required
          />
        </label>
        <label className="flex flex-col gap-1 text-xs font-medium text-ink-muted">
          Assigned technician (optional)
          <input
            value={assignedTo}
            onChange={(event) => setAssignedTo(event.target.value)}
            className="h-10 rounded-xl border border-line px-3 text-sm font-normal text-ink"
          />
        </label>
        <label className="flex flex-col gap-1 text-xs font-medium text-ink-muted">
          Related incident (optional)
          <input
            value={incidentId}
            onChange={(event) => setIncidentId(event.target.value)}
            className="h-10 rounded-xl border border-line px-3 text-sm font-normal text-ink"
            placeholder="INC-1842"
          />
        </label>
        <ActorField raw={raw} onChange={setActorName} />
      </div>
    </Modal>
  );
}
