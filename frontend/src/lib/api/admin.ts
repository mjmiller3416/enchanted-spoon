import type {
  CurrentUserDTO,
  AdminUserListResponse,
  AdminUserDTO,
  AdminGrantProRequest,
  AdminToggleAdminRequest,
  AdminQueryRequest,
  AdminQueryResponse,
  AdminUsageResponse,
} from "@/types/admin";
import { fetchApi, buildQueryString } from "./base";

export const adminApi = {
  // ── Current User ──────────────────────────────────────────────────────────

  getCurrentUser: (token?: string | null): Promise<CurrentUserDTO> =>
    fetchApi<CurrentUserDTO>("/api/users/me", undefined, token),

  // ── User Management ───────────────────────────────────────────────────────

  listUsers: (
    params: { skip?: number; limit?: number } = {},
    token?: string | null,
  ): Promise<AdminUserListResponse> =>
    fetchApi<AdminUserListResponse>(
      `/api/admin/users${buildQueryString(params)}`,
      undefined,
      token,
    ),

  grantPro: (
    userId: number,
    data: AdminGrantProRequest,
    token?: string | null,
  ): Promise<AdminUserDTO> =>
    fetchApi<AdminUserDTO>(
      `/api/admin/users/${userId}/pro`,
      { method: "PATCH", body: JSON.stringify(data) },
      token,
    ),

  revokePro: (userId: number, token?: string | null): Promise<AdminUserDTO> =>
    fetchApi<AdminUserDTO>(
      `/api/admin/users/${userId}/pro`,
      { method: "DELETE" },
      token,
    ),

  toggleAdmin: (
    userId: number,
    data: AdminToggleAdminRequest,
    token?: string | null,
  ): Promise<AdminUserDTO> =>
    fetchApi<AdminUserDTO>(
      `/api/admin/users/${userId}/admin`,
      { method: "PATCH", body: JSON.stringify(data) },
      token,
    ),

  deleteUser: (userId: number, token?: string | null): Promise<void> =>
    fetchApi<void>(
      `/api/admin/users/${userId}`,
      { method: "DELETE" },
      token,
    ),

  // ── Usage Metrics ──────────────────────────────────────────────────────

  getUsage: (
    month?: string,
    token?: string | null,
  ): Promise<AdminUsageResponse> =>
    fetchApi<AdminUsageResponse>(
      `/api/admin/usage${buildQueryString({ month })}`,
      undefined,
      token,
    ),

  // ── Database Query ─────────────────────────────────────────────────────

  executeQuery: (
    data: AdminQueryRequest,
    token?: string | null,
  ): Promise<AdminQueryResponse> =>
    fetchApi<AdminQueryResponse>(
      "/api/admin/query",
      { method: "POST", body: JSON.stringify(data) },
      token,
    ),
};
