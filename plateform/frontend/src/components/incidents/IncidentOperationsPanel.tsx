import { useState } from "react";
import { Link } from "react-router-dom";

import { useActorName } from "../../hooks/useActorName";
import { useOperationsWorkflow } from "../../hooks/useOperationsWorkflow";
import { formatDateTime } from "../../lib/format";
import {
  ACTION_DISABLED_HINT,
  RESOLUTION_LABELS,
  TASK_PRIORITY_LABELS,
  TASK_STATUS_LABELS,
} from "../../lib/incidents";
import type { IncidentOperations, ResolutionCode, ResponseTaskItem, ResponseTaskPriority } from "../../types/incidents";
import { Button } from "../ui/Button";
import { Card } from "../ui/Card";
import { Modal } from "../ui/Modal";
import { StatusBadge } from "./StatusBadge";

export function IncidentOperationsPanel({
  incidentId,
  operations,
  onChanged,
}: {
  incidentId: string;
  operations: IncidentOperations;
  onChanged: () => Promise<void> | void;
}) {
  const { actorName, setActorName, raw } = useActorName();
  const workflow = useOperationsWorkflow();
  const actions = new Set(operations.allowed_actions);
  const terminal = operations.status === "resolved" || operations.status === "false_alarm";
  const [note, setNote] = useState("");
  const [assignOpen, setAssignOpen] = useState(false);
  const [approvalOpen, setApprovalOpen] = useState(false);
  const [resolveOpen, setResolveOpen] = useState(false);
  const [falseOpen, setFalseOpen] = useState(false);
  const [reopenOpen, setReopenOpen] = useState(false);
  const [cancelTask, setCancelTask] = useState<ResponseTaskItem | null>(null);
  const [assignee, setAssignee] = useState(operations.assigned_to ?? "");
  const [assignNote, setAssignNote] = useState("");
  const [approvalNote, setApprovalNote] = useState("");
  const [resolutionCode, setResolutionCode] = useState<ResolutionCode>("monitoring_completed");
  const [resolutionSummary, setResolutionSummary] = useState("");
  const [confirmIncomplete, setConfirmIncomplete] = useState(false);
  const [falseSummary, setFalseSummary] = useState("");
  const [reopenNote, setReopenNote] = useState("");
  const [taskTitle, setTaskTitle] = useState("");
  const [taskPriority, setTaskPriority] = useState<ResponseTaskPriority>("medium");

  async function after(result: unknown) {
    if (result) {
      await onChanged();
    }
    return result;
  }

  return (
    <Card className="min-w-0 p-5">
      <h3 className="text-base font-semibold text-ink">Operations</h3>
      <p className="mt-1 text-sm text-ink-muted">
        Human-recorded workflow only. Actor name is a temporary development identity, not
        authentication. No physical command is executed.
      </p>
      <div className="mt-3 flex flex-wrap items-center gap-2">
        <StatusBadge status={operations.status} />
        <Link to="/operations" className="text-sm font-medium text-teal hover:underline">
          Operations Center
        </Link>
      </div>

      <dl className="mt-4 grid grid-cols-1 gap-2 text-sm">
        <Row label="Assigned" value={operations.assigned_to ?? "Unassigned"} />
        <Row
          label="Acknowledged"
          value={
            operations.acknowledged_at
              ? `${operations.acknowledged_by ?? "—"} · ${formatDateTime(operations.acknowledged_at)}`
              : "Not acknowledged"
          }
        />
        <Row
          label="Response started"
          value={operations.response_started_at ? formatDateTime(operations.response_started_at) : "—"}
        />
        {operations.resolution_summary ? (
          <Row
            label="Resolution"
            value={`${RESOLUTION_LABELS[operations.resolution_code ?? ""] ?? operations.resolution_code} · ${operations.resolution_summary}`}
          />
        ) : null}
      </dl>

      <label className="mt-4 flex flex-col gap-1 text-xs font-medium text-ink-muted">
        Actor name (temporary)
        <input
          value={raw}
          onChange={(event) => setActorName(event.target.value)}
          className="h-10 rounded-xl border border-line px-3 text-sm font-normal text-ink disabled:bg-page"
          maxLength={120}
        />
      </label>

      {workflow.error ? (
        <p className="mt-3 rounded-2xl bg-critical/10 px-3 py-2 text-sm text-critical" role="alert">
          {workflow.error}
        </p>
      ) : null}
      {workflow.success ? (
        <p className="mt-3 rounded-2xl bg-success/10 px-3 py-2 text-sm text-success" role="status">
          {workflow.success}
        </p>
      ) : null}

      {!terminal ? (
        <label className="mt-4 flex flex-col gap-1 text-xs font-medium text-ink-muted">
          Operational note
          <textarea
            value={note}
            onChange={(event) => setNote(event.target.value)}
            rows={3}
            className="rounded-xl border border-line px-3 py-2 text-sm font-normal text-ink"
            placeholder="Notes do not change status."
          />
        </label>
      ) : null}

      <div className="mt-4 flex flex-col gap-2">
        {actions.has("acknowledge") ? (
          <Button
            disabled={workflow.busy}
            onClick={() => after(workflow.acknowledge(incidentId, actorName, note || undefined))}
          >
            Acknowledge incident
          </Button>
        ) : null}
        {actions.has("start_investigation") || actions.has("return_investigation") ? (
          <Button
            variant="secondary"
            disabled={workflow.busy}
            onClick={() => after(workflow.startInvestigation(incidentId, actorName, note || undefined))}
          >
            {actions.has("return_investigation") ? "Return to investigation" : "Start investigation"}
          </Button>
        ) : null}
        {actions.has("start_response") ? (
          <Button
            variant="secondary"
            disabled={workflow.busy}
            onClick={() => after(workflow.startResponse(incidentId, actorName, note || undefined))}
          >
            Start response
          </Button>
        ) : null}
        {actions.has("add_note") ? (
          <Button
            variant="secondary"
            disabled={workflow.busy || !note.trim()}
            onClick={async () => {
              const result = await after(workflow.addNote(incidentId, actorName, note.trim()));
              if (result) setNote("");
            }}
          >
            Add note
          </Button>
        ) : null}
        {actions.has("assign") ? (
          <Button variant="secondary" disabled={workflow.busy} onClick={() => setAssignOpen(true)}>
            Assign or reassign
          </Button>
        ) : null}
        {actions.has("request_approval") ? (
          <Button variant="secondary" disabled={workflow.busy} onClick={() => setApprovalOpen(true)}>
            Request approval
          </Button>
        ) : null}
        {actions.has("resolve") ? (
          <Button variant="secondary" disabled={workflow.busy} onClick={() => setResolveOpen(true)}>
            Mark resolved
          </Button>
        ) : null}
        {actions.has("false_alarm") ? (
          <Button variant="secondary" disabled={workflow.busy} onClick={() => setFalseOpen(true)}>
            Mark false alarm
          </Button>
        ) : null}
        {actions.has("reopen") ? (
          <Button variant="secondary" disabled={workflow.busy} onClick={() => setReopenOpen(true)}>
            Reopen incident
          </Button>
        ) : null}
      </div>

      {actions.has("manage_tasks") || operations.tasks.length > 0 ? (
        <div className="mt-5">
          <h4 className="text-sm font-semibold text-ink">Response tasks</h4>
          <p className="mt-1 text-sm text-ink-muted">
            {operations.incomplete_task_count} incomplete · {operations.tasks.length} total
          </p>
          {actions.has("manage_tasks") ? (
            <div className="mt-3 flex flex-col gap-2 sm:flex-row">
              <input
                value={taskTitle}
                onChange={(event) => setTaskTitle(event.target.value)}
                className="h-10 flex-1 rounded-xl border border-line px-3 text-sm text-ink"
                placeholder="New task title"
              />
              <select
                value={taskPriority}
                onChange={(event) => setTaskPriority(event.target.value as ResponseTaskPriority)}
                className="h-10 rounded-xl border border-line bg-white px-3 text-sm text-ink"
              >
                {Object.entries(TASK_PRIORITY_LABELS).map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
              <Button
                disabled={workflow.busy || !taskTitle.trim()}
                onClick={async () => {
                  const result = await after(
                    workflow.createTask(incidentId, actorName, {
                      title: taskTitle.trim(),
                      priority: taskPriority,
                    }),
                  );
                  if (result) setTaskTitle("");
                }}
              >
                Add task
              </Button>
            </div>
          ) : null}
          <ul className="mt-3 space-y-2">
            {operations.tasks.map((task) => (
              <li key={task.public_id} className="rounded-2xl border border-line p-3">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-xs font-medium text-teal">{task.public_id}</span>
                  <span className="text-xs text-ink-muted">{TASK_STATUS_LABELS[task.status]}</span>
                  {task.overdue ? <span className="text-xs font-medium text-critical">Overdue</span> : null}
                </div>
                <p className="mt-1 text-sm font-medium text-ink">{task.title}</p>
                <p className="mt-1 text-xs text-ink-muted">
                  {TASK_PRIORITY_LABELS[task.priority]}
                  {task.assigned_to ? ` · ${task.assigned_to}` : ""}
                  {task.due_at ? ` · due ${formatDateTime(task.due_at)}` : ""}
                </p>
                {actions.has("manage_tasks") && (task.status === "todo" || task.status === "in_progress") ? (
                  <div className="mt-2 flex flex-wrap gap-2">
                    {task.status === "todo" ? (
                      <Button
                        variant="secondary"
                        className="!px-2.5 !py-1 text-xs"
                        disabled={workflow.busy}
                        onClick={() => after(workflow.startTask(incidentId, task.public_id, actorName))}
                      >
                        Start
                      </Button>
                    ) : null}
                    <Button
                      variant="secondary"
                      className="!px-2.5 !py-1 text-xs"
                      disabled={workflow.busy}
                      onClick={() =>
                        after(workflow.completeTask(incidentId, task.public_id, actorName, "Completed from Operations."))
                      }
                    >
                      Complete
                    </Button>
                    <Button
                      variant="ghost"
                      className="!px-2.5 !py-1 text-xs"
                      disabled={workflow.busy}
                      onClick={() => setCancelTask(task)}
                    >
                      Cancel
                    </Button>
                  </div>
                ) : null}
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      <div className="mt-5 rounded-2xl border border-critical/20 bg-critical/5 p-4">
        <p className="text-xs font-medium uppercase tracking-wide text-critical">Emergency control</p>
        <p className="mt-1 text-sm text-ink-muted">{ACTION_DISABLED_HINT}</p>
        <span className="mt-3 block" title={ACTION_DISABLED_HINT}>
          <Button disabled variant="danger" className="w-full">
            Emergency isolate valve
          </Button>
        </span>
      </div>

      {assignOpen ? (
        <Modal
          title="Assign incident"
          onClose={() => setAssignOpen(false)}
          footer={
            <>
              <Button variant="secondary" onClick={() => setAssignOpen(false)}>
                Cancel
              </Button>
              <Button
                disabled={workflow.busy || !assignee.trim()}
                onClick={async () => {
                  const result = await after(
                    workflow.assign(incidentId, actorName, assignee.trim(), assignNote || undefined),
                  );
                  if (result) setAssignOpen(false);
                }}
              >
                Confirm assignment
              </Button>
            </>
          }
        >
          <label className="flex flex-col gap-1 text-xs font-medium text-ink-muted">
            Assigned to
            <input
              value={assignee}
              onChange={(event) => setAssignee(event.target.value)}
              className="h-10 rounded-xl border border-line px-3 text-sm font-normal text-ink"
            />
          </label>
          <label className="mt-3 flex flex-col gap-1 text-xs font-medium text-ink-muted">
            Note
            <textarea
              value={assignNote}
              onChange={(event) => setAssignNote(event.target.value)}
              rows={3}
              className="rounded-xl border border-line px-3 py-2 text-sm text-ink"
            />
          </label>
        </Modal>
      ) : null}

      {approvalOpen ? (
        <Modal
          title="Request approval"
          onClose={() => setApprovalOpen(false)}
          footer={
            <>
              <Button variant="secondary" onClick={() => setApprovalOpen(false)}>
                Cancel
              </Button>
              <Button
                disabled={workflow.busy}
                onClick={async () => {
                  const result = await after(
                    workflow.requestApproval(incidentId, actorName, approvalNote || undefined),
                  );
                  if (result) setApprovalOpen(false);
                }}
              >
                Request approval
              </Button>
            </>
          }
        >
          <p className="text-sm text-ink-muted">
            This records that a supervisor decision is required. It does not execute any network
            command.
          </p>
          <label className="mt-3 flex flex-col gap-1 text-xs font-medium text-ink-muted">
            Note
            <textarea
              value={approvalNote}
              onChange={(event) => setApprovalNote(event.target.value)}
              rows={3}
              className="rounded-xl border border-line px-3 py-2 text-sm text-ink"
            />
          </label>
        </Modal>
      ) : null}

      {resolveOpen ? (
        <Modal
          title="Resolve incident"
          onClose={() => setResolveOpen(false)}
          footer={
            <>
              <Button variant="secondary" onClick={() => setResolveOpen(false)}>
                Cancel
              </Button>
              <Button
                disabled={workflow.busy || !resolutionSummary.trim()}
                onClick={async () => {
                  const result = await after(
                    workflow.resolve(
                      incidentId,
                      actorName,
                      resolutionCode,
                      resolutionSummary.trim(),
                      confirmIncomplete,
                    ),
                  );
                  if (result) setResolveOpen(false);
                }}
              >
                Confirm resolution
              </Button>
            </>
          }
        >
          <p className="text-sm text-ink-muted">
            Resolution records an operator outcome. AquaPulse does not claim that infrastructure was
            repaired unless that is written in the summary.
          </p>
          {operations.incomplete_task_count > 0 ? (
            <p className="mt-3 text-sm text-warning">
              {operations.incomplete_task_count} response task(s) are still open.
            </p>
          ) : null}
          <label className="mt-3 flex flex-col gap-1 text-xs font-medium text-ink-muted">
            Resolution code
            <select
              value={resolutionCode}
              onChange={(event) => setResolutionCode(event.target.value as ResolutionCode)}
              className="h-10 rounded-xl border border-line bg-white px-3 text-sm text-ink"
            >
              {Object.entries(RESOLUTION_LABELS)
                .filter(([value]) => value !== "false_alarm")
                .map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
            </select>
          </label>
          <label className="mt-3 flex flex-col gap-1 text-xs font-medium text-ink-muted">
            Resolution summary
            <textarea
              value={resolutionSummary}
              onChange={(event) => setResolutionSummary(event.target.value)}
              rows={4}
              className="rounded-xl border border-line px-3 py-2 text-sm text-ink"
            />
          </label>
          {operations.incomplete_task_count > 0 ? (
            <label className="mt-3 flex items-start gap-2 text-sm text-ink">
              <input
                type="checkbox"
                checked={confirmIncomplete}
                onChange={(event) => setConfirmIncomplete(event.target.checked)}
                className="mt-1"
              />
              Confirm resolve with incomplete tasks
            </label>
          ) : null}
        </Modal>
      ) : null}

      {falseOpen ? (
        <Modal
          title="Mark as false alarm"
          onClose={() => setFalseOpen(false)}
          footer={
            <>
              <Button variant="secondary" onClick={() => setFalseOpen(false)}>
                Cancel
              </Button>
              <Button
                variant="danger"
                disabled={workflow.busy || !falseSummary.trim()}
                onClick={async () => {
                  const result = await after(
                    workflow.falseAlarm(incidentId, actorName, falseSummary.trim(), note || undefined),
                  );
                  if (result) setFalseOpen(false);
                }}
              >
                Confirm false alarm
              </Button>
            </>
          }
        >
          <p className="text-sm text-ink-muted">
            Evidence and history will not be deleted. This only records the operator conclusion.
          </p>
          <label className="mt-3 flex flex-col gap-1 text-xs font-medium text-ink-muted">
            Summary
            <textarea
              value={falseSummary}
              onChange={(event) => setFalseSummary(event.target.value)}
              rows={4}
              className="rounded-xl border border-line px-3 py-2 text-sm text-ink"
            />
          </label>
        </Modal>
      ) : null}

      {reopenOpen ? (
        <Modal
          title="Reopen incident"
          onClose={() => setReopenOpen(false)}
          footer={
            <>
              <Button variant="secondary" onClick={() => setReopenOpen(false)}>
                Cancel
              </Button>
              <Button
                disabled={workflow.busy}
                onClick={async () => {
                  const result = await after(workflow.reopen(incidentId, actorName, reopenNote || undefined));
                  if (result) setReopenOpen(false);
                }}
              >
                Confirm reopen
              </Button>
            </>
          }
        >
          <p className="text-sm text-ink-muted">The incident returns to open for a new acknowledgement.</p>
          <label className="mt-3 flex flex-col gap-1 text-xs font-medium text-ink-muted">
            Note
            <textarea
              value={reopenNote}
              onChange={(event) => setReopenNote(event.target.value)}
              rows={3}
              className="rounded-xl border border-line px-3 py-2 text-sm text-ink"
            />
          </label>
        </Modal>
      ) : null}

      {cancelTask ? (
        <Modal
          title="Cancel response task"
          onClose={() => setCancelTask(null)}
          footer={
            <>
              <Button variant="secondary" onClick={() => setCancelTask(null)}>
                Keep task
              </Button>
              <Button
                variant="danger"
                disabled={workflow.busy}
                onClick={async () => {
                  const result = await after(workflow.cancelTask(incidentId, cancelTask.public_id, actorName));
                  if (result) setCancelTask(null);
                }}
              >
                Cancel task
              </Button>
            </>
          }
        >
          <p className="text-sm text-ink-muted">
            Cancel {cancelTask.public_id}? Completed or cancelled tasks cannot be returned to to-do.
          </p>
        </Modal>
      ) : null}
    </Card>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-start justify-between gap-3">
      <dt className="text-ink-muted">{label}</dt>
      <dd className="max-w-[70%] text-right text-ink">{value}</dd>
    </div>
  );
}
