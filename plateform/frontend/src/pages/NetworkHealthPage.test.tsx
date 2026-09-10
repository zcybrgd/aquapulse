import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { useNetworkHealthData } from "../hooks/useNetworkHealthData";
import type { DeviceNetworkListResponse, DeviceNetworkSummary } from "../types/networkHealth";
import { NetworkHealthPage } from "./NetworkHealthPage";

vi.mock("../hooks/useNetworkHealthData", () => ({
  useNetworkHealthData: vi.fn(),
}));
vi.mock("../api/networkHealth", () => ({
  fetchNetworkDevice: vi.fn(),
  refreshNetworkDevice: vi.fn(),
}));

const mockedData = vi.mocked(useNetworkHealthData);

function summary(overrides: Partial<DeviceNetworkSummary> = {}): DeviceNetworkSummary {
  return {
    cellular_devices: 8,
    reachable: 5,
    unreachable: 1,
    unknown_or_not_checked: 2,
    network_location_available: 4,
    stale_checks: 0,
    last_refresh_at: "2026-09-10T12:00:00Z",
    source_mode: "nokia_live",
    data_source_label: "Nokia live",
    environment_label: "Nokia live",
    available_zones: ["Harbour District"],
    note: "",
    ...overrides,
  };
}

function devices(overrides: Partial<DeviceNetworkListResponse> = {}): DeviceNetworkListResponse {
  return {
    total: 1,
    source_mode: "nokia_live",
    data_source_label: "Nokia live",
    last_refresh_at: "2026-09-10T12:00:00Z",
    items: [
      {
        snapshot_id: "DNS-000001",
        asset_id: "HBR-GW-02",
        asset_name: "Harbour gateway",
        asset_type: "gateway",
        zone_id: "ZONE-HBR",
        zone_name: "Harbour District",
        location_label: "Pump Station 2",
        registered_latitude: 25.08,
        registered_longitude: 55.14,
        has_cellular_identity: true,
        device_msisdn_masked: "+971••••4821",
        reachability_status: "reachable",
        reachable_via: "data",
        reachability_checked_at: "2026-09-10T12:00:00Z",
        network_location_available: true,
        network_latitude: 25.0894,
        network_longitude: 55.1402,
        accuracy_radius_m: 420,
        location_area_type: "CIRCLE",
        location_observed_at: "2026-09-10T12:00:00Z",
        location_offset_m: 12,
        retrieved_at: "2026-09-10T12:00:00Z",
        stale: false,
        provider: "nokia_camara",
        source_mode: "nokia_live",
        data_source_label: "Nokia live",
        error_code: null,
        error_message: null,
        last_telemetry: null,
      },
    ],
    ...overrides,
  };
}

function renderPage() {
  return render(
    <MemoryRouter>
      <NetworkHealthPage />
    </MemoryRouter>,
  );
}

describe("NetworkHealthPage", () => {
  it("shows live Nokia data when CAMARA is connected", () => {
    mockedData.mockReturnValue({
      summary: summary(),
      devices: devices(),
      loading: false,
      refreshing: false,
      error: null,
      updatedAt: new Date("2026-09-10T12:00:00Z"),
      reload: vi.fn(),
      refreshAll: vi.fn(),
    });
    renderPage();
    expect(screen.getByText("Nokia Network as Code is connected", { exact: false })).toBeInTheDocument();
    expect(screen.getAllByText("HBR-GW-02").length).toBeGreaterThan(0);
    expect(screen.queryByText("Network data source not connected")).not.toBeInTheDocument();
  });

  it("hides the empty state when stored snapshots exist without a live source", () => {
    mockedData.mockReturnValue({
      summary: summary({
        source_mode: "seeded_demo",
        data_source_label: "Demonstration data",
        environment_label: "Demonstration environment",
      }),
      devices: devices({
        source_mode: "seeded_demo",
        data_source_label: "Demonstration data",
        items: [
          {
            ...devices().items[0],
            source_mode: "seeded_demo",
            data_source_label: "Demonstration data",
            provider: "nokia_mock",
          },
        ],
      }),
      loading: false,
      refreshing: false,
      error: null,
      updatedAt: new Date("2026-09-10T12:00:00Z"),
      reload: vi.fn(),
      refreshAll: vi.fn(),
    });
    renderPage();
    expect(screen.getAllByText("HBR-GW-02").length).toBeGreaterThan(0);
    expect(screen.getByText(/Showing stored snapshots/)).toBeInTheDocument();
  });
});
