import { useCallback, useState } from "react";

import {
  acknowledgeIncident,
  addIncidentNote,
  assignIncident,
  cancelResponseTask,
  completeResponseTask,
  createResponseTask,
  markIncidentFalseAlarm,
  reopenIncident,
  requestIncidentApproval,
  resolveIncident,
  startIncidentInvestigation,
  startIncidentResponse,
  startResponseTask,
} from "../api/operations";
import { readApiError } from "../lib/apiError";
import type { ResolutionCode, ResponseTaskPriority } from "../types/incidents";

export function useOperationsWorkflow() {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const run = useCallback(async <T,>(work: () => Promise<T>, ok: string): Promise<T | null> => {
    setBusy(true);
    setError(null);
    setSuccess(null);
    try {
      const result = await work();
      setSuccess(ok);
      return result;
    } catch (caught) {
      setError(readApiError(caught).message);
      return null;
    } finally {
      setBusy(false);
    }
  }, []);

  return {
    busy,
    error,
    success,
    acknowledge: (id: string, actor: string, note?: string) =>
      run(() => acknowledgeIncident(id, actor, note), "Incident acknowledged."),
    assign: (id: string, actor: string, assignedTo: string, note?: string) =>
      run(() => assignIncident(id, actor, assignedTo, note), "Incident assigned."),
    startInvestigation: (id: string, actor: string, note?: string) =>
      run(() => startIncidentInvestigation(id, actor, note), "Investigation updated."),
    requestApproval: (id: string, actor: string, note?: string) =>
      run(() => requestIncidentApproval(id, actor, note), "Approval requested."),
    startResponse: (id: string, actor: string, note?: string) =>
      run(() => startIncidentResponse(id, actor, note), "Response started. No physical command was sent."),
    addNote: (id: string, actor: string, note: string) =>
      run(() => addIncidentNote(id, actor, note), "Operational note added."),
    resolve: (id: string, actor: string, code: ResolutionCode, summary: string, confirm = false) =>
      run(() => resolveIncident(id, actor, code, summary, confirm), "Incident resolved."),
    falseAlarm: (id: string, actor: string, summary: string, note?: string) =>
      run(() => markIncidentFalseAlarm(id, actor, summary, note), "Marked as a false alarm. History was kept."),
    reopen: (id: string, actor: string, note?: string) =>
      run(() => reopenIncident(id, actor, note), "Incident reopened."),
    createTask: (
      id: string,
      actor: string,
      payload: { title: string; description?: string; priority: ResponseTaskPriority; assigned_to?: string; due_at?: string },
    ) => run(() => createResponseTask(id, actor, payload), "Response task created."),
    startTask: (id: string, taskId: string, actor: string) =>
      run(() => startResponseTask(id, taskId, actor), "Task started."),
    completeTask: (id: string, taskId: string, actor: string, note?: string) =>
      run(() => completeResponseTask(id, taskId, actor, note), "Task completed."),
    cancelTask: (id: string, taskId: string, actor: string, note?: string) =>
      run(() => cancelResponseTask(id, taskId, actor, note), "Task cancelled."),
  };
}
