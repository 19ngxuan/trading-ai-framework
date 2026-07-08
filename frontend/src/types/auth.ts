export type LoginRequest = {
  username: string;
  password: string;
};

export type LoginResponse = {
  accessToken: string;
  tokenType: "bearer";
  expiresInSeconds: number;
  username: string;
};

export type AuthMeResponse = {
  authEnabled: boolean;
  authenticated: boolean;
  username: string | null;
};
