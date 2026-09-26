import type {
  SampleDataRemovalResultDTO,
  SampleDataSeedResultDTO,
  SampleDataStatusDTO,
} from "@/types/common";
import { fetchApi } from "./base";

export const sampleDataApi = {
  /**
   * Whether the account still has untouched onboarding starter content
   * @param token - Auth token for authenticated requests
   */
  getStatus: (token: string | null): Promise<SampleDataStatusDTO> =>
    fetchApi<SampleDataStatusDTO>("/api/sample-data", undefined, token),

  /**
   * Add the starter pack (recipes, meals, planner entries, shopping list)
   * @param token - Auth token for authenticated requests
   */
  add: (token: string | null): Promise<SampleDataSeedResultDTO> =>
    fetchApi<SampleDataSeedResultDTO>("/api/sample-data", { method: "POST" }, token),

  /**
   * Remove untouched sample recipes and meals (edited ones are kept)
   * @param token - Auth token for authenticated requests
   */
  remove: (token: string | null): Promise<SampleDataRemovalResultDTO> =>
    fetchApi<SampleDataRemovalResultDTO>("/api/sample-data", { method: "DELETE" }, token),
};
