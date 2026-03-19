// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

/**
 * Template Manager Component
 *
 * Manages blueprint templates for tenant-specific libraries.
 */

import React, { useState, useCallback } from 'react';

// ---------------------------------------------------------------------------

interface BlueprintTemplate {
  id: string;
  name: string;
  description: string;
  category: 'agency' | 'saas' | 'ecommerce' | 'content' | 'custom';
  roles: string[];
  isActive: boolean;
  isPublic: boolean;
  version: string;
  createdAt: string;
  updatedAt: string;
  usageCount: number;
}

interface TemplateFormData {
  name: string;
  description: string;
  category: BlueprintTemplate['category'];
  roles: string[];
  isPublic: boolean;
}

// ---------------------------------------------------------------------------

const DEFAULT_ROLES = ['content', 'ops', 'analytics', 'finance', 'build'];

const CATEGORY_LABELS: Record<BlueprintTemplate['category'], string> = {
  agency: 'Content Agency',
  saas: 'AI Micro-SaaS',
  ecommerce: 'E-commerce',
  content: 'Content Studio',
  custom: 'Custom',
};

// ---------------------------------------------------------------------------

export const TemplateManager: React.FC = () => {
  const [templates, setTemplates] = useState<BlueprintTemplate[]>([
    {
      id: 'tpl_campus_ai',
      name: 'Campus AI Tool',
      description: 'Student entrepreneurship AI tool template',
      category: 'saas',
      roles: ['build', 'content', 'ops'],
      isActive: true,
      isPublic: true,
      version: '1.0.0',
      createdAt: '2026-03-01',
      updatedAt: '2026-03-15',
      usageCount: 45,
    },
    {
      id: 'tpl_content_agency',
      name: 'Content Agency',
      description: 'Full-service content production agency',
      category: 'agency',
      roles: ['content', 'ops', 'analytics'],
      isActive: true,
      isPublic: true,
      version: '1.2.0',
      createdAt: '2026-02-15',
      updatedAt: '2026-03-10',
      usageCount: 128,
    },
  ]);

  const [selectedTemplate, setSelectedTemplate] = useState<BlueprintTemplate | null>(null);
  const [isCreating, setIsCreating] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterCategory, setFilterCategory] = useState<BlueprintTemplate['category'] | 'all'>('all');

  const handleCreateTemplate = useCallback((data: TemplateFormData) => {
    const newTemplate: BlueprintTemplate = {
      id: `tpl_${Date.now()}`,
      name: data.name,
      description: data.description,
      category: data.category,
      roles: data.roles,
      isActive: true,
      isPublic: data.isPublic,
      version: '1.0.0',
      createdAt: new Date().toISOString().split('T')[0],
      updatedAt: new Date().toISOString().split('T')[0],
      usageCount: 0,
    };

    setTemplates(prev => [...prev, newTemplate]);
    setIsCreating(false);
  }, []);

  const handleToggleActive = useCallback((templateId: string) => {
    setTemplates(prev =>
      prev.map(t =>
        t.id === templateId ? { ...t, isActive: !t.isActive } : t
      )
    );
  }, []);

  const handleDeleteTemplate = useCallback((templateId: string) => {
    if (confirm('Are you sure you want to delete this template?')) {
      setTemplates(prev => prev.filter(t => t.id !== templateId));
      setSelectedTemplate(null);
    }
  }, []);

  const filteredTemplates = templates.filter(template => {
    const matchesSearch = template.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      template.description.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesCategory = filterCategory === 'all' || template.category === filterCategory;
    return matchesSearch && matchesCategory;
  });

  return (
    <div className="template-manager">
      <div className="template-manager__header">
        <h2>Blueprint Templates</h2>
        <button
          className="btn btn-primary"
          onClick={() => setIsCreating(true)}
        >
          + Create Template
        </button>
      </div>

      <div className="template-manager__filters">
        <input
          type="text"
          placeholder="Search templates..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="search-input"
        />
        <select
          value={filterCategory}
          onChange={(e) => setFilterCategory(e.target.value as typeof filterCategory)}
          className="category-filter"
        >
          <option value="all">All Categories</option>
          {Object.entries(CATEGORY_LABELS).map(([value, label]) => (
            <option key={value} value={value}>{label}</option>
          ))}
        </select>
      </div>

      <div className="template-manager__content">
        <div className="template-list">
          {filteredTemplates.length === 0 ? (
            <div className="empty-state">
              <p>No templates found</p>
            </div>
          ) : (
            filteredTemplates.map(template => (
              <div
                key={template.id}
                className={`template-card ${selectedTemplate?.id === template.id ? 'selected' : ''}`}
                onClick={() => setSelectedTemplate(template)}
              >
                <div className="template-card__header">
                  <h3>{template.name}</h3>
                  <span className={`status-badge ${template.isActive ? 'active' : 'inactive'}`}>
                    {template.isActive ? 'Active' : 'Inactive'}
                  </span>
                </div>
                <p className="template-card__description">{template.description}</p>
                <div className="template-card__meta">
                  <span className="category">{CATEGORY_LABELS[template.category]}</span>
                  <span className="usage">{template.usageCount} uses</span>
                </div>
                <div className="template-card__roles">
                  {template.roles.map(role => (
                    <span key={role} className="role-tag">{role}</span>
                  ))}
                </div>
              </div>
            ))
          )}
        </div>

        {selectedTemplate && !isCreating && (
          <div className="template-detail">
            <div className="template-detail__header">
              <h3>{selectedTemplate.name}</h3>
              <div className="template-detail__actions">
                <button
                  className={`btn ${selectedTemplate.isActive ? 'btn-secondary' : 'btn-primary'}`}
                  onClick={() => handleToggleActive(selectedTemplate.id)}
                >
                  {selectedTemplate.isActive ? 'Deactivate' : 'Activate'}
                </button>
                <button
                  className="btn btn-danger"
                  onClick={() => handleDeleteTemplate(selectedTemplate.id)}
                >
                  Delete
                </button>
              </div>
            </div>

            <div className="template-detail__body">
              <div className="detail-section">
                <label>Description</label>
                <p>{selectedTemplate.description}</p>
              </div>

              <div className="detail-section">
                <label>Category</label>
                <p>{CATEGORY_LABELS[selectedTemplate.category]}</p>
              </div>

              <div className="detail-section">
                <label>Required Roles</label>
                <div className="roles-list">
                  {selectedTemplate.roles.map(role => (
                    <span key={role} className="role-badge">{role}</span>
                  ))}
                </div>
              </div>

              <div className="detail-section">
                <label>Visibility</label>
                <p>{selectedTemplate.isPublic ? 'Public (available to all tenants)' : 'Private (this tenant only)'}</p>
              </div>

              <div className="detail-section">
                <label>Version</label>
                <p>{selectedTemplate.version}</p>
              </div>

              <div className="detail-section">
                <label>Statistics</label>
                <div className="stats-grid">
                  <div className="stat">
                    <span className="stat-value">{selectedTemplate.usageCount}</span>
                    <span className="stat-label">Total Uses</span>
                  </div>
                  <div className="stat">
                    <span className="stat-value">{selectedTemplate.createdAt}</span>
                    <span className="stat-label">Created</span>
                  </div>
                  <div className="stat">
                    <span className="stat-value">{selectedTemplate.updatedAt}</span>
                    <span className="stat-label">Last Updated</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {isCreating && (
          <TemplateForm
            onSubmit={handleCreateTemplate}
            onCancel={() => setIsCreating(false)}
          />
        )}
      </div>
    </div>
  );
};

// ---------------------------------------------------------------------------

interface TemplateFormProps {
  onSubmit: (data: TemplateFormData) => void;
  onCancel: () => void;
}

const TemplateForm: React.FC<TemplateFormProps> = ({ onSubmit, onCancel }) => {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [category, setCategory] = useState<BlueprintTemplate['category']>('custom');
  const [selectedRoles, setSelectedRoles] = useState<string[]>([]);
  const [isPublic, setIsPublic] = useState(false);

  const handleRoleToggle = (role: string) => {
    setSelectedRoles(prev =>
      prev.includes(role)
        ? prev.filter(r => r !== role)
        : [...prev, role]
    );
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit({ name, description, category, roles: selectedRoles, isPublic });
  };

  return (
    <div className="template-form">
      <h3>Create New Template</h3>
      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label htmlFor="name">Template Name</label>
          <input
            id="name"
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g., Campus Startup Template"
            required
          />
        </div>

        <div className="form-group">
          <label htmlFor="description">Description</label>
          <textarea
            id="description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Describe the purpose and use case for this template"
            rows={3}
            required
          />
        </div>

        <div className="form-group">
          <label htmlFor="category">Category</label>
          <select
            id="category"
            value={category}
            onChange={(e) => setCategory(e.target.value as BlueprintTemplate['category'])}
          >
            {Object.entries(CATEGORY_LABELS).map(([value, label]) => (
              <option key={value} value={value}>{label}</option>
            ))}
          </select>
        </div>

        <div className="form-group">
          <label>Required Roles</label>
          <div className="roles-checkboxes">
            {DEFAULT_ROLES.map(role => (
              <label key={role} className="checkbox-label">
                <input
                  type="checkbox"
                  checked={selectedRoles.includes(role)}
                  onChange={() => handleRoleToggle(role)}
                />
                <span>{role}</span>
              </label>
            ))}
          </div>
        </div>

        <div className="form-group">
          <label className="checkbox-label">
            <input
              type="checkbox"
              checked={isPublic}
              onChange={(e) => setIsPublic(e.target.checked)}
            />
            <span>Make available to all tenants (Public)</span>
          </label>
        </div>

        <div className="form-actions">
          <button type="button" className="btn btn-secondary" onClick={onCancel}>
            Cancel
          </button>
          <button type="submit" className="btn btn-primary">
            Create Template
          </button>
        </div>
      </form>
    </div>
  );
};

// ---------------------------------------------------------------------------

export default TemplateManager;
