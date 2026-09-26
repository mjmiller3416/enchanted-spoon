import type {
  ImportPreviewDTO,
  ImportResultDTO,
  DuplicateResolutionDTO,
  ExportFilterDTO,
  FullBackup,
  RestorePreview,
  RestoreResult,
} from "@/types/common";
import { API_BASE, buildQueryString, toApiError } from "./base";

export const dataManagementApi = {
  /**
   * Upload xlsx file and get import preview
   * @param file - The xlsx file to import
   * @param token - Optional auth token for authenticated requests
   * @returns Preview with duplicate info and validation errors
   */
  previewImport: async (file: File, token?: string | null): Promise<ImportPreviewDTO> => {
    const formData = new FormData();
    formData.append("file", file);

    const headers: Record<string, string> = {};
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    const response = await fetch(`${API_BASE}/api/data-management/import/preview`, {
      method: "POST",
      body: formData,
      headers,
    });

    if (!response.ok) {
      throw await toApiError(response, "Failed to preview import");
    }

    return response.json();
  },

  /**
   * Execute import with duplicate resolutions
   * @param file - The xlsx file to import
   * @param resolutions - How to handle each duplicate
   * @param token - Optional auth token for authenticated requests
   * @returns Result with counts and errors
   */
  executeImport: async (
    file: File,
    resolutions: DuplicateResolutionDTO[],
    token?: string | null
  ): Promise<ImportResultDTO> => {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("resolutions", JSON.stringify(resolutions));

    const headers: Record<string, string> = {};
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    const response = await fetch(`${API_BASE}/api/data-management/import/execute`, {
      method: "POST",
      body: formData,
      headers,
    });

    if (!response.ok) {
      throw await toApiError(response, "Failed to execute import");
    }

    return response.json();
  },

  /**
   * Export recipes to xlsx file
   * @param filters - Optional filters for which recipes to export
   * @param token - Optional auth token for authenticated requests
   * @returns Blob of the xlsx file
   */
  exportRecipes: async (filters?: ExportFilterDTO, token?: string | null): Promise<Blob> => {
    const query = filters ? buildQueryString(filters as Record<string, unknown>) : "";

    const headers: Record<string, string> = {};
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    const response = await fetch(`${API_BASE}/api/data-management/export${query}`, { headers });

    if (!response.ok) {
      throw await toApiError(response, "Failed to export recipes");
    }

    return response.blob();
  },

  /**
   * Download xlsx template for import
   * @param token - Optional auth token for authenticated requests
   * @returns Blob of the template file
   */
  downloadTemplate: async (token?: string | null): Promise<Blob> => {
    const headers: Record<string, string> = {};
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    const response = await fetch(`${API_BASE}/api/data-management/template`, { headers });

    if (!response.ok) {
      throw await toApiError(response, "Failed to download template");
    }

    return response.blob();
  },

  /**
   * Delete all data from the database
   * @param token - Optional auth token for authenticated requests
   * @returns Object with success status and counts of deleted records
   */
  clearAllData: async (token?: string | null): Promise<{ success: boolean; deleted_counts: Record<string, number> }> => {
    const headers: Record<string, string> = {};
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    const response = await fetch(`${API_BASE}/api/data-management/clear-all`, {
      method: "DELETE",
      headers,
    });

    if (!response.ok) {
      throw await toApiError(response, "Failed to clear data");
    }

    return response.json();
  },

  /**
   * Export full backup including all database data
   * @param token - Optional auth token for authenticated requests
   * @returns FullBackup object (frontend adds settings before download)
   */
  exportFullBackup: async (token?: string | null): Promise<FullBackup> => {
    const headers: Record<string, string> = {};
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    const response = await fetch(`${API_BASE}/api/data-management/backup/full`, { headers });

    if (!response.ok) {
      throw await toApiError(response, "Failed to export backup");
    }

    return response.json();
  },

  /**
   * Preview restore from backup file
   * @param file - The JSON backup file
   * @param token - Optional auth token for authenticated requests
   * @returns RestorePreview with counts and warnings
   */
  previewRestore: async (file: File, token?: string | null): Promise<RestorePreview> => {
    const formData = new FormData();
    formData.append("file", file);

    const headers: Record<string, string> = {};
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    const response = await fetch(`${API_BASE}/api/data-management/restore/preview`, {
      method: "POST",
      body: formData,
      headers,
    });

    if (!response.ok) {
      throw await toApiError(response, "Failed to preview restore");
    }

    return response.json();
  },

  /**
   * Execute restore from backup file
   * @param file - The JSON backup file
   * @param clearExisting - Whether to clear existing data first (default true)
   * @param token - Optional auth token for authenticated requests
   * @returns RestoreResult with counts, errors, and settings to restore
   */
  executeRestore: async (
    file: File,
    clearExisting: boolean = true,
    token?: string | null
  ): Promise<RestoreResult> => {
    const formData = new FormData();
    formData.append("file", file);

    const headers: Record<string, string> = {};
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    const response = await fetch(
      `${API_BASE}/api/data-management/restore/execute?clear_existing=${clearExisting}`,
      {
        method: "POST",
        body: formData,
        headers,
      }
    );

    if (!response.ok) {
      throw await toApiError(response, "Failed to execute restore");
    }

    return response.json();
  },
};
