import type {
  AuthorizeCheckDTO,
  AuthorizeParams,
  AuthorizeResultDTO,
  ConnectionsDTO,
  DisconnectResultDTO,
} from "@/types/oauth";
import { buildQueryString, fetchApi } from "./base";

/** The ChatGPT connector's consent step and the connected-apps list in Settings. */
export const oauthApi = {
  /**
   * Validate an authorization request before showing Allow / Cancel
   * @param params - The consent page's query parameters
   */
  check: (params: AuthorizeParams): Promise<AuthorizeCheckDTO> =>
    fetchApi<AuthorizeCheckDTO>(
      `/api/oauth/authorize/check${buildQueryString({ ...params })}`
    ),

  /**
   * Allow or cancel as the signed-in person; returns where to send the browser
   * @param params - The consent page's query parameters
   * @param decision - "allow" or "deny"
   * @param token - Clerk token (it identifies the person and protects the request from forgery)
   */
  decide: (
    params: AuthorizeParams,
    decision: "allow" | "deny",
    token: string | null
  ): Promise<AuthorizeResultDTO> =>
    fetchApi<AuthorizeResultDTO>(
      "/api/oauth/authorize",
      { method: "POST", body: JSON.stringify({ ...params, decision }) },
      token
    ),

  /**
   * The apps (ChatGPT) connected to this account
   * @param token - Auth token for authenticated requests
   */
  listConnections: (token: string | null): Promise<ConnectionsDTO> =>
    fetchApi<ConnectionsDTO>("/api/oauth/connections", undefined, token),

  /**
   * Disconnect every connected app
   * @param token - Auth token for authenticated requests
   */
  disconnectAll: (token: string | null): Promise<DisconnectResultDTO> =>
    fetchApi<DisconnectResultDTO>("/api/oauth/connections", { method: "DELETE" }, token),
};
