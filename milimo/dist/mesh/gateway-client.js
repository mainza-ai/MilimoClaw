"use strict";
// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
exports.GatewayClient = exports.GatewayDeliveryError = void 0;
exports.getGatewaySocketPath = getGatewaySocketPath;
exports.checkGatewayAvailable = checkGatewayAvailable;
/**
 * Gateway Client
 *
 * Unix socket connection to OpenShell gateway for inter-claw messaging.
 * Falls back to file-based queues when gateway unavailable.
 */
const net = __importStar(require("node:net"));
const node_crypto_1 = require("node:crypto");
const node_path_1 = require("node:path");
const node_fs_1 = require("node:fs");
class GatewayDeliveryError extends Error {
    constructor(message) {
        super(message);
        this.name = "GatewayDeliveryError";
    }
}
exports.GatewayDeliveryError = GatewayDeliveryError;
const LINUX_SOCKET_PATH = "/var/run/openshell/gateway.sock";
const MACOS_SOCKET_PATH = "/tmp/openshell-gateway.sock";
const MAX_RETRIES = 5;
const INITIAL_RETRY_DELAY = 1000;
const MAX_RETRY_DELAY = 30000;
const MESSAGE_TIMEOUT = 5000;
class GatewayClient {
    squadId;
    meshSecret;
    socketPath;
    socket = null;
    connected = false;
    fallbackMode = false;
    messageHandlers = [];
    pendingAcks = new Map();
    retryCount = 0;
    constructor(options) {
        this.squadId = options.squadId;
        this.meshSecret = options.meshSecret;
        this.socketPath = process.platform === "darwin" ? MACOS_SOCKET_PATH : LINUX_SOCKET_PATH;
        if (options.onMessage) {
            this.messageHandlers.push(options.onMessage);
        }
    }
    async connect() {
        if (this.connected) {
            return;
        }
        if (!(0, node_fs_1.existsSync)(this.socketPath)) {
            this.fallbackMode = true;
            return;
        }
        return new Promise((resolve, reject) => {
            this.socket = new net.Socket();
            const onConnect = () => {
                this.connected = true;
                this.fallbackMode = false;
                this.retryCount = 0;
                this.setupSocketHandlers();
                resolve();
            };
            const onError = (err) => {
                this.socket?.destroy();
                this.socket = null;
                if (this.retryCount < MAX_RETRIES) {
                    const delay = Math.min(INITIAL_RETRY_DELAY * Math.pow(2, this.retryCount), MAX_RETRY_DELAY);
                    this.retryCount++;
                    setTimeout(() => {
                        this.connect().then(resolve).catch(reject);
                    }, delay);
                }
                else {
                    this.fallbackMode = true;
                    resolve();
                }
            };
            this.socket.once("connect", onConnect);
            this.socket.once("error", onError);
            this.socket.connect(this.socketPath);
        });
    }
    setupSocketHandlers() {
        if (!this.socket)
            return;
        this.socket.on("data", (data) => {
            try {
                const message = JSON.parse(data.toString());
                if ("ack" in message) {
                    const pending = this.pendingAcks.get(message.ack);
                    if (pending) {
                        clearTimeout(pending.timeout);
                        pending.resolve();
                        this.pendingAcks.delete(message.ack);
                    }
                }
                else {
                    this.handleIncomingMessage(message);
                }
            }
            catch {
                // Ignore parse errors
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
    handleIncomingMessage(message) {
        const decrypted = this.decryptMessage(message);
        for (const handler of this.messageHandlers) {
            handler(decrypted);
        }
    }
    async send(message) {
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
    onMessage(handler) {
        this.messageHandlers.push(handler);
    }
    disconnect() {
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
    isConnected() {
        return this.connected;
    }
    getFallbackMode() {
        return this.fallbackMode;
    }
    encryptMessage(message) {
        const key = this.deriveKey(message.sender_role, message.recipient_role);
        const iv = (0, node_crypto_1.randomBytes)(16);
        const cipher = (0, node_crypto_1.createCipheriv)("aes-256-gcm", key, iv);
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
    decryptMessage(message) {
        if (!message.encrypted) {
            return message;
        }
        const key = this.deriveKey(message.recipient_role, message.sender_role);
        const payload = message.payload;
        const iv = Buffer.from(payload.iv, "base64");
        const data = Buffer.from(payload.data, "base64");
        const authTag = data.slice(-16);
        const encrypted = data.slice(0, -16);
        const decipher = (0, node_crypto_1.createDecipheriv)("aes-256-gcm", key, iv);
        decipher.setAuthTag(authTag);
        const decrypted = Buffer.concat([decipher.update(encrypted), decipher.final()]);
        return JSON.parse(decrypted.toString("utf8"));
    }
    deriveKey(sender, recipient) {
        const salt = Buffer.from(`${sender}:${recipient}`, "utf8");
        const secret = Buffer.from(this.meshSecret, "utf8");
        const combined = Buffer.concat([salt, secret]);
        const key = Buffer.alloc(32);
        for (let i = 0; i < 32; i++) {
            key[i] = combined[i % combined.length] ?? 0;
        }
        return key;
    }
    sendFileMessage(message) {
        const queueDir = (0, node_path_1.join)(process.env.HOME ?? "/tmp", ".milimo", "mesh", "pending", this.squadId, message.recipient_role);
        (0, node_fs_1.mkdirSync)(queueDir, { recursive: true });
        const filePath = (0, node_path_1.join)(queueDir, `${message.id}.json`);
        (0, node_fs_1.writeFileSync)(filePath, JSON.stringify(message, null, 2));
    }
}
exports.GatewayClient = GatewayClient;
function getGatewaySocketPath() {
    return process.platform === "darwin" ? MACOS_SOCKET_PATH : LINUX_SOCKET_PATH;
}
function checkGatewayAvailable() {
    return (0, node_fs_1.existsSync)(getGatewaySocketPath());
}
//# sourceMappingURL=gateway-client.js.map