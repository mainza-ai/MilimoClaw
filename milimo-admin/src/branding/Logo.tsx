// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

/**
 * Logo Configuration Component
 *
 * Manages tenant logo upload and display.
 */

import React, { useState, useRef } from "react";

// ---------------------------------------------------------------------------

export interface LogoProps {
  currentLogoUrl: string;
  tenantId: string;
  onLogoChange: (logoUrl: string) => void;
  maxWidth?: number;
  maxHeight?: number;
}

// ---------------------------------------------------------------------------

export function Logo({
  currentLogoUrl,
  tenantId,
  onLogoChange,
  maxWidth = 300,
  maxHeight = 100,
}: LogoProps) {
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setError(null);

    if (!file.type.startsWith("image/")) {
      setError("Please select an image file (PNG, SVG, or JPG)");
      return;
    }

    if (file.size > 5 * 1024 * 1024) {
      setError("Logo file must be smaller than 5MB");
      return;
    }

    const reader = new FileReader();
    reader.onload = (e) => {
      setPreview(e.target?.result as string);
    };
    reader.readAsDataURL(file);
  };

  const handleUpload = async () => {
    if (!preview) return;

    setIsUploading(true);
    setError(null);

    try {
      console.log(`[Logo] Uploading logo for tenant ${tenantId}`);

      await new Promise((resolve) => setTimeout(resolve, 1000));

      onLogoChange(preview);
      setPreview(null);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setIsUploading(false);
    }
  };

  const handleRemove = () => {
    setPreview(null);
    onLogoChange("");
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  return (
    <div className="logo-config">
      <h3>Logo</h3>

      <div className="logo-preview" style={{ maxWidth, maxHeight }}>
        {preview || currentLogoUrl ? (
          <img
            src={preview || currentLogoUrl}
            alt="Tenant Logo"
            className="logo-image"
          />
        ) : (
          <div className="logo-placeholder">
            <span>No logo uploaded</span>
          </div>
        )}
      </div>

      <div className="logo-actions">
        <input
          ref={fileInputRef}
          type="file"
          accept="image/png,image/svg+xml,image/jpeg"
          onChange={handleFileSelect}
          style={{ display: "none" }}
        />
        <button
          className="btn-secondary"
          onClick={() => fileInputRef.current?.click()}
        >
          {currentLogoUrl ? "Change Logo" : "Upload Logo"}
        </button>

        {preview && (
          <>
            <button
              className="btn-primary"
              onClick={handleUpload}
              disabled={isUploading}
            >
              {isUploading ? "Uploading..." : "Save"}
            </button>
            <button className="btn-secondary" onClick={() => setPreview(null)}>
              Cancel
            </button>
          </>
        )}

        {currentLogoUrl && !preview && (
          <button className="btn-danger" onClick={handleRemove}>
            Remove
          </button>
        )}
      </div>

      {error && <div className="error-message">{error}</div>}

      <div className="logo-requirements">
        <p>Requirements:</p>
        <ul>
          <li>Format: PNG, SVG, or JPG</li>
          <li>Max size: 5MB</li>
          <li>Recommended: PNG or SVG for best quality</li>
        </ul>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------

export default Logo;
