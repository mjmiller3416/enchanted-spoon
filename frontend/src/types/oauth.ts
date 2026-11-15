// ChatGPT connector (OAuth for the MCP server): consent page and connected apps

/** The authorization request's query parameters, passed through from the consent page URL. */
export interface AuthorizeParams {
  response_type: string | null;
  client_id: string | null;
  redirect_uri: string | null;
  code_challenge: string | null;
  code_challenge_method: string | null;
  state: string | null;
  scope: string | null;
  resource: string | null;
}

/** ok: show consent. redirect: send the browser back with an error. error: show the message only. */
export interface AuthorizeCheckDTO {
  status: "ok" | "redirect" | "error";
  client_name: string | null;
  redirect_to: string | null;
  message: string | null;
}

export interface AuthorizeResultDTO {
  redirect_to: string;
}

export interface ConnectionDTO {
  client_name: string;
  connected_at: string;
}

export interface ConnectionsDTO {
  connections: ConnectionDTO[];
}

export interface DisconnectResultDTO {
  revoked: number;
}
