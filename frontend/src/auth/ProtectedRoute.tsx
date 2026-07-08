import { ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";

import { LoadingState } from "../components/ui/LoadingState";
import { useAuth } from "./AuthProvider";

type ProtectedRouteProps = {
  children: ReactNode;
};

export function ProtectedRoute({ children }: ProtectedRouteProps) {
  const auth = useAuth();
  const location = useLocation();

  if (auth.loading) {
    return <LoadingState label="Checking login..." />;
  }

  if (auth.authEnabled && !auth.authenticated) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }

  return <>{children}</>;
}
