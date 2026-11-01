import type { Household, HouseholdInvite, HouseholdState } from "@/types/household";
import { fetchApi } from "./base";

export const householdApi = {
  get: (token?: string | null): Promise<HouseholdState> =>
    fetchApi<HouseholdState>("/api/household", undefined, token),

  create: (name: string, token?: string | null): Promise<Household> =>
    fetchApi<Household>(
      "/api/household",
      { method: "POST", body: JSON.stringify({ name }) },
      token,
    ),

  rename: (name: string, token?: string | null): Promise<Household> =>
    fetchApi<Household>(
      "/api/household",
      { method: "PATCH", body: JSON.stringify({ name }) },
      token,
    ),

  dissolve: (token?: string | null): Promise<void> =>
    fetchApi<void>("/api/household", { method: "DELETE" }, token),

  createInvite: (email: string | null, token?: string | null): Promise<HouseholdInvite> =>
    fetchApi<HouseholdInvite>(
      "/api/household/invites",
      { method: "POST", body: JSON.stringify({ email }) },
      token,
    ),

  revokeInvite: (inviteId: number, token?: string | null): Promise<void> =>
    fetchApi<void>(`/api/household/invites/${inviteId}`, { method: "DELETE" }, token),

  join: (code: string, token?: string | null): Promise<Household> =>
    fetchApi<Household>(
      "/api/household/join",
      { method: "POST", body: JSON.stringify({ code }) },
      token,
    ),

  leave: (token?: string | null): Promise<void> =>
    fetchApi<void>("/api/household/leave", { method: "POST" }, token),

  removeMember: (userId: number, token?: string | null): Promise<void> =>
    fetchApi<void>(`/api/household/members/${userId}`, { method: "DELETE" }, token),

  transfer: (userId: number, token?: string | null): Promise<Household> =>
    fetchApi<Household>(
      "/api/household/transfer",
      { method: "POST", body: JSON.stringify({ user_id: userId }) },
      token,
    ),

  shareRecipe: (recipeId: number, token?: string | null): Promise<void> =>
    fetchApi<void>(`/api/household/recipes/${recipeId}/share`, { method: "POST" }, token),

  unshareRecipe: (recipeId: number, token?: string | null): Promise<void> =>
    fetchApi<void>(`/api/household/recipes/${recipeId}/share`, { method: "DELETE" }, token),
};
