// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

/**
 * useAuth Hook
 *
 * Manages authentication state for the mobile app.
 * Integrates with the War Room API for real login/logout.
 */

import { useState, useEffect, useCallback } from 'react';
import { login as apiLogin, logout as apiLogout } from '../api/warroom';
import type { AuthTokens } from '../types';

interface User {
  squadId: string;
  deviceId: string;
}

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  loading: boolean;
  error: string | null;
}

const AUTH_STORAGE_KEY = 'milimo_user';

function loadStoredUser(): User | null {
  try {
    const stored = localStorage.getItem(AUTH_STORAGE_KEY);
    if (stored) {
      return JSON.parse(stored);
    }
  } catch {
    // Storage unavailable
  }
  return null;
}

function storeUser(user: User): void {
  try {
    localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(user));
  } catch {
    // Storage unavailable
  }
}

function clearStoredUser(): void {
  try {
    localStorage.removeItem(AUTH_STORAGE_KEY);
  } catch {
    // Storage unavailable
  }
}

export function useAuth(): AuthState & {
  login: (squadId: string, deviceId: string) => Promise<void>;
  logout: () => Promise<void>;
} {
  const [state, setState] = useState<AuthState>({
    user: null,
    isAuthenticated: false,
    loading: true,
    error: null,
  });

  useEffect(() => {
    checkExistingAuth();
  }, []);

  const checkExistingAuth = async () => {
    try {
      const storedUser = loadStoredUser();
      if (storedUser) {
        setState({
          user: storedUser,
          isAuthenticated: true,
          loading: false,
          error: null,
        });
      } else {
        setState(prev => ({
          ...prev,
          loading: false,
        }));
      }
    } catch (error) {
      setState(prev => ({
        ...prev,
        loading: false,
        error: 'Failed to check authentication',
      }));
    }
  };

  const login = useCallback(async (squadId: string, deviceId: string) => {
    setState(prev => ({ ...prev, loading: true, error: null }));

    try {
      const result = await apiLogin(squadId, deviceId);
      if (result.ok && result.data) {
        const tokens = result.data as AuthTokens;
        const user: User = { squadId, deviceId };
        storeUser(user);
        setState({
          user,
          isAuthenticated: true,
          loading: false,
          error: null,
        });
      } else {
        setState(prev => ({
          ...prev,
          loading: false,
          error: result.error || 'Login failed',
        }));
      }
    } catch (error) {
      setState(prev => ({
        ...prev,
        loading: false,
        error: (error as Error).message || 'Login failed',
      }));
    }
  }, []);

  const logout = useCallback(async () => {
    setState(prev => ({ ...prev, loading: true }));

    try {
      await apiLogout();
    } catch {
      // API logout may fail if already logged out server-side
    }

    clearStoredUser();
    setState({
      user: null,
      isAuthenticated: false,
      loading: false,
      error: null,
    });
  }, []);

  return {
    ...state,
    login,
    logout,
  };
}
