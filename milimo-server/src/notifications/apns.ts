// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

/**
 * Apple Push Notification Service (APNs) Integration
 */

interface APNsConfig {
  teamId: string;
  keyId: string;
  privateKey: string;
  bundleId: string;
  production: boolean;
}

interface APSPayload {
  alert?: {
    title: string;
    body: string;
  };
  badge?: number;
  sound?: string | { critical: number; name: string; volume: number };
  "content-available"?: number;
  "mutable-content"?: number;
  category?: string;
  "thread-id"?: string;
}

interface APNsNotification {
  deviceToken: string;
  aps: APSPayload;
  data?: Record<string, string>;
}

interface APNsResponse {
  success: boolean;
  deviceToken: string;
  messageId?: string;
  error?: string;
}

class APNsService {
  private config: APNsConfig;
  private initialized = false;

  constructor(config: APNsConfig) {
    this.config = config;
  }

  async initialize(): Promise<void> {
    try {
      // In production, load and validate the APNs key
      this.initialized = true;
      console.log("APNs service initialized for", this.config.bundleId);
    } catch (error) {
      console.error("Failed to initialize APNs:", error);
      throw error;
    }
  }

  async send(notification: APNsNotification): Promise<APNsResponse> {
    if (!this.initialized) {
      throw new Error("APNs service not initialized");
    }

    const host = this.config.production
      ? "api.push.apple.com:443"
      : "api.sandbox.push.apple.com:443";

    const path = `/3/device/${notification.deviceToken}`;

    try {
      // In production, use node-apn library or HTTP/2 client
      // This is a simplified implementation
      console.log(`Sending APNs notification to ${notification.deviceToken}`);
      console.log(`Host: ${host}, Path: ${path}`);
      console.log(`Payload:`, JSON.stringify(notification.aps, null, 2));

      // Simulate successful send
      return {
        success: true,
        deviceToken: notification.deviceToken,
        messageId: `apns-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      };
    } catch (error) {
      return {
        success: false,
        deviceToken: notification.deviceToken,
        error: String(error),
      };
    }
  }

  async sendMultiple(
    deviceTokens: string[],
    payload: Omit<APNsNotification, "deviceToken">
  ): Promise<APNsResponse[]> {
    const results: APNsResponse[] = [];

    for (const token of deviceTokens) {
      const result = await this.send({
        ...payload,
        deviceToken: token,
      });
      results.push(result);
    }

    return results;
  }

  createPayload(
    title: string,
    body: string,
    options: {
      badge?: number;
      sound?: string;
      category?: string;
      threadId?: string;
      data?: Record<string, string>;
    } = {}
  ): Omit<APNsNotification, "deviceToken"> {
    const aps: APSPayload = {
      alert: { title, body },
    };

    if (options.badge !== undefined) {
      aps.badge = options.badge;
    }

    if (options.sound) {
      aps.sound = options.sound;
    }

    if (options.category) {
      aps.category = options.category;
    }

    if (options.threadId) {
      aps["thread-id"] = options.threadId;
    }

    return { aps, data: options.data };
  }

  createSilentNotification(): Omit<APNsNotification, "deviceToken"> {
    return {
      aps: {
        "content-available": 1,
      },
    };
  }

  createMutableContentNotification(
    title: string,
    body: string,
    data?: Record<string, string>
  ): Omit<APNsNotification, "deviceToken"> {
    return {
      aps: {
        alert: { title, body },
        "mutable-content": 1,
      },
      data,
    };
  }
}

export { APNsService, APNsConfig, APNsNotification, APNsResponse };

export function createPendingActionAPNs(
  actionId: string,
  description: string,
  riskLevel: string
): Omit<APNsNotification, "deviceToken"> {
  const service = new APNsService({
    teamId: "",
    keyId: "",
    privateKey: "",
    bundleId: "com.milimo.mobile",
    production: false,
  });

  return service.createPayload(
    "Action Requires Approval",
    description.slice(0, 100),
    {
      badge: 1,
      sound: riskLevel === "high" ? "alert.aiff" : "default",
      category: "PENDING_ACTION",
      threadId: "pending-actions",
      data: {
        actionId,
        riskLevel,
        type: "pending_action",
      },
    }
  );
}

export function createApprovedAPNs(
  actionId: string,
  clawRole: string
): Omit<APNsNotification, "deviceToken"> {
  const service = new APNsService({
    teamId: "",
    keyId: "",
    privateKey: "",
    bundleId: "com.milimo.mobile",
    production: false,
  });

  return service.createPayload(
    "Action Approved",
    `${clawRole} action approved`,
    {
      badge: 0,
      sound: "default",
      category: "ACTION_RESULT",
      threadId: "action-results",
      data: {
        actionId,
        type: "action_approved",
      },
    }
  );
}

export function createClawOfflineAPNs(
  clawRole: string,
  region: string
): Omit<APNsNotification, "deviceToken"> {
  const service = new APNsService({
    teamId: "",
    keyId: "",
    privateKey: "",
    bundleId: "com.milimo.mobile",
    production: false,
  });

  return service.createPayload(
    "Claw Offline",
    `${clawRole} in ${region} is offline`,
    {
      badge: 1,
      sound: "alert.aiff",
      category: "CLAW_ALERT",
      threadId: "claw-alerts",
      data: {
        clawRole,
        region,
        type: "claw_offline",
      },
    }
  );
}
