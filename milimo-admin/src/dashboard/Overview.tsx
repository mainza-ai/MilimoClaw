// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

/**
 * Tenant Overview Dashboard Component
 *
 * Displays high-level metrics and status for a tenant.
 */

import React from "react";

// ---------------------------------------------------------------------------

export interface TenantOverviewProps {
  tenant: {
    id: string;
    name: string;
    type: string;
    status: string;
    billing: {
      plan: string;
    };
  };
  metrics: {
    totalSquads: number;
    activeSquads: number;
    totalUsers: number;
    activeUsers: number;
    storageUsedGb: number;
    storageLimitGb: number;
    apiCallsThisMonth: number;
    apiLimitPerMonth: number;
  };
  recentActivity: Array<{
    id: string;
    type: string;
    description: string;
    timestamp: string;
  }>;
}

// ---------------------------------------------------------------------------

export function Overview({ tenant, metrics, recentActivity }: TenantOverviewProps) {
  const squadUtilization = Math.round(
    (metrics.activeSquads / Math.max(metrics.totalSquads, 1)) * 100
  );

  const storageUtilization = Math.round(
    (metrics.storageUsedGb / metrics.storageLimitGb) * 100
  );

  const apiUtilization = Math.round(
    (metrics.apiCallsThisMonth / metrics.apiLimitPerMonth) * 100
  );

  return (
    <div className="overview-dashboard">
      <header className="overview-header">
        <h1>{tenant.name}</h1>
        <span className={`status-badge ${tenant.status}`}>
          {tenant.status}
        </span>
        <span className="plan-badge">{tenant.billing.plan}</span>
      </header>

      <section className="metrics-grid">
        <div className="metric-card">
          <h3>Active Squads</h3>
          <div className="metric-value">
            {metrics.activeSquads} / {metrics.totalSquads}
          </div>
          <div className="metric-bar">
            <div
              className="metric-fill"
              style={{ width: `${squadUtilization}%` }}
            />
          </div>
        </div>

        <div className="metric-card">
          <h3>Active Users</h3>
          <div className="metric-value">{metrics.activeUsers}</div>
          <div className="metric-secondary">
            of {metrics.totalUsers} total
          </div>
        </div>

        <div className="metric-card">
          <h3>Storage Used</h3>
          <div className="metric-value">
            {metrics.storageUsedGb} GB
          </div>
          <div className="metric-bar">
            <div
              className={`metric-fill ${storageUtilization > 80 ? "warning" : ""}`}
              style={{ width: `${storageUtilization}%` }}
            />
          </div>
          <div className="metric-secondary">
            of {metrics.storageLimitGb} GB limit
          </div>
        </div>

        <div className="metric-card">
          <h3>API Calls</h3>
          <div className="metric-value">
            {metrics.apiCallsThisMonth.toLocaleString()}
          </div>
          <div className="metric-bar">
            <div
              className={`metric-fill ${apiUtilization > 80 ? "warning" : ""}`}
              style={{ width: `${apiUtilization}%` }}
            />
          </div>
          <div className="metric-secondary">
            of {metrics.apiLimitPerMonth.toLocaleString()} monthly
          </div>
        </div>
      </section>

      <section className="recent-activity">
        <h2>Recent Activity</h2>
        <table className="activity-table">
          <thead>
            <tr>
              <th>Type</th>
              <th>Description</th>
              <th>Time</th>
            </tr>
          </thead>
          <tbody>
            {recentActivity.map((activity) => (
              <tr key={activity.id}>
                <td>
                  <span className={`activity-type ${activity.type}`}>
                    {activity.type}
                  </span>
                </td>
                <td>{activity.description}</td>
                <td>{activity.timestamp}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}

// ---------------------------------------------------------------------------

export default Overview;
