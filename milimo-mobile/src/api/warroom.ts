// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

/**
 * War Room API Client
 *
 * REST API client for communicating with the War Room server.
 */

const API_BASE_URL = 'https://warroom.milimo.dev/api/v1';

interface PendingAction {
  id: string;
  type: string;
  claw_role: string;
  action_type: string;
  description: string;
  confidence: number;
  risk_level: 'low' | 'medium' | 'high';
  created_at: string;
  expires_at: string;
}

interface SquadStatus {
  squad_id: string;
  mesh_status: string;
  claws_online: number;
  pending_count: number;
  approved_today: number;
  vetoed_today: number;
  rate_limit: {
    used: number;
    limit: number;
    resets_at: string;
  };
  last_activity: string;
}

async function getAuthToken(): Promise<string | null> {
  // In production, retrieve from secure storage
  return 'mock-token';
}

async function apiRequest<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const token = await getAuthToken();

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ message: 'Request failed' }));
    throw new Error(error.message || `HTTP ${response.status}`);
  }

  return response.json();
}

export async function fetchPendingActions(): Promise<PendingAction[]> {
  const response = await apiRequest<{ items: PendingAction[] }>('/pending');
  return response.items;
}

export async function fetchActionDetails(actionId: string): Promise<PendingAction> {
  return apiRequest<PendingAction>(`/pending/${actionId}`);
}

export async function approveAction(
  actionId: string,
  biometricVerified: boolean = false,
  notes?: string
): Promise<{ success: boolean; action_id: string; status: string }> {
  return apiRequest(`/pending/${actionId}/approve`, {
    method: 'POST',
    body: JSON.stringify({ biometric_verified: biometricVerified, notes }),
  });
}

export async function vetoAction(
  actionId: string,
  reason: string,
  biometricVerified: boolean = false
): Promise<{ success: boolean; action_id: string; status: string }> {
  return apiRequest(`/pending/${actionId}/veto`, {
    method: 'POST',
    body: JSON.stringify({ reason, biometric_verified: biometricVerified }),
  });
}

export async function fetchSquadStatus(): Promise<SquadStatus> {
  return apiRequest<SquadStatus>('/status');
}

export async function fetchClawHealth(): Promise<{
  claws: Array<{
    role: string;
    status: string;
    region: string;
    last_heartbeat: string;
    actions_today: number;
  }>;
}> {
  return apiRequest('/status/claws');
}

export type { PendingAction, SquadStatus };
