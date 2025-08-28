import axios from "axios";

const API = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
});

// after login we’ll inject the token here:
export function setAuthToken(token) {
  API.defaults.headers.common["Authorization"] = `Bearer ${token}`;
}

// — Authentication —
export const register = (name, email, password) =>
  API.post(
    "/register",
    { name, email, password },
    { headers: { "Content-Type": "application/json" } }
  );

export const login = (username, password) =>
  API.post(
    "/token",
    new URLSearchParams({ username, password }),
    { headers: { "Content-Type": "application/x-www-form-urlencoded" } }
  );

// — Fernet Key —
export const generateFernetKey = () =>
  API.post("/generate_fernet_key");

// — Connections & DB Info —
export const listConnections = () =>
  API.get("/list_connections");

export const addConnection = (connectionInput) =>
  API.post(
    "/new_connection",
    connectionInput,
    { headers: { "Content-Type": "application/json" } }
  );

export const getDbInfo = (dbName) =>
  API.get("/db_info", { params: { db_name: dbName } });

// — Providers & Models —
export const listProviders = () =>
  API.get("/providers");

export const listModels = (provider) =>
  API.get("/models", { params: { provider } });

// — Querying —
export const answerQuery = (params) =>
  API.get("/answer", { params });

// — Saved Queries —
export const saveQuery = (key, question, sql, answer) =>
  API.post(
    "/save_query",
    {}, // empty body
    {
      params: { query_key: key, question, sql_query: sql, answer },
    }
  );

export const listSavedQueries = () =>
  API.get("/list_saved_queries");

export const deleteSavedQuery = (key) =>
  API.delete("/delete_query", { params: { query_key: key } });

// — API Key Management —
export const upsertApiKey = (provider, apiKey) =>
  API.post(
    "/api_keys",
    {},
    {
      params: { provider, api_key: apiKey },
    }
  );

export const deleteApiKey = (provider) =>
  API.delete("/api_keys", { params: { provider } });

export default API;
