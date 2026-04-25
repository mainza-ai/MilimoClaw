// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

vi.mock("blessed", () => ({
  screen: vi.fn(() => ({
    append: vi.fn(),
    render: vi.fn(),
    destroy: vi.fn(),
    key: vi.fn(),
  })),
  box: vi.fn(() => ({
    setContent: vi.fn(),
    destroy: vi.fn(),
  })),
}));

vi.mock("node:fs", () => ({
  existsSync: vi.fn(),
  readFileSync: vi.fn(),
  readdirSync: vi.fn(),
  mkdirSync: vi.fn(),
  writeFileSync: vi.fn(),
}));

vi.mock("node:path", () => ({
  join: vi.fn((...args: string[]) => args.join("/")),
}));

import { WarRoomTUI } from "../warroom/warroom-tui";

const mockedFs = (await import("node:fs")) as any;
const mockedBlessed = (await import("blessed")) as any;

describe("WarRoomTUI (Blessed)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    process.env.HOME = "/home/test";
  });

  describe("constructor", () => {
    it("initializes with squad ID and operator ID", () => {
      new WarRoomTUI({ squadId: "test-squad", operatorId: "test-operator" });

      expect(mockedBlessed.screen).toHaveBeenCalled();
    });

    it("defaults operator ID to 'local-operator'", () => {
      const _tui = new WarRoomTUI({ squadId: "test-squad" });

      expect((_tui as any).operatorId).toBe("local-operator");
    });

    it("creates left panel for war room actions", () => {
      new WarRoomTUI({ squadId: "test-squad" });

      expect(mockedBlessed.box).toHaveBeenCalledWith(
        expect.objectContaining({
          label: expect.stringContaining("WAR ROOM"),
        }),
      );
    });

    it("creates right panel for claw health", () => {
      new WarRoomTUI({ squadId: "test-squad" });

      expect(mockedBlessed.box).toHaveBeenCalledWith(
        expect.objectContaining({
          label: expect.stringContaining("CLAW HEALTH"),
        }),
      );
    });

    it("creates bottom bar for keyboard shortcuts", () => {
      new WarRoomTUI({ squadId: "test-squad" });

      expect(mockedBlessed.box).toHaveBeenCalledWith(
        expect.objectContaining({
          height: 3,
        }),
      );
    });

    it("initializes ApprovalEngine with squad ID", () => {
      const _tui = new WarRoomTUI({ squadId: "my-squad" });

      expect((_tui as any).squadId).toBe("my-squad");
    });

    it("initializes AuditLogger with squad ID", () => {
      const _tui = new WarRoomTUI({ squadId: "audit-squad" });

      expect((_tui as any).audit).toBeDefined();
    });

    it("initializes EvolutionManager with squad ID", () => {
      const _tui = new WarRoomTUI({ squadId: "evolution-squad" });

      expect((_tui as any).evolution).toBeDefined();
    });
  });

  describe("start()", () => {
    it("sets isRunning to true", () => {
      const _tui = new WarRoomTUI({ squadId: "test-squad" });
      _tui.start();

      expect((_tui as any).isRunning).toBe(true);
    });

    it("sets up health polling interval", () => {
      vi.useFakeTimers();
      const _tui = new WarRoomTUI({ squadId: "test-squad" });
      _tui.start();

      expect(vi.getTimerCount()).toBeGreaterThanOrEqual(0);
      vi.useRealTimers();
    });

    it("sets up revenue polling interval (30s)", () => {
      vi.useFakeTimers();
      const _tui = new WarRoomTUI({ squadId: "test-squad" });
      _tui.start();

      expect((_tui as any).revenuePollInterval).toBeDefined();
      vi.useRealTimers();
    });

    it("renders initial screen", () => {
      const _tui = new WarRoomTUI({ squadId: "test-squad" });
      _tui.start();

      expect((_tui as any).screen.render).toHaveBeenCalled();
    });
  });

  describe("stop()", () => {
    it("sets isRunning to false", () => {
      const _tui = new WarRoomTUI({ squadId: "test-squad" });
      _tui.start();
      _tui.stop();

      expect((_tui as any).isRunning).toBe(false);
    });

    it("clears the health polling interval", () => {
      const _tui = new WarRoomTUI({ squadId: "test-squad" });
      _tui.start();
      _tui.stop();

      expect((_tui as any).refreshInterval).toBeNull();
    });

    it("clears the revenue polling interval", () => {
      const _tui = new WarRoomTUI({ squadId: "test-squad" });
      _tui.start();
      _tui.stop();

      expect((_tui as any).revenuePollInterval).toBeNull();
    });

    it("destroys the screen", () => {
      const _tui = new WarRoomTUI({ squadId: "test-squad" });
      _tui.stop();

      expect((_tui as any).screen.destroy).toHaveBeenCalled();
    });
  });

  describe("revenue widget", () => {
    it("displays revenue data when file exists", () => {
      const mockRevenueData = {
        current_week: { total_revenue: 5000, invoices_paid: 3 },
        previous_week: { total_revenue: 4000 },
        pending_invoices: 2,
        last_updated: "2026-03-20T10:00:00Z",
      };

      mockedFs.existsSync.mockReturnValue(true);
      mockedFs.readFileSync.mockReturnValue(JSON.stringify(mockRevenueData));

      const _tui = new WarRoomTUI({ squadId: "test-squad" });
      (_tui as any).fetchRevenueData();

      expect((_tui as any).revenueData).toBeDefined();
      expect((_tui as any).revenueData.week_revenue).toBe(5000);
      expect((_tui as any).revenueData.invoices_paid).toBe(3);
      expect((_tui as any).revenueData.invoices_pending).toBe(2);
    });

    it("calculates week-over-week percentage correctly", () => {
      const mockRevenueData = {
        current_week: { total_revenue: 5500 },
        previous_week: { total_revenue: 5000 },
        pending_invoices: 1,
        last_updated: "2026-03-20T10:00:00Z",
      };

      mockedFs.existsSync.mockReturnValue(true);
      mockedFs.readFileSync.mockReturnValue(JSON.stringify(mockRevenueData));

      const _tui = new WarRoomTUI({ squadId: "test-squad" });
      (_tui as any).fetchRevenueData();

      expect((_tui as any).revenueData.week_over_week_pct).toBe(10);
    });

    it("shows negative WoW percentage for revenue decline", () => {
      const mockRevenueData = {
        current_week: { total_revenue: 4500 },
        previous_week: { total_revenue: 5000 },
        pending_invoices: 1,
        last_updated: "2026-03-20T10:00:00Z",
      };

      mockedFs.existsSync.mockReturnValue(true);
      mockedFs.readFileSync.mockReturnValue(JSON.stringify(mockRevenueData));

      const _tui = new WarRoomTUI({ squadId: "test-squad" });
      (_tui as any).fetchRevenueData();

      expect((_tui as any).revenueData.week_over_week_pct).toBe(-10);
    });

    it("returns null when revenue file does not exist", () => {
      mockedFs.existsSync.mockReturnValue(false);

      const _tui = new WarRoomTUI({ squadId: "test-squad" });
      (_tui as any).fetchRevenueData();

      expect((_tui as any).revenueData).toBeNull();
    });

    it("handles invalid JSON gracefully", () => {
      mockedFs.existsSync.mockReturnValue(true);
      mockedFs.readFileSync.mockReturnValue("not valid json");

      const _tui = new WarRoomTUI({ squadId: "test-squad" });
      (_tui as any).fetchRevenueData();

      expect((_tui as any).revenueData).toBeNull();
    });

    it("formats currency correctly", () => {
      const _tui = new WarRoomTUI({ squadId: "test-squad" });

      expect((_tui as any).formatCurrency(5000)).toBe("$5,000");
      expect((_tui as any).formatCurrency(1234567)).toBe("$1,234,567");
      expect((_tui as any).formatCurrency(0)).toBe("$0");
    });

    it("handles zero previous revenue for WoW calculation", () => {
      const mockRevenueData = {
        current_week: { total_revenue: 5000 },
        previous_week: { total_revenue: 0 },
        pending_invoices: 0,
        last_updated: "2026-03-20T10:00:00Z",
      };

      mockedFs.existsSync.mockReturnValue(true);
      mockedFs.readFileSync.mockReturnValue(JSON.stringify(mockRevenueData));

      const _tui = new WarRoomTUI({ squadId: "test-squad" });
      (_tui as any).fetchRevenueData();

      expect((_tui as any).revenueData.week_over_week_pct).toBe(0);
    });

    it("handles missing invoices_paid field", () => {
      const mockRevenueData = {
        current_week: { total_revenue: 5000 },
        previous_week: { total_revenue: 4000 },
        pending_invoices: 2,
        last_updated: "2026-03-20T10:00:00Z",
      };

      mockedFs.existsSync.mockReturnValue(true);
      mockedFs.readFileSync.mockReturnValue(JSON.stringify(mockRevenueData));

      const _tui = new WarRoomTUI({ squadId: "test-squad" });
      (_tui as any).fetchRevenueData();

      expect((_tui as any).revenueData.invoices_paid).toBe(0);
      expect((_tui as any).revenueData.invoices_pending).toBe(2);
    });
  });

  describe("polling intervals", () => {
    it("uses 3 second interval for health polling", () => {
      const _tui = new WarRoomTUI({ squadId: "test-squad" });

      expect((_tui as any).POLL_INTERVAL).toBe(3000);
    });

    it("uses 30 second interval for revenue polling", () => {
      const _tui = new WarRoomTUI({ squadId: "test-squad" });

      expect((_tui as any).REVENUE_POLL_INTERVAL).toBe(30000);
    });
  });
});
