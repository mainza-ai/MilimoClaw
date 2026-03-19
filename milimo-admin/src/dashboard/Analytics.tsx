// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

/**
 * Analytics Dashboard Component
 *
 * Displays usage analytics and reports for a tenant.
 */

import React, { useState } from "react";
import {
  LineChart,
  Line,
  AreaChart,
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";

// ---------------------------------------------------------------------------

export interface AnalyticsProps {
  tenantId: string;
  usageData: Array<{
    date: string;
    apiCalls: number;
    activeUsers: number;
    storageGb: number;
  }>;
  squadMetrics: Array<{
    squadId: string;
    squadName: string;
    actions: number;
    approvals: number;
    rejections: number;
    avgResponseTime: number;
  }>;
  summary: {
    totalApiCalls: number;
    totalActions: number;
    totalApprovals: number;
    totalRejections: number;
    avgResponseTime: number;
    peakConcurrency: number;
  };
}

export type TimeRange = "7d" | "30d" | "90d" | "1y";

// ---------------------------------------------------------------------------

export function Analytics({
  tenantId,
  usageData,
  squadMetrics,
  summary,
}: AnalyticsProps) {
  const [timeRange, setTimeRange] = useState<TimeRange>("30d");

  const approvalRate =
    summary.totalActions > 0
      ? Math.round(
          (summary.totalApprovals / summary.totalActions) * 100
        )
      : 0;

  return (
    <div className="analytics-dashboard">
      <header className="analytics-header">
        <h1>Analytics</h1>
        <div className="time-range-selector">
          <button
            className={timeRange === "7d" ? "active" : ""}
            onClick={() => setTimeRange("7d")}
          >
            7 Days
          </button>
          <button
            className={timeRange === "30d" ? "active" : ""}
            onClick={() => setTimeRange("30d")}
          >
            30 Days
          </button>
          <button
            className={timeRange === "90d" ? "active" : ""}
            onClick={() => setTimeRange("90d")}
          >
            90 Days
          </button>
          <button
            className={timeRange === "1y" ? "active" : ""}
            onClick={() => setTimeRange("1y")}
          >
            1 Year
          </button>
        </div>
      </header>

      <section className="summary-cards">
        <div className="summary-card">
          <h3>Total API Calls</h3>
          <div className="summary-value">
            {summary.totalApiCalls.toLocaleString()}
          </div>
        </div>
        <div className="summary-card">
          <h3>Total Actions</h3>
          <div className="summary-value">
            {summary.totalActions.toLocaleString()}
          </div>
        </div>
        <div className="summary-card">
          <h3>Approval Rate</h3>
          <div className="summary-value">{approvalRate}%</div>
          <div className="summary-secondary">
            {summary.totalApprovals} / {summary.totalActions}
          </div>
        </div>
        <div className="summary-card">
          <h3>Avg Response Time</h3>
          <div className="summary-value">{summary.avgResponseTime}ms</div>
        </div>
        <div className="summary-card">
          <h3>Peak Concurrency</h3>
          <div className="summary-value">{summary.peakConcurrency}</div>
          <div className="summary-secondary">simultaneous users</div>
        </div>
      </section>

      <section className="charts-grid">
        <div className="chart-card">
          <h3>API Usage Over Time</h3>
          <ResponsiveContainer width="100%" height={250}>
            <AreaChart data={usageData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" />
              <YAxis />
              <Tooltip />
              <Area
                type="monotone"
                dataKey="apiCalls"
                stroke="#4F46E5"
                fill="#4F46E5"
                fillOpacity={0.3}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        <div className="chart-card">
          <h3>Active Users</h3>
          <ResponsiveContainer width="100%" height={250}>
            <LineChart data={usageData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" />
              <YAxis />
              <Tooltip />
              <Line
                type="monotone"
                dataKey="activeUsers"
                stroke="#10B981"
                strokeWidth={2}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>

        <div className="chart-card">
          <h3>Storage Growth</h3>
          <ResponsiveContainer width="100%" height={250}>
            <AreaChart data={usageData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" />
              <YAxis />
              <Tooltip />
              <Area
                type="monotone"
                dataKey="storageGb"
                stroke="#F59E0B"
                fill="#F59E0B"
                fillOpacity={0.3}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </section>

      <section className="squad-performance">
        <h2>Squad Performance</h2>
        <table className="squad-metrics-table">
          <thead>
            <tr>
              <th>Squad</th>
              <th>Actions</th>
              <th>Approvals</th>
              <th>Rejections</th>
              <th>Avg Response</th>
            </tr>
          </thead>
          <tbody>
            {squadMetrics.map((squad) => (
              <tr key={squad.squadId}>
                <td>{squad.squadName}</td>
                <td>{squad.actions.toLocaleString()}</td>
                <td className="metric-positive">
                  {squad.approvals.toLocaleString()}
                </td>
                <td className="metric-negative">
                  {squad.rejections.toLocaleString()}
                </td>
                <td>{squad.avgResponseTime}ms</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className="export-actions">
        <button className="btn-secondary">
          Export CSV
        </button>
        <button className="btn-secondary">
          Export PDF Report
        </button>
      </section>
    </div>
  );
}

// ---------------------------------------------------------------------------

export default Analytics;
