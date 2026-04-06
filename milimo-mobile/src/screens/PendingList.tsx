// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

/**
 * Pending List Screen
 *
 * Displays list of pending actions requiring approval.
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  FlatList,
  TouchableOpacity,
  RefreshControl,
  Text,
  StyleSheet,
  Alert,
} from 'react-native';
import { useNavigation } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';

import type { RootStackParamList } from '../App';
import ActionCard from '../components/ActionCard';
import { useAuth } from '../hooks/useAuth';
import { fetchPendingActions, approveAction, vetoAction } from '../api/warroom';
import type { PendingAction } from '../types';

type NavigationProp = NativeStackNavigationProp<RootStackParamList, 'PendingList'>;

function PendingListScreen(): React.JSX.Element {
  const navigation = useNavigation<NavigationProp>();
  const { user, isAuthenticated } = useAuth();

  const [pendingActions, setPendingActions] = useState<PendingAction[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadPendingActions = useCallback(async () => {
    try {
      setError(null);
      const actions = await fetchPendingActions();
      setPendingActions(actions);
    } catch (err) {
      setError('Failed to load pending actions');
      console.error(err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    if (isAuthenticated) {
      loadPendingActions();
    }
  }, [isAuthenticated, loadPendingActions]);

  const handleRefresh = useCallback(() => {
    setRefreshing(true);
    loadPendingActions();
  }, [loadPendingActions]);

  const handleActionPress = useCallback((actionId: string) => {
    navigation.navigate('ActionDetail', { actionId });
  }, [navigation]);

  const handleApprove = useCallback((actionId: string) => {
    Alert.alert(
      'Approve Action',
      'Are you sure you want to approve this action?',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Approve',
          style: 'default',
          onPress: async () => {
            const result = await approveAction(actionId);
            if (result.ok) {
              setPendingActions(prev => prev.filter(a => a.id !== actionId));
            } else {
              Alert.alert('Error', result.error || 'Failed to approve action');
            }
          },
        },
      ]
    );
  }, []);

  const handleVeto = useCallback((actionId: string) => {
    Alert.alert(
      'Veto Action',
      'Are you sure you want to veto this action?',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Veto',
          style: 'destructive',
          onPress: async () => {
            const result = await vetoAction(actionId, 'Vetoed via mobile app');
            if (result.ok) {
              setPendingActions(prev => prev.filter(a => a.id !== actionId));
            } else {
              Alert.alert('Error', result.error || 'Failed to veto action');
            }
          },
        },
      ]
    );
  }, []);

  const renderItem = useCallback(({ item }: { item: PendingAction }) => (
    <ActionCard
      action={item}
      onPress={() => handleActionPress(item.id)}
      onApprove={() => handleApprove(item.id)}
      onVeto={() => handleVeto(item.id)}
    />
  ), [handleActionPress, handleApprove, handleVeto]);

  const keyExtractor = useCallback((item: PendingAction) => item.id, []);

  if (!isAuthenticated) {
    return (
      <View style={styles.centered}>
        <Text style={styles.errorText}>Please log in to view pending actions</Text>
      </View>
    );
  }

  if (loading) {
    return (
      <View style={styles.centered}>
        <Text>Loading...</Text>
      </View>
    );
  }

  if (error) {
    return (
      <View style={styles.centered}>
        <Text style={styles.errorText}>{error}</Text>
        <TouchableOpacity style={styles.retryButton} onPress={loadPendingActions}>
          <Text style={styles.retryButtonText}>Retry</Text>
        </TouchableOpacity>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <FlatList
        data={pendingActions}
        renderItem={renderItem}
        keyExtractor={keyExtractor}
        contentContainerStyle={styles.listContent}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={handleRefresh}
            colors={['#1a1a2e']}
          />
        }
        ListEmptyComponent={
          <View style={styles.emptyContainer}>
            <Text style={styles.emptyText}>No pending actions</Text>
            <Text style={styles.emptySubtext}>
              All caught up! Pull to refresh for new items.
            </Text>
          </View>
        }
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  listContent: {
    padding: 16,
  },
  centered: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  errorText: {
    fontSize: 16,
    color: '#ef4444',
    textAlign: 'center',
    marginBottom: 16,
  },
  retryButton: {
    backgroundColor: '#1a1a2e',
    paddingHorizontal: 24,
    paddingVertical: 12,
    borderRadius: 8,
  },
  retryButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
  emptyContainer: {
    alignItems: 'center',
    paddingVertical: 40,
  },
  emptyText: {
    fontSize: 18,
    fontWeight: '600',
    color: '#333',
    marginBottom: 8,
  },
  emptySubtext: {
    fontSize: 14,
    color: '#666',
    textAlign: 'center',
  },
});

export default PendingListScreen;
