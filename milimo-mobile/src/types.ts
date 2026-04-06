// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

/**
 * Shared type definitions for Milimo Mobile
 */

export interface PendingAction {
  id: string;
  type: string;
  claw_role: string;
  action_type: string;
  description: string;
  payload: Record<string, unknown>;
  context?: Record<string, unknown>;
  confidence: number;
  risk_level: string;
  created_at: string;
  expires_at: string;
}

export interface SquadStatus {
  squad_id: string;
  mode: string;
  claws: ClawHealth[];
  pending_actions: number;
}

export interface ClawHealth {
  role: string;
  status: 'healthy' | 'degraded' | 'offline';
  score: number;
  tools: number;
  last_cycle?: string;
}

export interface AuthTokens {
  token: string;
  refresh_token: string;
  expires_in: number;
}

export interface ApiResponse<T> {
  ok: boolean;
  data?: T;
  error?: string;
}
