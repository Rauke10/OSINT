import { useApiAuth } from "../context/ApiAuthContext";

/** Shared API key state (localStorage + server debug mode from /api/health). */
export function useApiKey(): [string, (k: string) => void] {
  const { apiKey, setApiKey } = useApiAuth();
  return [apiKey, setApiKey];
}
