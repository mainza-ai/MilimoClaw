// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

/**
 * Settings Screen
 *
 * App settings and preferences.
 */

import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Switch,
  Alert,
} from 'react-native';
import { useNavigation } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import type { RootStackParamList } from '../App';
import { useAuth } from '../hooks/useAuth';
import { logout } from '../api/warroom';

type NavigationProp = NativeStackNavigationProp<RootStackParamList>;

interface Settings {
  notificationsEnabled: boolean;
  biometricEnabled: boolean;
  offlineMode: boolean;
  squadId: string;
  deviceId: string;
  appVersion: string;
}

function SettingsScreen(): React.JSX.Element {
  const navigation = useNavigation<NavigationProp>();
  const { logout: authLogout } = useAuth();
  const [settings, setSettings] = useState<Settings>({
    notificationsEnabled: true,
    biometricEnabled: true,
    offlineMode: false,
    squadId: 'my-squad',
    deviceId: 'device-xxx',
    appVersion: '0.1.0',
  });

  const toggleNotifications = (value: boolean) => {
    setSettings(prev => ({ ...prev, notificationsEnabled: value }));
    if (!value) {
      Alert.alert(
        'Notifications Disabled',
        'You will not receive push notifications for pending actions.'
      );
    }
  };

  const toggleBiometric = (value: boolean) => {
    setSettings(prev => ({ ...prev, biometricEnabled: value }));
    if (value) {
      // In production, trigger biometric enrollment check
      Alert.alert(
        'Biometric Enabled',
        'You will be prompted for biometric verification for high-risk actions.'
      );
    }
  };

  const toggleOfflineMode = (value: boolean) => {
    setSettings(prev => ({ ...prev, offlineMode: value }));
  };

  const handleLogout = () => {
    Alert.alert(
      'Log Out',
      'Are you sure you want to log out?',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Log Out',
          style: 'destructive',
          onPress: async () => {
            await logout();
            await authLogout();
            navigation.reset({
              index: 0,
              routes: [{ name: 'Login' as never }],
            });
          },
        },
      ]
    );
  };

  return (
    <ScrollView style={styles.container}>
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Notifications</Text>

        <View style={styles.row}>
          <View style={styles.rowContent}>
            <Text style={styles.rowLabel}>Push Notifications</Text>
            <Text style={styles.rowDescription}>
              Receive alerts for pending actions
            </Text>
          </View>
          <Switch
            value={settings.notificationsEnabled}
            onValueChange={toggleNotifications}
            trackColor={{ false: '#d1d5db', true: '#22c55e' }}
          />
        </View>
      </View>

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Security</Text>

        <View style={styles.row}>
          <View style={styles.rowContent}>
            <Text style={styles.rowLabel}>Biometric Authentication</Text>
            <Text style={styles.rowDescription}>
              Require Face ID / Touch ID for approvals
            </Text>
          </View>
          <Switch
            value={settings.biometricEnabled}
            onValueChange={toggleBiometric}
            trackColor={{ false: '#d1d5db', true: '#22c55e' }}
          />
        </View>
      </View>

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Connectivity</Text>

        <View style={styles.row}>
          <View style={styles.rowContent}>
            <Text style={styles.rowLabel}>Offline Mode</Text>
            <Text style={styles.rowDescription}>
              Queue decisions when offline
            </Text>
          </View>
          <Switch
            value={settings.offlineMode}
            onValueChange={toggleOfflineMode}
            trackColor={{ false: '#d1d5db', true: '#22c55e' }}
          />
        </View>
      </View>

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Account</Text>

        <View style={styles.infoRow}>
          <Text style={styles.infoLabel}>Squad ID</Text>
          <Text style={styles.infoValue}>{settings.squadId}</Text>
        </View>

        <View style={styles.infoRow}>
          <Text style={styles.infoLabel}>Device ID</Text>
          <Text style={styles.infoValue}>{settings.deviceId}</Text>
        </View>

        <TouchableOpacity style={styles.logoutButton} onPress={handleLogout}>
          <Text style={styles.logoutButtonText}>Log Out</Text>
        </TouchableOpacity>
      </View>

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>About</Text>

        <View style={styles.infoRow}>
          <Text style={styles.infoLabel}>App Version</Text>
          <Text style={styles.infoValue}>{settings.appVersion}</Text>
        </View>

        <View style={styles.infoRow}>
          <Text style={styles.infoLabel}>License</Text>
          <Text style={styles.infoValue}>Apache-2.0</Text>
        </View>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  section: {
    backgroundColor: '#fff',
    marginTop: 16,
    paddingHorizontal: 16,
  },
  sectionTitle: {
    fontSize: 14,
    fontWeight: '600',
    color: '#6b7280',
    textTransform: 'uppercase',
    paddingTop: 16,
    paddingBottom: 8,
  },
  row: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#f0f0f0',
  },
  rowContent: {
    flex: 1,
    marginRight: 16,
  },
  rowLabel: {
    fontSize: 16,
    fontWeight: '500',
    color: '#1a1a2e',
  },
  rowDescription: {
    fontSize: 14,
    color: '#6b7280',
    marginTop: 2,
  },
  infoRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#f0f0f0',
  },
  infoLabel: {
    fontSize: 16,
    color: '#1a1a2e',
  },
  infoValue: {
    fontSize: 16,
    color: '#6b7280',
  },
  logoutButton: {
    paddingVertical: 16,
    alignItems: 'center',
  },
  logoutButtonText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#ef4444',
  },
});

export default SettingsScreen;
