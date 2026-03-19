// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

/**
 * Action Card Component
 *
 * Displays a pending action in a card format.
 */

import React from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
} from 'react-native';

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

interface ActionCardProps {
  action: PendingAction;
  onPress: () => void;
  onApprove: () => void;
  onVeto: () => void;
}

function ActionCard({ action, onPress, onApprove, onVeto }: ActionCardProps): React.JSX.Element {
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

  const formatTimeAgo = (dateString: string) => {
    const now = new Date();
    const date = new Date(dateString);
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    const diffHours = Math.floor(diffMins / 60);
    if (diffHours < 24) return `${diffHours}h ago`;
    const diffDays = Math.floor(diffHours / 24);
    return `${diffDays}d ago`;
  };

  return (
    <TouchableOpacity style={styles.card} onPress={onPress} activeOpacity={0.7}>
      <View style={styles.header}>
        <View style={styles.roleContainer}>
          <Text style={styles.role}>{action.claw_role}</Text>
          <Text style={styles.actionType}>{action.action_type}</Text>
        </View>
        <View style={[styles.riskBadge, { backgroundColor: getRiskColor(action.risk_level) }]}>
          <Text style={styles.riskText}>{action.risk_level}</Text>
        </View>
      </View>

      <Text style={styles.description} numberOfLines={2}>
        {action.description}
      </Text>

      <View style={styles.footer}>
        <View style={styles.meta}>
          <Text style={styles.confidence}>
            {(action.confidence * 100).toFixed(0)}% confident
          </Text>
          <Text style={styles.time}>{formatTimeAgo(action.created_at)}</Text>
        </View>

        <View style={styles.actions}>
          <TouchableOpacity style={styles.approveButton} onPress={onApprove}>
            <Text style={styles.approveText}>Approve</Text>
          </TouchableOpacity>

          <TouchableOpacity style={styles.vetoButton} onPress={onVeto}>
            <Text style={styles.vetoText}>Veto</Text>
          </TouchableOpacity>
        </View>
      </View>
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 4,
    elevation: 2,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 8,
  },
  roleContainer: {
    flex: 1,
  },
  role: {
    fontSize: 12,
    fontWeight: '600',
    color: '#6b7280',
    textTransform: 'uppercase',
  },
  actionType: {
    fontSize: 14,
    fontWeight: '500',
    color: '#1a1a2e',
    marginTop: 2,
  },
  riskBadge: {
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 12,
  },
  riskText: {
    fontSize: 12,
    fontWeight: '600',
    color: '#fff',
    textTransform: 'uppercase',
  },
  description: {
    fontSize: 16,
    color: '#374151',
    lineHeight: 22,
    marginBottom: 12,
  },
  footer: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  meta: {
    flex: 1,
  },
  confidence: {
    fontSize: 12,
    color: '#22c55e',
    fontWeight: '500',
  },
  time: {
    fontSize: 12,
    color: '#9ca3af',
    marginTop: 2,
  },
  actions: {
    flexDirection: 'row',
    gap: 8,
  },
  approveButton: {
    backgroundColor: '#22c55e',
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 8,
  },
  approveText: {
    color: '#fff',
    fontSize: 14,
    fontWeight: '600',
  },
  vetoButton: {
    backgroundColor: '#fff',
    borderWidth: 1,
    borderColor: '#ef4444',
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 8,
  },
  vetoText: {
    color: '#ef4444',
    fontSize: 14,
    fontWeight: '600',
  },
});

export default ActionCard;
