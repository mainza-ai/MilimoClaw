// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

/**
 * Login Screen
 *
 * Authenticates the user with the War Room server.
 */

import React, { useState } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  Alert,
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
} from 'react-native';
import { useNavigation } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import type { RootStackParamList } from '../App';
import { useAuth } from '../hooks/useAuth';

type NavigationProp = NativeStackNavigationProp<RootStackParamList, 'Login'>;

function LoginScreen(): React.JSX.Element {
  const navigation = useNavigation<NavigationProp>();
  const { login, loading, error } = useAuth();
  const [squadId, setSquadId] = useState('');
  const [deviceId, setDeviceId] = useState('');

  const handleLogin = async () => {
    if (!squadId.trim() || !deviceId.trim()) {
      Alert.alert('Error', 'Squad ID and Device ID are required');
      return;
    }

    await login(squadId.trim(), deviceId.trim());
  };

  if (loading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#6366f1" />
        <Text style={styles.loadingText}>Authenticating...</Text>
      </View>
    );
  }

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
    >
      <View style={styles.content}>
        <Text style={styles.title}>Milimo Claw</Text>
        <Text style={styles.subtitle}>War Room Access</Text>

        {error && <Text style={styles.error}>{error}</Text>}

        <View style={styles.form}>
          <Text style={styles.label}>Squad ID</Text>
          <TextInput
            style={styles.input}
            value={squadId}
            onChangeText={setSquadId}
            placeholder="Enter your squad ID"
            placeholderTextColor="#9ca3af"
            autoCapitalize="none"
            autoCorrect={false}
          />

          <Text style={styles.label}>Device ID</Text>
          <TextInput
            style={styles.input}
            value={deviceId}
            onChangeText={setDeviceId}
            placeholder="Enter your device ID"
            placeholderTextColor="#9ca3af"
            autoCapitalize="none"
            autoCorrect={false}
          />

          <TouchableOpacity
            style={styles.loginButton}
            onPress={handleLogin}
            disabled={loading}
          >
            {loading ? (
              <ActivityIndicator color="#fff" />
            ) : (
              <Text style={styles.loginButtonText}>Login</Text>
            )}
          </TouchableOpacity>
        </View>
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#1a1a2e',
  },
  loadingContainer: {
    flex: 1,
    backgroundColor: '#1a1a2e',
    justifyContent: 'center',
    alignItems: 'center',
  },
  loadingText: {
    color: '#fff',
    marginTop: 16,
    fontSize: 16,
  },
  content: {
    flex: 1,
    justifyContent: 'center',
    paddingHorizontal: 32,
  },
  title: {
    fontSize: 32,
    fontWeight: '700',
    color: '#fff',
    textAlign: 'center',
    marginBottom: 8,
  },
  subtitle: {
    fontSize: 18,
    color: '#9ca3af',
    textAlign: 'center',
    marginBottom: 40,
  },
  error: {
    color: '#ef4444',
    textAlign: 'center',
    marginBottom: 16,
    fontSize: 14,
  },
  form: {
    gap: 16,
  },
  label: {
    color: '#d1d5db',
    fontSize: 14,
    fontWeight: '500',
    marginBottom: -8,
  },
  input: {
    backgroundColor: '#2d2d44',
    color: '#fff',
    borderRadius: 8,
    padding: 16,
    fontSize: 16,
    borderWidth: 1,
    borderColor: '#3d3d5c',
  },
  loginButton: {
    backgroundColor: '#6366f1',
    borderRadius: 8,
    padding: 16,
    alignItems: 'center',
    marginTop: 8,
  },
  loginButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
});

export default LoginScreen;
