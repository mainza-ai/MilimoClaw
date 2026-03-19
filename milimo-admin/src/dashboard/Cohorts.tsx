// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

/**
 * Cohorts Management Dashboard Component
 *
 * Manages cohort creation and progress tracking.
 */

import React, { useState } from "react";

// ---------------------------------------------------------------------------

export interface Cohort {
  id: string;
  name: string;
  template: string;
  status: "pending" | "creating" | "active" | "completed" | "failed";
  totalSquads: number;
  createdSquads: number;
  failedSquads: number;
  createdAt: string;
  completedAt?: string;
}

export interface CohortProgress {
  cohortId: string;
  squadsCreated: number;
  squadsPending: number;
  squadsFailed: number;
  membersInvited: number;
  membersJoined: number;
  errors: Array<{
    squadName: string;
    error: string;
  }>;
}

export interface CohortsProps {
  tenantId: string;
  cohorts: Cohort[];
  onCreateCohort: (data: {
    name: string;
    template: string;
    squads: Array<{
      name: string;
      members: Array<{ email: string; role: string }>;
    }>;
  }) => void;
  onViewProgress: (cohortId: string) => CohortProgress;
  onDeleteCohort: (cohortId: string) => void;
}

// ---------------------------------------------------------------------------

export function Cohorts({
  tenantId,
  cohorts,
  onCreateCohort,
  onViewProgress,
  onDeleteCohort,
}: CohortsProps) {
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [cohortName, setCohortName] = useState("");
  const [cohortTemplate, setCohortTemplate] = useState("campus-ai-tool");
  const [numberOfSquads, setNumberOfSquads] = useState(10);
  const [selectedCohort, setSelectedCohort] = useState<string | null>(null);

  const handleCreateCohort = () => {
    if (!cohortName.trim()) return;

    const squads = Array.from({ length: numberOfSquads }, (_, i) => ({
      name: `${cohortName} - Team ${i + 1}`,
      members: [],
    }));

    onCreateCohort({
      name: cohortName,
      template: cohortTemplate,
      squads,
    });

    setCohortName("");
    setShowCreateForm(false);
  };

  const getProgressPercentage = (cohort: Cohort): number => {
    if (cohort.totalSquads === 0) return 0;
    return Math.round((cohort.createdSquads / cohort.totalSquads) * 100);
  };

  return (
    <div className="cohorts-dashboard">
      <header className="cohorts-header">
        <h1>Cohorts</h1>
        <p className="cohorts-description">
          Create and manage bulk squad deployments for incubator programs and university cohorts.
        </p>
        <button
          className="btn-primary"
          onClick={() => setShowCreateForm(true)}
        >
          Create Cohort
        </button>
      </header>

      {showCreateForm && (
        <div className="create-form-overlay">
          <div className="create-form">
            <h2>Create New Cohort</h2>
            <div className="form-group">
              <label>Cohort Name</label>
              <input
                type="text"
                value={cohortName}
                onChange={(e) => setCohortName(e.target.value)}
                placeholder="e.g., Fall 2026 Incubator"
              />
            </div>
            <div className="form-group">
              <label>Template</label>
              <select
                value={cohortTemplate}
                onChange={(e) => setCohortTemplate(e.target.value)}
              >
                <option value="campus-ai-tool">Campus AI Tool</option>
                <option value="content-agency">Content Agency</option>
                <option value="ai-micro-saas">AI Micro-SaaS</option>
              </select>
            </div>
            <div className="form-group">
              <label>Number of Squads</label>
              <input
                type="number"
                min="1"
                max="100"
                value={numberOfSquads}
                onChange={(e) => setNumberOfSquads(parseInt(e.target.value) || 1)}
              />
            </div>
            <div className="form-actions">
              <button
                className="btn-secondary"
                onClick={() => setShowCreateForm(false)}
              >
                Cancel
              </button>
              <button
                className="btn-primary"
                onClick={handleCreateCohort}
                disabled={!cohortName.trim()}
              >
                Create Cohort
              </button>
            </div>
          </div>
        </div>
      )}

      <div className="cohorts-grid">
        {cohorts.map((cohort) => (
          <div
            key={cohort.id}
            className={`cohort-card ${cohort.status}`}
          >
            <div className="cohort-header">
              <h3>{cohort.name}</h3>
              <span className={`status-badge ${cohort.status}`}>
                {cohort.status}
              </span>
            </div>
            <div className="cohort-meta">
              <span>Template: {cohort.template}</span>
              <span>Created: {cohort.createdAt}</span>
            </div>
            <div className="cohort-progress">
              <div className="progress-bar">
                <div
                  className="progress-fill"
                  style={{ width: `${getProgressPercentage(cohort)}%` }}
                />
              </div>
              <div className="progress-text">
                {cohort.createdSquads} / {cohort.totalSquads} squads
                {cohort.failedSquads > 0 && (
                  <span className="failed-count">
                    ({cohort.failedSquads} failed)
                  </span>
                )}
              </div>
            </div>
            <div className="cohort-actions">
              <button
                className="btn-small btn-secondary"
                onClick={() => setSelectedCohort(cohort.id)}
              >
                View Details
              </button>
              {cohort.status !== "creating" && (
                <button
                  className="btn-small btn-danger"
                  onClick={() => onDeleteCohort(cohort.id)}
                >
                  Delete
                </button>
              )}
            </div>
          </div>
        ))}
      </div>

      {cohorts.length === 0 && (
        <div className="empty-state">
          <h3>No Cohorts Yet</h3>
          <p>Create a cohort to bulk-deploy squads for your program.</p>
        </div>
      )}

      {selectedCohort && (
        <CohortProgressModal
          cohortId={selectedCohort}
          getProgress={onViewProgress}
          onClose={() => setSelectedCohort(null)}
        />
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------

function CohortProgressModal({
  cohortId,
  getProgress,
  onClose,
}: {
  cohortId: string;
  getProgress: (id: string) => CohortProgress;
  onClose: () => void;
}) {
  const progress = getProgress(cohortId);

  return (
    <div className="modal-overlay">
      <div className="modal">
        <h2>Cohort Progress</h2>
        <div className="progress-stats">
          <div className="stat">
            <span className="stat-label">Squads Created</span>
            <span className="stat-value">{progress.squadsCreated}</span>
          </div>
          <div className="stat">
            <span className="stat-label">Squads Pending</span>
            <span className="stat-value">{progress.squadsPending}</span>
          </div>
          <div className="stat">
            <span className="stat-label">Members Invited</span>
            <span className="stat-value">{progress.membersInvited}</span>
          </div>
          <div className="stat">
            <span className="stat-label">Members Joined</span>
            <span className="stat-value">{progress.membersJoined}</span>
          </div>
        </div>
        {progress.errors.length > 0 && (
          <div className="errors-section">
            <h3>Errors</h3>
            <ul>
              {progress.errors.map((error, i) => (
                <li key={i}>
                  <strong>{error.squadName}:</strong> {error.error}
                </li>
              ))}
            </ul>
          </div>
        )}
        <button className="btn-primary" onClick={onClose}>
          Close
        </button>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------

export default Cohorts;
