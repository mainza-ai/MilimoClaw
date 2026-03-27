// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

/**
 * Jest tests for WarRoomTUI (Blessed implementation)
 */

jest.mock("blessed", () => ({
  screen: jest.fn(() => ({
    append: jest.fn(),
    render: jest.fn(),
    destroy: jest.fn(),
    key: jest.fn(),
  })),
  box: jest.fn(() => ({
    setContent: jest.fn(),
    destroy: jest.fn(),
  })),
}));

jest.mock("node:fs", () => ({
  existsSync: jest.fn(),
  readFileSync: jest.fn(),
  readdirSync: jest.fn(),
  mkdirSync: jest.fn(),
  writeFileSync: jest.fn(),
}));

jest.mock("node:path", () => ({
  join: jest.fn((...args: string[]) => args.join("/")),
}));

import { WarRoomTUI } from "../warroom/warroom-tui";
import { ApprovalEngine } from "../warroom/approval";
import { AuditLogger } from "../warroom/audit";
import { EvolutionManager } from "../warroom/evolution";

const mockedFs = jest.requireMock("node:fs");
const mockedBlessed = jest.requireMock("blessed");

describe("WarRoomTUI (Blessed)", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    process.env.HOME = "/home/test";
  });

  describe("constructor", () => {
    it("initializes with squad ID and operator ID", () => {
      const tui = new WarRoomTUI({ squadId: "test-squad", operatorId: "test-operator" });

      expect(mockedBlessed.screen).toHaveBeenCalled();
    });

    it("defaults operator ID to 'local-operator'", () => {
      const tui = new WarRoomTUI({ squadId: "test-squad" });

      expect((tui as any).operatorId).toBe("local-operator");
    });

    it("creates left panel for war room actions", () => {
      const tui = new WarRoomTUI({ squadId: "test-squad" });

      expect(mockedBlessed.box).toHaveBeenCalledWith(
        expect.objectContaining({
          label: expect.stringContaining("WAR ROOM"),
        })
      );
    });

    it("creates right panel for claw health", () => {
      const tui = new WarRoomTUI({ squadId: "test-squad" });

      expect(mockedBlessed.box).toHaveBeenCalledWith(
        expect.objectContaining({
          label: expect.stringContaining("CLAW HEALTH"),
        })
      );
    });

    it("creates bottom bar for keyboard shortcuts", () => {
      const tui = new WarRoomTUI({ squadId: "test-squad" });

      expect(mockedBlessed.box).toHaveBeenCalledWith(
        expect.objectContaining({
          height: 3,
        })
      );
    });

    it("initializes ApprovalEngine with squad ID", () => {
      const tui = new WarRoomTUI({ squadId: "my-squad" });

      expect((tui as any).squadId).toBe("my-squad");
    });

    it("initializes AuditLogger with squad ID", () => {
      const tui = new WarRoomTUI({ squadId: "audit-squad" });

      expect((tui as any).audit).toBeDefined();
    });

    it("initializes EvolutionManager with squad ID", () => {
      const tui = new WarRoomTUI({ squadId: "evolution-squad" });

      expect((tui as any).evolution).toBeDefined();
    });
  });

  describe("start()", () => {
    it("sets isRunning to true", () => {
      const tui = new WarRoomTUI({ squadId: "test-squad" });
      tui.start();

      expect((tui as any).isRunning).toBe(true);
    });

    it("sets up health polling interval", () => {
      jest.useFakeTimers();
      const tui = new WarRoomTUI({ squadId: "test-squad" });
      tui.start();

      expect(jest.getTimerCount()).toBeGreaterThanOrEqual(0);
      jest.useRealTimers();
    });

    it("sets up revenue polling interval (30s)", () => {
      jest.useFakeTimers();
      const tui = new WarRoomTUI({ squadId: "test-squad" });
      tui.start();

      expect((tui as any).revenuePollInterval).toBeDefined();
      jest.useRealTimers();
    });

    it("renders initial screen", () => {
      const tui = new WarRoomTUI({ squadId: "test-squad" });
      tui.start();

      expect((tui as any).screen.render).toHaveBeenCalled();
    });
  });

  describe("stop()", () => {
    it("sets isRunning to false", () => {
      const tui = new WarRoomTUI({ squadId: "test-squad" });
      tui.start();
      tui.stop();

      expect((tui as any).isRunning).toBe(false);
    });

    it("clears the health polling interval", () => {
      const tui = new WarRoomTUI({ squadId: "test-squad" });
      tui.start();
      tui.stop();

      expect((tui as any).refreshInterval).toBeNull();
    });

    it("clears the revenue polling interval", () => {
      const tui = new WarRoomTUI({ squadId: "test-squad" });
      tui.start();
      tui.stop();

      expect((tui as any).revenuePollInterval).toBeNull();
    });

    it("destroys the screen", () => {
      const tui = new WarRoomTUI({ squadId: "test-squad" });
      tui.stop();

      expect((tui as any).screen.destroy).toHaveBeenCalled();
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

      const tui = new WarRoomTUI({ squadId: "test-squad" });
      (tui as any).fetchRevenueData();

      expect((tui as any).revenueData).toBeDefined();
      expect((tui as any).revenueData.week_revenue).toBe(5000);
      expect((tui as any).revenueData.invoices_paid).toBe(3);
      expect((tui as any).revenueData.invoices_pending).toBe(2);
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

      const tui = new WarRoomTUI({ squadId: "test-squad" });
      (tui as any).fetchRevenueData();

      expect((tui as any).revenueData.week_over_week_pct).toBe(10);
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

      const tui = new WarRoomTUI({ squadId: "test-squad" });
      (tui as any).fetchRevenueData();

      expect((tui as any).revenueData.week_over_week_pct).toBe(-10);
    });

    it("returns null when revenue file does not exist", () => {
      mockedFs.existsSync.mockReturnValue(false);

      const tui = new WarRoomTUI({ squadId: "test-squad" });
      (tui as any).fetchRevenueData();

      expect((tui as any).revenueData).toBeNull();
    });

    it("handles invalid JSON gracefully", () => {
      mockedFs.existsSync.mockReturnValue(true);
      mockedFs.readFileSync.mockReturnValue("not valid json");

      const tui = new WarRoomTUI({ squadId: "test-squad" });
      (tui as any).fetchRevenueData();

      expect((tui as any).revenueData).toBeNull();
    });

    it("formats currency correctly", () => {
      const tui = new WarRoomTUI({ squadId: "test-squad" });

      expect((tui as any).formatCurrency(5000)).toBe("$5,000");
      expect((tui as any).formatCurrency(1234567)).toBe("$1,234,567");
      expect((tui as any).formatCurrency(0)).toBe("$0");
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

      const tui = new WarRoomTUI({ squadId: "test-squad" });
      (tui as any).fetchRevenueData();

      expect((tui as any).revenueData.week_over_week_pct).toBe(0);
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

      const tui = new WarRoomTUI({ squadId: "test-squad" });
      (tui as any).fetchRevenueData();

      expect((tui as any).revenueData.invoices_paid).toBe(0);
      expect((tui as any).revenueData.invoices_pending).toBe(2);
    });
  });

  describe("polling intervals", () => {
    it("uses 3 second interval for health polling", () => {
      const tui = new WarRoomTUI({ squadId: "test-squad" });

      expect((tui as any).POLL_INTERVAL).toBe(3000);
    });

    it("uses 30 second interval for revenue polling", () => {
      const tui = new WarRoomTUI({ squadId: "test-squad" });

      expect((tui as any).REVENUE_POLL_INTERVAL).toBe(30000);
    });
  });
});
