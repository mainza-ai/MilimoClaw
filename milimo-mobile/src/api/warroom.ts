// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

/**
 * War Room API Client
 *
 * REST API client for communicating with the War Room server.
 */

import type { PendingAction, SquadStatus, ClawHealth, ApiResponse, AuthTokens } from '../types';

const API_BASE_URL = 'https://warroom.milimo.dev/api/v1';

const STORAGE_KEY = 'milimo_auth_tokens';

// Simple in-memory storage (replace with @react-native-async-storage/async-storage in production)
const memoryStore: Record<string, string> = {};

async function storageGet(key: string): Promise<string | null> {
  return memoryStore[key] ?? null;
}

async function storageSet(key: string, value: string): Promise<void> {
  memoryStore[key] = value;
}

async function storageRemove(key: string): Promise<void> {
  delete memoryStore[key];
}

async function getAuthToken(): Promise<string | null> {
  try {
    const stored = await storageGet(STORAGE_KEY);
    if (stored) {
      const tokens: AuthTokens = JSON.parse(stored);
      if (Date.now() < (tokens.expires_in * 1000)) {
        return tokens.token;
      }
    }
  } catch {
    // Storage error, continue without token
  }
  return null;
}

async function setAuthToken(tokens: AuthTokens): Promise<void> {
  try {
    await storageSet(STORAGE_KEY, JSON.stringify(tokens));
  } catch {
    // Storage error, token won't persist
  }
}

async function clearAuthToken(): Promise<void> {
  try {
    await storageRemove(STORAGE_KEY);
  } catch {
    // Storage error
  }
}

async function apiRequest<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<ApiResponse<T>> {
  try {
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
      const error = await response.json().catch(() => ({ error: { message: 'Request failed' } }));
      return {
        ok: false,
        error: error.error?.message || `HTTP ${response.status}`,
      };
    }

    const data = await response.json();
    return { ok: true, data };
  } catch (err) {
    return {
      ok: false,
      error: (err as Error).message,
    };
  }
}

export async function login(squadId: string, deviceId: string): Promise<ApiResponse<AuthTokens>> {
  const result = await apiRequest<AuthTokens>('/auth/token', {
    method: 'POST',
    body: JSON.stringify({ squad_id: squadId, device_id: deviceId }),
  });
  if (result.ok && result.data) {
    await setAuthToken(result.data);
  }
  return result;
}

export async function refreshTokenFn(token: string): Promise<ApiResponse<AuthTokens>> {
  const result = await apiRequest<AuthTokens>('/auth/refresh', {
    method: 'POST',
    body: JSON.stringify({ refresh_token: token }),
  });
  if (result.ok && result.data) {
    await setAuthToken(result.data);
  }
  return result;
}

export async function logout(): Promise<ApiResponse<void>> {
  const result = await apiRequest<void>('/auth/logout', { method: 'POST' });
  if (result.ok) {
    await clearAuthToken();
  }
  return result;
}

export async function fetchPendingActions(): Promise<ApiResponse<PendingAction[]>> {
  const result = await apiRequest<{ items: PendingAction[] }>('/pending');
  if (result.ok && result.data) {
    return { ok: true, data: result.data.items };
  }
  return { ok: false, error: result.error };
}

export async function fetchActionDetails(actionId: string): Promise<ApiResponse<PendingAction>> {
  return apiRequest<PendingAction>(`/pending/${actionId}`);
}

export async function approveAction(
  actionId: string,
  biometricVerified: boolean = false,
  notes?: string
): Promise<ApiResponse<{ success: boolean; action_id: string; status: string }>> {
  return apiRequest(`/pending/${actionId}/approve`, {
    method: 'POST',
    body: JSON.stringify({ biometric_verified: biometricVerified, notes }),
  });
}

export async function vetoAction(
  actionId: string,
  reason: string,
  biometricVerified: boolean = false
): Promise<ApiResponse<{ success: boolean; action_id: string; status: string }>> {
  return apiRequest(`/pending/${actionId}/veto`, {
    method: 'POST',
    body: JSON.stringify({ reason, biometric_verified: biometricVerified }),
  });
}

export async function fetchSquadStatus(): Promise<ApiResponse<SquadStatus>> {
  return apiRequest<SquadStatus>('/status');
}

export async function fetchClawHealth(): Promise<ApiResponse<{ claws: ClawHealth[] }>> {
  return apiRequest<{ claws: ClawHealth[] }>('/status/claws');
}

export { clearAuthToken as logoutStorage };
