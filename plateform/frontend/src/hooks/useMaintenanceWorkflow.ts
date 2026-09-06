import { useState } from "react";

import {
  addWorkOrderNote,
  assignWorkOrder,
  cancelWorkOrder,
  completeWorkOrder,
  createWorkOrder,
  rescheduleWorkOrder,
  startWorkOrder,
} from "../api/maintenance";
import { readApiError } from "../lib/apiError";
import type { WorkOrderDetail } from "../types/maintenance";

export function useMaintenanceWorkflow() {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run(task: () => Promise<WorkOrderDetail>) {
    setBusy(true);
    setError(null);
    try {
      return await task();
    } catch (caught) {
      setError(readApiError(caught).message);
      return null;
    } finally {
      setBusy(false);
    }
  }

  return {
    busy,
    error,
    clearError: () => setError(null),
    create: (payload: Record<string, unknown>) => run(() => createWorkOrder(payload)),
    assign: (id: string, actorName: string, assignedTo: string, note?: string) =>
      run(() => assignWorkOrder(id, actorName, assignedTo, note)),
    reschedule: (id: string, actorName: string, dueAt: string, note?: string) =>
      run(() => rescheduleWorkOrder(id, actorName, dueAt, note)),
    start: (
      id: string,
      actorName: string,
      options?: { assignedTo?: string; confirmUnassigned?: boolean; note?: string },
    ) => run(() => startWorkOrder(id, actorName, options)),
    addNote: (id: string, actorName: string, note: string) => run(() => addWorkOrderNote(id, actorName, note)),
    complete: (id: string, actorName: string, result: string, summary: string) =>
      run(() => completeWorkOrder(id, actorName, result, summary)),
    cancel: (id: string, actorName: string, reason: string) => run(() => cancelWorkOrder(id, actorName, reason)),
  };
}
