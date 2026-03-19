// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

/**
 * Firebase Cloud Messaging Integration
 */

interface PushNotification {
  to: string;
  notification: {
    title: string;
    body: string;
  };
  data?: Record<string, string>;
  android?: {
    priority: "high" | "normal";
  };
  apns?: {
    payload: {
      aps: {
        sound?: string;
        badge?: number;
      };
    };
  };
}

interface PushConfig {
  projectId: string;
  serviceAccount?: string;
}

class FirebasePushService {
  private initialized = false;

  async initialize(config: PushConfig): Promise<void> {
    try {
      const admin = await import("firebase-admin");

      if (!admin.apps.length) {
        admin.initializeApp({
          credential: admin.credential.applicationDefault(),
          projectId: config.projectId,
        });
      }

      this.initialized = true;
    } catch (error) {
      console.error("Failed to initialize Firebase:", error);
      throw error;
    }
  }

  async send(token: string, notification: PushNotification): Promise<string> {
    if (!this.initialized) {
      throw new Error("Firebase not initialized");
    }

    const admin = await import("firebase-admin");

    const message = {
      token,
      notification: {
        title: notification.notification.title,
        body: notification.notification.body,
      },
      data: notification.data || {},
      android: {
        priority: (notification.android?.priority || "high") as "high" | "normal",
      },
      apns: {
        payload: notification.apns?.payload || {
          aps: {
            sound: "default",
            badge: 1,
          },
        },
      },
    };

    const messageId = await admin.messaging().send(message);
    return messageId;
  }

  async sendMultiple(
    tokens: string[],
    notification: Omit<PushNotification, "to">
  ): Promise<{ successCount: number; failureCount: number }> {
    if (!this.initialized) {
      throw new Error("Firebase not initialized");
    }

    const admin = await import("firebase-admin");

    const message = {
      tokens,
      notification: {
        title: notification.notification.title,
        body: notification.notification.body,
      },
      data: notification.data || {},
    };

    const response = await admin.messaging().sendEachForMulticast(message);
    return {
      successCount: response.successCount,
      failureCount: response.failureCount,
    };
  }

  async sendToTopic(
    topic: string,
    notification: Omit<PushNotification, "to">
  ): Promise<string> {
    if (!this.initialized) {
      throw new Error("Firebase not initialized");
    }

    const admin = await import("firebase-admin");

    const message = {
      topic,
      notification: {
        title: notification.notification.title,
        body: notification.notification.body,
      },
      data: notification.data || {},
    };

    const messageId = await admin.messaging().send(message);
    return messageId;
  }
}

export const pushService = new FirebasePushService();

export function createPendingActionNotification(
  action: {
    id: string;
    type: string;
    description: string;
    risk_level: string;
  }
): Omit<PushNotification, "to"> {
  return {
    notification: {
      title: "Action Requires Approval",
      body: action.description.slice(0, 100),
    },
    data: {
      action_id: action.id,
      type: "pending_action",
      risk_level: action.risk_level,
    },
    android: {
      priority: action.risk_level === "high" ? "high" : "normal",
    },
    apns: {
      payload: {
        aps: {
          sound: action.risk_level === "high" ? "alert" : "default",
          badge: 1,
        },
      },
    },
  };
}

export function createApprovedNotification(
  action: { id: string; claw_role: string }
): Omit<PushNotification, "to"> {
  return {
    notification: {
      title: "Action Approved",
      body: `${action.claw_role} action approved`,
    },
    data: {
      action_id: action.id,
      type: "action_approved",
    },
    android: {
      priority: "normal",
    },
    apns: {
      payload: {
        aps: {
          sound: "default",
          badge: 0,
        },
      },
    },
  };
}

export function createVetoedNotification(
  action: { id: string; claw_role: string; reason?: string }
): Omit<PushNotification, "to"> {
  return {
    notification: {
      title: "Action Vetoed",
      body: action.reason || `${action.claw_role} action vetoed`,
    },
    data: {
      action_id: action.id,
      type: "action_vetoed",
    },
    android: {
      priority: "normal",
    },
    apns: {
      payload: {
        aps: {
          sound: "default",
          badge: 0,
        },
      },
    },
  };
}

export function createClawOfflineNotification(
  claw: { role: string; region: string }
): Omit<PushNotification, "to"> {
  return {
    notification: {
      title: "Claw Offline",
      body: `${claw.role} in ${claw.region} is offline`,
    },
    data: {
      claw_role: claw.role,
      region: claw.region,
      type: "claw_offline",
    },
    android: {
      priority: "high",
    },
    apns: {
      payload: {
        aps: {
          sound: "alert",
          badge: 1,
        },
      },
    },
  };
}

export function createRateLimitWarningNotification(
  info: { used: number; limit: number }
): Omit<PushNotification, "to"> {
  return {
    notification: {
      title: "Rate Limit Warning",
      body: `${info.used}/${info.limit} daily approvals used`,
    },
    data: {
      used: String(info.used),
      limit: String(info.limit),
      type: "rate_limit_warning",
    },
    android: {
      priority: "high",
    },
    apns: {
      payload: {
        aps: {
          sound: "default",
          badge: 1,
        },
      },
    },
  };
}
