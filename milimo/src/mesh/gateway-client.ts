// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

/**
 * Gateway Client
 *
 * Unix socket connection to OpenShell gateway for inter-claw messaging.
 * Falls back to file-based queues when gateway unavailable.
 */

import * as net from "node:net";
import { createCipheriv, createDecipheriv, randomBytes, hkdfSync } from "node:crypto";
import { join } from "node:path";
import { existsSync, mkdirSync, writeFileSync } from "node:fs";

export class GatewayDeliveryError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "GatewayDeliveryError";
  }
}

export interface GatewayMessage {
  id: string;
  sender_role: string;
  recipient_role: string;
  message_type: string;
  payload: Record<string, unknown>;
  timestamp: string;
  encrypted?: boolean;
}

export interface GatewayClientOptions {
  squadId: string;
  meshSecret: string;
  onMessage?: (message: GatewayMessage) => void;
}

const LINUX_SOCKET_PATH = "/var/run/openshell/gateway.sock";
const MACOS_SOCKET_PATH = "/tmp/openshell-gateway.sock";
const MAX_RETRIES = 5;
const INITIAL_RETRY_DELAY = 1000;
const MAX_RETRY_DELAY = 30000;
const MESSAGE_TIMEOUT = 5000;

export class GatewayClient {
  private squadId: string;
  private meshSecret: string;
  private socketPath: string;
  private socket: net.Socket | null = null;
  private connected: boolean = false;
  private fallbackMode: boolean = false;
  private messageHandlers: Array<(message: GatewayMessage) => void> = [];
  private pendingAcks: Map<
    string,
    { resolve: () => void; reject: (err: Error) => void; timeout: NodeJS.Timeout }
  > = new Map();
  private retryCount: number = 0;

  constructor(options: GatewayClientOptions) {
    this.squadId = options.squadId;
    this.meshSecret = options.meshSecret;
    this.socketPath = process.platform === "darwin" ? MACOS_SOCKET_PATH : LINUX_SOCKET_PATH;

    if (options.onMessage) {
      this.messageHandlers.push(options.onMessage);
    }
  }

  public async connect(): Promise<void> {
    if (this.connected) {
      return;
    }

    if (!existsSync(this.socketPath)) {
      this.fallbackMode = true;
      return;
    }

    return new Promise((resolve, reject) => {
      this.socket = new net.Socket();

      const onConnect = (): void => {
        this.connected = true;
        this.fallbackMode = false;
        this.retryCount = 0;
        this.setupSocketHandlers();
        resolve();
      };

      const onError = (_err: Error): void => {
        this.socket?.destroy();
        this.socket = null;

        if (this.retryCount < MAX_RETRIES) {
          const delay = Math.min(
            INITIAL_RETRY_DELAY * Math.pow(2, this.retryCount),
            MAX_RETRY_DELAY,
          );
          this.retryCount++;

          setTimeout(() => {
            this.connect().then(resolve).catch(reject);
          }, delay);
        } else {
          this.fallbackMode = true;
          resolve();
        }
      };

      this.socket.once("connect", onConnect);
      this.socket.once("error", onError);

      this.socket.connect(this.socketPath);
    });
  }

  private setupSocketHandlers(): void {
    if (!this.socket) return;

    this.socket.on("data", (data: Buffer) => {
      try {
        const message = JSON.parse(data.toString()) as GatewayMessage | { ack: string };
        if ("ack" in message) {
          const pending = this.pendingAcks.get(message.ack);
          if (pending) {
            clearTimeout(pending.timeout);
            pending.resolve();
            this.pendingAcks.delete(message.ack);
          }
        } else {
          this.handleIncomingMessage(message);
        }
      } catch (_err) {
        console.warn("[GatewayClient] Failed to parse incoming message:", _err);
      }
    });

    this.socket.on("close", () => {
      this.connected = false;
    });

    this.socket.on("error", () => {
      this.connected = false;
      this.fallbackMode = true;
    });
  }

  private handleIncomingMessage(message: GatewayMessage): void {
    const decrypted = this.decryptMessage(message);
    for (const handler of this.messageHandlers) {
      handler(decrypted);
    }
  }

  public async send(message: GatewayMessage): Promise<void> {
    if (this.fallbackMode || !this.connected) {
      this.sendFileMessage(message);
      return;
    }

    const encrypted = this.encryptMessage(message);

    return new Promise((resolve, reject) => {
      const timeout = setTimeout(() => {
        this.pendingAcks.delete(message.id);
        reject(new GatewayDeliveryError(`Message ${message.id} timed out`));
      }, MESSAGE_TIMEOUT);

      this.pendingAcks.set(message.id, { resolve, reject, timeout });

      this.socket?.write(JSON.stringify(encrypted));
    });
  }

  public onMessage(handler: (message: GatewayMessage) => void): void {
    this.messageHandlers.push(handler);
  }

  public disconnect(): void {
    if (this.socket) {
      this.socket.destroy();
      this.socket = null;
    }
    this.connected = false;
    this.pendingAcks.forEach((pending) => {
      clearTimeout(pending.timeout);
      pending.reject(new Error("Connection closed"));
    });
    this.pendingAcks.clear();
  }

  public isConnected(): boolean {
    return this.connected;
  }

  public getFallbackMode(): boolean {
    return this.fallbackMode;
  }

  private encryptMessage(message: GatewayMessage): GatewayMessage {
    const key = this.deriveKey(message.sender_role, message.recipient_role);
    const iv = randomBytes(16);
    const cipher = createCipheriv("aes-256-gcm", key, iv);

    const plaintext = JSON.stringify(message);
    const encrypted = Buffer.concat([cipher.update(plaintext, "utf8"), cipher.final()]);
    const authTag = cipher.getAuthTag();

    return {
      ...message,
      payload: {
        iv: iv.toString("base64"),
        data: Buffer.concat([encrypted, authTag]).toString("base64"),
        timestamp: message.timestamp,
      },
      encrypted: true,
    };
  }

  private decryptMessage(message: GatewayMessage): GatewayMessage {
    if (!message.encrypted) {
      return message;
    }

    const key = this.deriveKey(message.recipient_role, message.sender_role);
    const payload = message.payload as { iv: string; data: string; timestamp: string };

    const iv = Buffer.from(payload.iv, "base64");
    const data = Buffer.from(payload.data, "base64");
    const authTag = data.slice(-16);
    const encrypted = data.slice(0, -16);

    const decipher = createDecipheriv("aes-256-gcm", key, iv);
    decipher.setAuthTag(authTag);

    const decrypted = Buffer.concat([decipher.update(encrypted), decipher.final()]);
    return JSON.parse(decrypted.toString("utf8"));
  }

  private deriveKey(sender: string, recipient: string): Buffer {
    const salt = Buffer.from(`${sender}:${recipient}:${this.squadId}`, "utf8");
    const keyMaterial = Buffer.from(this.meshSecret, "utf8");

    // Use HKDF (HMAC-based Key Derivation Function) for proper key derivation
    return Buffer.from(
      hkdfSync("sha256", keyMaterial, salt, `milimo-mesh:${sender}:${recipient}`, 32),
    );
  }

  private sendFileMessage(message: GatewayMessage): void {
    const queueDir = join(
      process.env.HOME ?? "/tmp",
      ".openclaw/milimo",
      "mesh",
      "pending",
      this.squadId,
      message.recipient_role,
    );
    mkdirSync(queueDir, { recursive: true });

    const filePath = join(queueDir, `${message.id}.json`);
    writeFileSync(filePath, JSON.stringify(message, null, 2));
  }
}

export function getGatewaySocketPath(): string {
  return process.platform === "darwin" ? MACOS_SOCKET_PATH : LINUX_SOCKET_PATH;
}

export function checkGatewayAvailable(): boolean {
  return existsSync(getGatewaySocketPath());
}
