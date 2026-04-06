// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

/**
 * Action Detail Screen
 *
 * Displays details of a pending action with approve/veto options.
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Alert,
  ActivityIndicator,
} from 'react-native';
import { useRoute, useNavigation } from '@react-navigation/native';

import type { RootStackParamList } from '../App';
import type { RouteProp } from '@react-navigation/native';
import { fetchActionDetails, approveAction, vetoAction } from '../api/warroom';
import type { PendingAction } from '../types';

type ActionDetailRouteProp = RouteProp<RootStackParamList, 'ActionDetail'>;

function ActionDetailScreen(): React.JSX.Element {
  const route = useRoute<ActionDetailRouteProp>();
  const navigation = useNavigation();
  const { actionId } = route.params;

  const [action, setAction] = useState<PendingAction | null>(null);
  const [loading, setLoading] = useState(true);
  const [processing, setProcessing] = useState(false);

  useEffect(() => {
    loadActionDetail();
  }, [actionId]);

  const loadActionDetail = async () => {
    try {
      setLoading(true);
      const result = await fetchActionDetails(actionId);
      if (result.ok && result.data) {
        setAction(result.data);
      } else {
        Alert.alert('Error', result.error || 'Failed to load action details');
      }
    } catch (error) {
      console.error('Failed to load action:', error);
      Alert.alert('Error', 'Failed to load action details');
    } finally {
      setLoading(false);
    }
  };

  const handleApprove = useCallback(() => {
    Alert.alert(
      'Approve Action',
      'Are you sure you want to approve this action?',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Approve',
          onPress: async () => {
            setProcessing(true);
            try {
              const result = await approveAction(actionId);
              if (result.ok) {
                Alert.alert('Approved', 'Action has been approved', [
                  { text: 'OK', onPress: () => navigation.goBack() },
                ]);
              } else {
                Alert.alert('Error', result.error || 'Failed to approve action');
              }
            } catch (error) {
              Alert.alert('Error', 'Failed to approve action');
            } finally {
              setProcessing(false);
            }
          },
        },
      ]
    );
  }, [navigation, actionId]);

  const handleVeto = useCallback(() => {
    Alert.alert(
      'Veto Action',
      'Please provide a reason for vetoing this action.',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Veto',
          style: 'destructive',
          onPress: async () => {
            setProcessing(true);
            try {
              const result = await vetoAction(actionId, 'Vetoed via mobile app');
              if (result.ok) {
                Alert.alert('Vetoed', 'Action has been vetoed', [
                  { text: 'OK', onPress: () => navigation.goBack() },
                ]);
              } else {
                Alert.alert('Error', result.error || 'Failed to veto action');
              }
            } catch (error) {
              Alert.alert('Error', 'Failed to veto action');
            } finally {
              setProcessing(false);
            }
          },
        },
      ]
    );
  }, [navigation, actionId]);

  const getRiskColor = (risk: string) => {
    switch (risk) {
      case 'high':
        return '#ef4444';
      case 'medium':
        return '#f97316';
      case 'low':
        return '#22c55e';
      default:
        return '#6b7280';
    }
  };

  if (loading) {
    return (
      <View style={styles.centered}>
        <ActivityIndicator size="large" color="#1a1a2e" />
      </View>
    );
  }

  if (!action) {
    return (
      <View style={styles.centered}>
        <Text>Action not found</Text>
      </View>
    );
  }

  return (
    <ScrollView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.role}>{action.claw_role.toUpperCase()}</Text>
        <View style={[styles.riskBadge, { backgroundColor: getRiskColor(action.risk_level) }]}>
          <Text style={styles.riskText}>{action.risk_level.toUpperCase()}</Text>
        </View>
      </View>

      <View style={styles.section}>
        <Text style={styles.label}>Description</Text>
        <Text style={styles.value}>{action.description}</Text>
      </View>

      <View style={styles.section}>
        <Text style={styles.label}>Confidence</Text>
        <Text style={styles.value}>{(action.confidence * 100).toFixed(0)}%</Text>
      </View>

      <View style={styles.section}>
        <Text style={styles.label}>Type</Text>
        <Text style={styles.value}>{action.action_type}</Text>
      </View>

      <View style={styles.section}>
        <Text style={styles.label}>Payload</Text>
        <Text style={styles.code}>{JSON.stringify(action.payload, null, 2)}</Text>
      </View>

      <View style={styles.section}>
        <Text style={styles.label}>Created</Text>
        <Text style={styles.value}>
          {new Date(action.created_at).toLocaleString()}
        </Text>
      </View>

      <View style={styles.section}>
        <Text style={styles.label}>Expires</Text>
        <Text style={styles.value}>
          {new Date(action.expires_at).toLocaleString()}
        </Text>
      </View>

      <View style={styles.actions}>
        <TouchableOpacity
          style={[styles.button, styles.approveButton]}
          onPress={handleApprove}
          disabled={processing}
        >
          {processing ? (
            <ActivityIndicator color="#fff" />
          ) : (
            <Text style={styles.approveButtonText}>Approve</Text>
          )}
        </TouchableOpacity>

        <TouchableOpacity
          style={[styles.button, styles.vetoButton]}
          onPress={handleVeto}
          disabled={processing}
        >
          {processing ? (
            <ActivityIndicator color="#ef4444" />
          ) : (
            <Text style={styles.vetoButtonText}>Veto</Text>
          )}
        </TouchableOpacity>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#fff',
  },
  centered: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#e5e5e5',
  },
  role: {
    fontSize: 18,
    fontWeight: '700',
    color: '#1a1a2e',
  },
  riskBadge: {
    paddingHorizontal: 12,
    paddingVertical: 4,
    borderRadius: 16,
  },
  riskText: {
    fontSize: 12,
    fontWeight: '600',
    color: '#fff',
  },
  section: {
    padding: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#f0f0f0',
  },
  label: {
    fontSize: 12,
    color: '#6b7280',
    marginBottom: 4,
  },
  value: {
    fontSize: 16,
    color: '#1a1a2e',
  },
  code: {
    fontSize: 14,
    fontFamily: 'monospace',
    color: '#1a1a2e',
    backgroundColor: '#f5f5f5',
    padding: 8,
    borderRadius: 4,
  },
  actions: {
    flexDirection: 'row',
    padding: 16,
    gap: 12,
  },
  button: {
    flex: 1,
    paddingVertical: 16,
    borderRadius: 8,
    alignItems: 'center',
  },
  approveButton: {
    backgroundColor: '#22c55e',
  },
  vetoButton: {
    backgroundColor: '#fff',
    borderWidth: 2,
    borderColor: '#ef4444',
  },
  approveButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
  vetoButtonText: {
    color: '#ef4444',
    fontSize: 16,
    fontWeight: '600',
  },
});

export default ActionDetailScreen;
