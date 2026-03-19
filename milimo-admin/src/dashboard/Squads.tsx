// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

/**
 * Squads Management Dashboard Component
 *
 * Manages squads within a tenant.
 */

import React, { useState } from "react";

// ---------------------------------------------------------------------------

export interface Squad {
  id: string;
  name: string;
  template: string;
  members: number;
  status: "active" | "inactive" | "suspended";
  createdAt: string;
  lastActive: string;
}

export interface SquadsProps {
  tenantId: string;
  squads: Squad[];
  onCreateSquad: (data: { name: string; template: string }) => void;
  onSuspendSquad: (squadId: string) => void;
  onActivateSquad: (squadId: string) => void;
  onDeleteSquad: (squadId: string) => void;
}

// ---------------------------------------------------------------------------

export function Squads({
  tenantId,
  squads,
  onCreateSquad,
  onSuspendSquad,
  onActivateSquad,
  onDeleteSquad,
}: SquadsProps) {
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [newSquadName, setNewSquadName] = useState("");
  const [newSquadTemplate, setNewSquadTemplate] = useState("content-agency");
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");

  const filteredSquads = squads.filter((squad) => {
    const matchesSearch = squad.name
      .toLowerCase()
      .includes(searchQuery.toLowerCase());
    const matchesStatus =
      statusFilter === "all" || squad.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  const handleCreate = () => {
    if (newSquadName.trim()) {
      onCreateSquad({
        name: newSquadName.trim(),
        template: newSquadTemplate,
      });
      setNewSquadName("");
      setShowCreateForm(false);
    }
  };

  return (
    <div className="squads-dashboard">
      <header className="squads-header">
        <h1>Squads</h1>
        <button
          className="btn-primary"
          onClick={() => setShowCreateForm(true)}
        >
          Create Squad
        </button>
      </header>

      <div className="squads-toolbar">
        <input
          type="text"
          placeholder="Search squads..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="search-input"
        />
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="status-filter"
        >
          <option value="all">All Status</option>
          <option value="active">Active</option>
          <option value="inactive">Inactive</option>
          <option value="suspended">Suspended</option>
        </select>
      </div>

      {showCreateForm && (
        <div className="create-form">
          <h3>Create New Squad</h3>
          <div className="form-group">
            <label>Squad Name</label>
            <input
              type="text"
              value={newSquadName}
              onChange={(e) => setNewSquadName(e.target.value)}
              placeholder="Enter squad name"
            />
          </div>
          <div className="form-group">
            <label>Template</label>
            <select
              value={newSquadTemplate}
              onChange={(e) => setNewSquadTemplate(e.target.value)}
            >
              <option value="content-agency">Content Agency</option>
              <option value="design-studio">Design Studio</option>
              <option value="ai-micro-saas">AI Micro-SaaS</option>
              <option value="campus-ai-tool">Campus AI Tool</option>
            </select>
          </div>
          <div className="form-actions">
            <button className="btn-secondary" onClick={() => setShowCreateForm(false)}>
              Cancel
            </button>
            <button className="btn-primary" onClick={handleCreate}>
              Create
            </button>
          </div>
        </div>
      )}

      <table className="squads-table">
        <thead>
          <tr>
            <th>Name</th>
            <th>Template</th>
            <th>Members</th>
            <th>Status</th>
            <th>Created</th>
            <th>Last Active</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {filteredSquads.map((squad) => (
            <tr key={squad.id}>
              <td className="squad-name">{squad.name}</td>
              <td>{squad.template}</td>
              <td>{squad.members}</td>
              <td>
                <span className={`status-badge ${squad.status}`}>
                  {squad.status}
                </span>
              </td>
              <td>{squad.createdAt}</td>
              <td>{squad.lastActive}</td>
              <td className="actions">
                {squad.status === "active" && (
                  <button
                    className="btn-small btn-warning"
                    onClick={() => onSuspendSquad(squad.id)}
                  >
                    Suspend
                  </button>
                )}
                {squad.status === "suspended" && (
                  <button
                    className="btn-small btn-success"
                    onClick={() => onActivateSquad(squad.id)}
                  >
                    Activate
                  </button>
                )}
                <button
                  className="btn-small btn-danger"
                  onClick={() => onDeleteSquad(squad.id)}
                >
                  Delete
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {filteredSquads.length === 0 && (
        <div className="empty-state">
          <p>No squads found matching your criteria.</p>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------

export default Squads;
