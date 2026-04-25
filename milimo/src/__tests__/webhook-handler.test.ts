// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

import {
  StripeWebhookHandler,
  type WebhookEvent,
  type SubscriptionChange,
  type PaymentFailureAlert,
} from "../lib/webhook-handler";

const mockExistsSync = vi.fn();
const mockReadFileSync = vi.fn();
const mockWriteFileSync = vi.fn();
const mockMkdirSync = vi.fn();

vi.mock("node:fs", () => ({
  existsSync: (...args: unknown[]) => mockExistsSync(...args),
  readFileSync: (...args: unknown[]) => mockReadFileSync(...args),
  writeFileSync: (...args: unknown[]) => mockWriteFileSync(...args),
  mkdirSync: (...args: unknown[]) => mockMkdirSync(...args),
}));

vi.mock("node:os", () => ({
  homedir: () => "/home/test",
}));

vi.mock("node:path", () => ({
  join: (...args: string[]) => args.join("/"),
}));

describe("StripeWebhookHandler", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockExistsSync.mockReturnValue(false);
    mockMkdirSync.mockReturnValue(undefined);
    mockWriteFileSync.mockReturnValue(undefined);
  });

  describe("handleEvent", () => {
    it("handles subscription.created event", () => {
      mockExistsSync.mockReturnValue(true);
      mockReadFileSync.mockReturnValue(JSON.stringify({ tier: "free" }));

      const handler = new StripeWebhookHandler();
      const event: WebhookEvent = {
        id: "evt_123",
        type: "customer.subscription.created",
        data: {
          object: {
            id: "sub_123",
            customer: "cus_123",
            status: "active",
          },
        },
      };

      const result = handler.handleEvent(event) as SubscriptionChange;

      expect(result).not.toBeNull();
      expect(result.tier).toBe("pro");
      expect(mockWriteFileSync).toHaveBeenCalled();
    });

    it("handles subscription.deleted event", () => {
      mockExistsSync.mockReturnValue(true);
      mockReadFileSync.mockReturnValue(JSON.stringify({ tier: "pro" }));

      const handler = new StripeWebhookHandler();
      const event: WebhookEvent = {
        id: "evt_456",
        type: "customer.subscription.deleted",
        data: {
          object: {
            id: "sub_123",
            customer: "cus_123",
          },
        },
      };

      const result = handler.handleEvent(event) as SubscriptionChange;

      expect(result).not.toBeNull();
      expect(result.tier).toBe("free");
    });

    it("handles invoice.payment_failed event", () => {
      mockExistsSync.mockReturnValue(true);
      mockMkdirSync.mockReturnValue(undefined);

      const handler = new StripeWebhookHandler();
      const event: WebhookEvent = {
        id: "evt_789",
        type: "invoice.payment_failed",
        data: {
          object: {
            id: "inv_123",
            customer: "cus_123",
          },
        },
      };

      const result = handler.handleEvent(event) as PaymentFailureAlert;

      expect(result).not.toBeNull();
      expect(result.customerId).toBe("cus_123");
    });

    it("returns null for unhandled event types", () => {
      const handler = new StripeWebhookHandler();
      const event: WebhookEvent = {
        id: "evt_000",
        type: "unknown.event",
        data: {
          object: { id: "obj_123" },
        },
      };

      const result = handler.handleEvent(event);

      expect(result).toBeNull();
    });
  });
});
