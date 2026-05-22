import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { getHealth } from "../api";

const STORAGE_KEY = "globeye-key";

export type ApiAuthContextValue = {
  apiKey: string;
  setApiKey: (key: string) => void;
  apiDebug: boolean;
  configLoaded: boolean;
  /** True when the UI must prompt for GLOBEYE_API_KEY before protected API calls. */
  requiresApiKey: boolean;
};

const ApiAuthContext = createContext<ApiAuthContextValue | null>(null);

function readStoredKey(): string {
  try {
    return localStorage.getItem(STORAGE_KEY) ?? "";
  } catch {
    return "";
  }
}

export function ApiAuthProvider({ children }: { children: ReactNode }) {
  const [apiKey, setApiKeyState] = useState(readStoredKey);
  const [apiDebug, setApiDebug] = useState(false);
  const [configLoaded, setConfigLoaded] = useState(false);

  useEffect(() => {
    getHealth()
      .then((h) => setApiDebug(Boolean(h.api_debug)))
      .catch(() => setApiDebug(false))
      .finally(() => setConfigLoaded(true));
  }, []);

  const setApiKey = useCallback((key: string) => {
    setApiKeyState(key);
    try {
      if (key) localStorage.setItem(STORAGE_KEY, key);
      else localStorage.removeItem(STORAGE_KEY);
    } catch {
      /* ignore */
    }
  }, []);

  const value = useMemo(
    () => ({
      apiKey,
      setApiKey,
      apiDebug,
      configLoaded,
      requiresApiKey: configLoaded && !apiDebug,
    }),
    [apiKey, setApiKey, apiDebug, configLoaded],
  );

  return <ApiAuthContext.Provider value={value}>{children}</ApiAuthContext.Provider>;
}

export function useApiAuth(): ApiAuthContextValue {
  const ctx = useContext(ApiAuthContext);
  if (!ctx) {
    throw new Error("useApiAuth must be used within ApiAuthProvider");
  }
  return ctx;
}
