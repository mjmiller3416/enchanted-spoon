export interface HouseholdMember {
  user_id: number;
  name: string | null;
  email: string;
  role: "owner" | "member" | string;
  joined_at: string;
}

export interface HouseholdInvite {
  id: number;
  code: string;
  email: string | null;
  expires_at: string;
  created_at: string;
}

export interface Household {
  id: number;
  name: string;
  role: "owner" | "member" | string;
  owner_user_id: number;
  pro_covers_members: boolean;
  members: HouseholdMember[];
  invites: HouseholdInvite[];
}

export interface HouseholdState {
  household: Household | null;
}
