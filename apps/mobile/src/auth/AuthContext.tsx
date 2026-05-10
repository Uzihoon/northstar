import {
  createContext,
  type ReactNode,
  useContext,
  useMemo,
  useState,
} from "react";

const DEFAULT_AUTHENTICATED = false;

type AuthContextValue = {
  isAuthenticated: boolean;
  completeOnboarding: () => void;
  resetLocalAuth: () => void;
};

const AuthContext = createContext<AuthContextValue | null>(null);

type AuthProviderProps = {
  children: ReactNode;
};

export function AuthProvider({ children }: AuthProviderProps) {
  const [isAuthenticated, setIsAuthenticated] = useState(DEFAULT_AUTHENTICATED);

  const value = useMemo<AuthContextValue>(
    () => ({
      isAuthenticated,
      completeOnboarding: () => setIsAuthenticated(true),
      resetLocalAuth: () => setIsAuthenticated(false),
    }),
    [isAuthenticated],
  );

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);

  if (context === null) {
    throw new Error("useAuth must be used inside AuthProvider.");
  }

  return context;
}
