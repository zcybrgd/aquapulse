import axios from "axios";

import type { ApiErrorDetail } from "../types/detections";

export function readApiError(caught: unknown): ApiErrorDetail {
  if (axios.isAxiosError(caught)) {
    const detail = caught.response?.data?.detail;
    if (detail && typeof detail === "object" && "message" in detail) {
      return {
        message: String((detail as ApiErrorDetail).message),
        code: typeof (detail as ApiErrorDetail).code === "string" ? (detail as ApiErrorDetail).code : undefined,
        incident_id:
          typeof (detail as ApiErrorDetail).incident_id === "string"
            ? (detail as ApiErrorDetail).incident_id
            : undefined,
        target_detection_id:
          typeof (detail as ApiErrorDetail).target_detection_id === "string"
            ? (detail as ApiErrorDetail).target_detection_id
            : undefined,
      };
    }
    if (caught.response?.status === 422) {
      return { message: "Check the required fields and try again.", code: "validation_error" };
    }
  }
  return { message: "The investigation action could not be completed. Try again." };
}
