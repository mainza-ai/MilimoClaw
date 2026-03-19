// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

/**
 * Theme Configuration Component
 *
 * Manages tenant color scheme and typography.
 */

import React, { useState } from "react";

// ---------------------------------------------------------------------------

export interface ThemeConfig {
  primaryColor: string;
  secondaryColor: string;
  accentColor?: string;
  backgroundColor?: string;
  textColor?: string;
  fontFamily?: string;
}

export interface ThemeProps {
  currentTheme: ThemeConfig;
  tenantId: string;
  onThemeChange: (theme: ThemeConfig) => void;
}

const PRESET_COLORS = {
  primary: [
    { name: "Indigo", value: "#4F46E5" },
    { name: "Blue", value: "#3B82F6" },
    { name: "Green", value: "#10B981" },
    { name: "Purple", value: "#8B5CF6" },
    { name: "Red", value: "#EF4444" },
    { name: "Orange", value: "#F97316" },
    { name: "Teal", value: "#14B8A6" },
    { name: "Pink", value: "#EC4899" },
  ],
  secondary: [
    { name: "Emerald", value: "#10B981" },
    { name: "Sky", value: "#0EA5E9" },
    { name: "Amber", value: "#F59E0B" },
    { name: "Rose", value: "#F43F5E" },
    { name: "Violet", value: "#8B5CF6" },
    { name: "Cyan", value: "#06B6D4" },
    { name: "Lime", value: "#84CC16" },
    { name: "Fuchsia", value: "#D946EF" },
  ],
};

const FONT_OPTIONS = [
  { name: "System Default", value: "system-ui, -apple-system, sans-serif" },
  { name: "Inter", value: "'Inter', sans-serif" },
  { name: "Roboto", value: "'Roboto', sans-serif" },
  { name: "Open Sans", value: "'Open Sans', sans-serif" },
  { name: "Lato", value: "'Lato', sans-serif" },
  { name: "Poppins", value: "'Poppins', sans-serif" },
];

// ---------------------------------------------------------------------------

export function Theme({
  currentTheme,
  tenantId,
  onThemeChange,
}: ThemeProps) {
  const [theme, setTheme] = useState<ThemeConfig>(currentTheme);
  const [hasChanges, setHasChanges] = useState(false);

  const updateTheme = (updates: Partial<ThemeConfig>) => {
    setTheme((prev) => ({ ...prev, ...updates }));
    setHasChanges(true);
  };

  const handleSave = () => {
    onThemeChange(theme);
    setHasChanges(false);
  };

  const handleReset = () => {
    setTheme(currentTheme);
    setHasChanges(false);
  };

  return (
    <div className="theme-config">
      <h3>Theme & Colors</h3>

      <div className="theme-section">
        <h4>Primary Color</h4>
        <div className="color-picker">
          <div className="color-presets">
            {PRESET_COLORS.primary.map((color) => (
              <button
                key={color.value}
                className={`color-swatch ${theme.primaryColor === color.value ? "selected" : ""}`}
                style={{ backgroundColor: color.value }}
                onClick={() => updateTheme({ primaryColor: color.value })}
                title={color.name}
              />
            ))}
          </div>
          <div className="color-custom">
            <input
              type="color"
              value={theme.primaryColor}
              onChange={(e) => updateTheme({ primaryColor: e.target.value })}
            />
            <input
              type="text"
              value={theme.primaryColor}
              onChange={(e) => updateTheme({ primaryColor: e.target.value })}
              placeholder="#000000"
            />
          </div>
        </div>
      </div>

      <div className="theme-section">
        <h4>Secondary Color</h4>
        <div className="color-picker">
          <div className="color-presets">
            {PRESET_COLORS.secondary.map((color) => (
              <button
                key={color.value}
                className={`color-swatch ${theme.secondaryColor === color.value ? "selected" : ""}`}
                style={{ backgroundColor: color.value }}
                onClick={() => updateTheme({ secondaryColor: color.value })}
                title={color.name}
              />
            ))}
          </div>
          <div className="color-custom">
            <input
              type="color"
              value={theme.secondaryColor}
              onChange={(e) => updateTheme({ secondaryColor: e.target.value })}
            />
            <input
              type="text"
              value={theme.secondaryColor}
              onChange={(e) => updateTheme({ secondaryColor: e.target.value })}
              placeholder="#000000"
            />
          </div>
        </div>
      </div>

      <div className="theme-section">
        <h4>Font Family</h4>
        <select
          value={theme.fontFamily}
          onChange={(e) => updateTheme({ fontFamily: e.target.value })}
          style={{ fontFamily: theme.fontFamily }}
        >
          {FONT_OPTIONS.map((font) => (
            <option key={font.value} value={font.value} style={{ fontFamily: font.value }}>
              {font.name}
            </option>
          ))}
        </select>
      </div>

      <div className="theme-preview">
        <h4>Preview</h4>
        <div
          className="preview-card"
          style={{
            borderColor: theme.primaryColor,
            fontFamily: theme.fontFamily,
          }}
        >
          <div
            className="preview-header"
            style={{ backgroundColor: theme.primaryColor }}
          >
            Header
          </div>
          <div className="preview-content">
            <p>Content text using the selected font.</p>
            <button
              className="preview-button"
              style={{
                backgroundColor: theme.primaryColor,
                borderColor: theme.secondaryColor,
              }}
            >
              Primary Button
            </button>
            <button
              className="preview-button secondary"
              style={{ backgroundColor: theme.secondaryColor }}
            >
              Secondary Button
            </button>
          </div>
        </div>
      </div>

      <div className="theme-actions">
        {hasChanges && (
          <>
            <button className="btn-secondary" onClick={handleReset}>
              Reset
            </button>
            <button className="btn-primary" onClick={handleSave}>
              Save Theme
            </button>
          </>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------

export default Theme;
