import {
  createContext,
  ReactNode,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

import { getCurrentAuth, login as loginRequest } from "../api/authApi";
import { clearAuthToken, getAuthToken, setAuthToken } from "./tokenStorage";

type AuthState = {
  loading: boolean;
  authEnabled: boolean;
  authenticated: boolean;
  username: string | null;
};

type AuthContextValue = AuthState & {
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
  refresh: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

type AuthProviderProps = {
  children: ReactNode;
};

export function AuthProvider({ children }: AuthProviderProps) {
  const [state, setState] = useState<AuthState>({
    loading: true,
    authEnabled: false,
    authenticated: false,
    username: null,
  });

  const refresh = useCallback(async () => {
    setState((current) => ({ ...current, loading: true }));
    try {
      const auth = await getCurrentAuth();
      setState({
        loading: false,
        authEnabled: auth.authEnabled,
        authenticated: auth.authenticated,
        username: auth.username,
      });
    } catch {
      setState({
        loading: false,
        authEnabled: true,
        authenticated: false,
        username: null,
      });
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  useEffect(() => {
    const onExpired = () => {
      setState((current) => ({
        ...current,
        loading: false,
        authEnabled: true,
        authenticated: false,
        username: null,
      }));
    };
    window.addEventListener("trading-lab-auth-expired", onExpired);
    return () => window.removeEventListener("trading-lab-auth-expired", onExpired);
  }, []);

  const login = useCallback(
    async (username: string, password: string) => {
      const response = await loginRequest({ username, password });
      setAuthToken(response.accessToken);
      await refresh();
    },
    [refresh],
  );

  const logout = useCallback(() => {
    clearAuthToken();
    setState((current) => ({
      ...current,
      authenticated: !current.authEnabled,
      username: null,
    }));
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      ...state,
      authenticated: state.authEnabled ? state.authenticated : true,
      login,
      logout,
      refresh,
    }),
    [login, logout, refresh, state],
  );

  useEffect(() => {
    if (!getAuthToken() && state.authEnabled && state.authenticated) {
      setState((current) => ({ ...current, authenticated: false, username: null }));
    }
  }, [state.authEnabled, state.authenticated]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const value = useContext(AuthContext);
  if (value === null) {
    throw new Error("useAuth must be used inside AuthProvider.");
  }
  return value;
}
