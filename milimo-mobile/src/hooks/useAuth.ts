// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

/**
 * useAuth Hook
 *
 * Manages authentication state for the mobile app.
 */

import { useState, useEffect, useCallback } from 'react';

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
      // In production, check secure storage for existing token
      // For now, simulate no existing auth
      setState(prev => ({
        ...prev,
        loading: false,
      }));
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
      // In production, call auth API and store token securely
      await new Promise(resolve => setTimeout(resolve, 1000));

      setState({
        user: { squadId, deviceId },
        isAuthenticated: true,
        loading: false,
        error: null,
      });
    } catch (error) {
      setState(prev => ({
        ...prev,
        loading: false,
        error: 'Login failed',
      }));
    }
  }, []);

  const logout = useCallback(async () => {
    setState(prev => ({ ...prev, loading: true }));

    try {
      // In production, clear secure storage
      await new Promise(resolve => setTimeout(resolve, 500));

      setState({
        user: null,
        isAuthenticated: false,
        loading: false,
        error: null,
      });
    } catch (error) {
      setState(prev => ({
        ...prev,
        loading: false,
        error: 'Logout failed',
      }));
    }
  }, []);

  return {
    ...state,
    login,
    logout,
  };
}
