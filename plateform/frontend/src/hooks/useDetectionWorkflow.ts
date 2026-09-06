import { useCallback, useState } from "react";

import {
  addDetectionNote,
  dismissDetection,
  mergeDetection,
  promoteDetection,
  reopenDetection,
  startDetectionReview,
} from "../api/detections";
import { readApiError } from "../lib/apiError";
import type {
  AddNotePayload,
  DetectionDetail,
  DismissPayload,
  MergePayload,
  PromotePayload,
  PromoteResponse,
  ReopenPayload,
  StartReviewPayload,
} from "../types/detections";

interface WorkflowState {
  busy: boolean;
  error: string | null;
  success: string | null;
  startReview: (id: string, payload: StartReviewPayload) => Promise<DetectionDetail | null>;
  addNote: (id: string, payload: AddNotePayload) => Promise<DetectionDetail | null>;
  dismiss: (id: string, payload: DismissPayload) => Promise<DetectionDetail | null>;
  reopen: (id: string, payload: ReopenPayload) => Promise<DetectionDetail | null>;
  merge: (id: string, payload: MergePayload) => Promise<DetectionDetail | null>;
  promote: (id: string, payload: PromotePayload) => Promise<PromoteResponse | null>;
  clearFeedback: () => void;
}

export function useDetectionWorkflow(): WorkflowState {
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
    startReview: (id, payload) => run(() => startDetectionReview(id, payload), "Review started."),
    addNote: (id, payload) => run(() => addDetectionNote(id, payload), "Note added."),
    dismiss: (id, payload) => run(() => dismissDetection(id, payload), "Detection dismissed."),
    reopen: (id, payload) => run(() => reopenDetection(id, payload), "Detection reopened."),
    merge: (id, payload) => run(() => mergeDetection(id, payload), "Detection merged."),
    promote: (id, payload) => run(() => promoteDetection(id, payload), "Incident created from this detection."),
    clearFeedback: () => {
      setError(null);
      setSuccess(null);
    },
  };
}
