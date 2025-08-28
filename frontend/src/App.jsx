import React, { useState, useEffect, useRef } from "react";
import {
  register,
  login,
  setAuthToken,
  listConnections,
  addConnection,
  getDbInfo,
  listProviders,
  listModels,
  answerQuery,
  generateFernetKey,
  upsertApiKey,
  saveQuery,
} from "./api";
import ChatLayout from "./components/ChatLayout";
import Message from "./components/Message";
import ResultsTable from "./components/ResultsTable";

export default function App() {
  const [token, setToken] = useState("");
  const [userInfo, setUserInfo] = useState({ name: "", email: "", password: "" });

  const [fernetKey, setFernetKey] = useState("");
  const [connections, setConnections] = useState([]);
  const [providers, setProviders] = useState([]);
  const [models, setModels] = useState([]);

  const [sessionOpts, setSessionOpts] = useState({
    provider: "",
    apiKeyInput: "",
    model: "",
    connection: "",
    dbInfoName: "",
    dbTypeInput: "",
    connNameInput: "",
  });

  const [messages, setMessages] = useState([]);
  const [prompt, setPrompt] = useState("");
  const [lastResult, setLastResult] = useState(null);   // last /answer payload
  const [lastQuestion, setLastQuestion] = useState(""); // <-- store question for pagination
  const [saveKey, setSaveKey] = useState("");
  const [page, setPage] = useState(1);

  const bottomRef = useRef(null);
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const dedupeBy = (arr, keyFn) =>
    [...new Map((arr || []).map((x, i) => [keyFn(x, i), x])).values()];

  const requireReady = () => {
    const { provider, model, connection } = sessionOpts;
    if (!provider) return "Choose a provider and save its API key first.";
    if (!model) return "Choose a model.";
    if (!connection) return "Choose a connection.";
    return "";
  };

  // ---------- auth ----------
  const handleRegister = async () => {
    await register(userInfo.name, userInfo.email, userInfo.password);
    alert("Registered, now please login!");
  };

  const handleLogin = async () => {
    const res = await login(userInfo.email, userInfo.password);
    const tk = res.data.access_token;
    setToken(tk);
    setAuthToken(tk);

    const conRes = await listConnections();
    const unique = dedupeBy(conRes.data, (c) => c.id ?? c.connection_name);
    setConnections(unique);
    if (unique.length) {
      const first = unique[0].connection_name;
      setSessionOpts((s) => ({ ...s, connection: first, dbInfoName: first }));
    }

    const prov = await listProviders();
    setProviders([...(new Set(prov.data.providers || []))]);
  };

  // ---------- fernet ----------
  const handleGenerateFernet = async () => {
    const res = await generateFernetKey();
    setFernetKey(res.data.fernet_key);
  };

  // ---------- API key ----------
  const handleSaveApiKey = async () => {
    const { provider, apiKeyInput } = sessionOpts;
    if (!provider || !apiKeyInput) {
      return alert("Choose provider and enter API key");
    }
    await upsertApiKey(provider, apiKeyInput);
    alert("API key saved!");
    await loadModels();
  };

  // ---------- connections ----------
  const handleSaveConnection = async () => {
    const { dbTypeInput, connNameInput } = sessionOpts;
    if (!dbTypeInput || !connNameInput) {
      return alert("Select DB type and enter a connection name");
    }
    await addConnection({ db_type: dbTypeInput, connection_name: connNameInput });
    const conRes = await listConnections();
    const unique = dedupeBy(conRes.data, (c) => c.id ?? c.connection_name);
    setConnections(unique);
    setSessionOpts((s) => ({
      ...s,
      connection: s.connection || connNameInput,
      dbInfoName: s.dbInfoName || connNameInput,
    }));
    alert("Connection saved!");
  };

  const handleShowDbInfo = async () => {
    if (!sessionOpts.dbInfoName) return alert("Pick a connection");
    const res = await getDbInfo(sessionOpts.dbInfoName);
    alert(JSON.stringify(res.data, null, 2));
  };

  // ---------- providers & models ----------
  const loadProviders = async () => {
    const res = await listProviders();
    setProviders([...(new Set(res.data.providers || []))]);
  };

  const loadModels = async () => {
    if (!sessionOpts.provider) return;
    const res = await listModels(sessionOpts.provider);
    // handle Together possibly returning list/objects already mapped in backend
    const models = Array.isArray(res.data.models) ? res.data.models : [];
    setModels([...(new Set(models))]);
  };

  // ---------- chat / pagination ----------
  const runQuery = async (questionParam, opts = {}) => {
    const guard = requireReady();
    if (guard) {
      setMessages((m) => [...m, { role: "assistant", text: `Error: ${guard}` }]);
      return;
    }

    // Prefer the provided question; if not given (pagination), reuse lastQuestion
    const q = (questionParam ?? lastQuestion)?.trim();
    if (!q) {
      setMessages((m) => [
        ...m,
        { role: "assistant", text: "Error: No question to run." },
      ]);
      return;
    }

    // Record question for future page requests
    setLastQuestion(q);

    const { provider, model, connection } = sessionOpts;

    if (!opts.silent) {
      setMessages((m) => [...m, { role: "user", text: q }]);
    }

    try {
      const res = await answerQuery({
        question: q,
        provider,
        model,
        connection_name: connection,
        page: opts.page || 1,
      });
      setLastResult(res.data);
      setPage(res.data.page);
      if (!opts.silent) {
        setMessages((m) => [...m, { role: "assistant", text: res.data.answer }]);
      }
    } catch (err) {
      const msg = err.response?.data?.detail || err.message || "Unknown error";
      setMessages((m) => [...m, { role: "assistant", text: `Error: ${msg}` }]);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!prompt) return;
    await runQuery(prompt);
    setPrompt("");
  };

  const goToPage = async (p) => {
    if (!lastResult) return;
    const total = lastResult.total_pages || 1;
    if (p < 1 || p > total) return;
    // Silent run using the remembered question
    await runQuery(undefined, { page: p, silent: true });
  };

  // ---------- save current ----------
  const handleSaveCurrent = async () => {
    if (!lastResult) return alert("No result to save yet.");
    if (!saveKey) return alert("Enter a query key to save.");

    try {
      await saveQuery(
        saveKey,
        lastResult.question || lastQuestion || "",
        lastResult.sql || lastResult.last_sql_query || "",
        lastResult.answer || ""
      );
      alert("Saved to S3!");
    } catch (err) {
      alert("Save failed: " + (err.response?.data?.detail || err.message));
    }
  };

  // ---------- UI ----------
  const footer = !token ? (
    <div className="flex space-x-2">
      <input
        placeholder="Name"
        onChange={(e) => setUserInfo((u) => ({ ...u, name: e.target.value }))}
        className="border p-2"
      />
      <input
        placeholder="Email"
        onChange={(e) => setUserInfo((u) => ({ ...u, email: e.target.value }))}
        className="border p-2"
      />
      <input
        type="password"
        placeholder="Password"
        onChange={(e) => setUserInfo((u) => ({ ...u, password: e.target.value }))}
        className="border p-2"
      />
      <button onClick={handleRegister} className="bg-blue-600 text-white px-4 py-2 rounded">
        Register
      </button>
      <button onClick={handleLogin} className="bg-green-600 text-white px-4 py-2 rounded">
        Login
      </button>
    </div>
  ) : (
    <div className="space-y-4">
      {/* Fernet */}
      <button onClick={handleGenerateFernet} className="bg-purple-600 text-white px-4 py-2 rounded">
        Generate Fernet Key
      </button>
      {fernetKey && (
        <div className="bg-gray-100 p-2 rounded">
          <strong>Your Fernet Key:</strong> <code>{fernetKey}</code>
        </div>
      )}

      {/* API key */}
      <div className="flex space-x-2">
        <select
          onClick={loadProviders}
          onChange={(e) =>
            setSessionOpts((s) => ({ ...s, provider: e.target.value, model: "" }))
          }
          className="border p-2"
          value={sessionOpts.provider}
        >
          <option value="">Choose provider</option>
          {providers.map((p, idx) => (
            <option key={`prov-${idx}-${p}`} value={p}>
              {p}
            </option>
          ))}
        </select>
        <input
          placeholder="API Key"
          onChange={(e) => setSessionOpts((s) => ({ ...s, apiKeyInput: e.target.value }))}
          className="border p-2 flex-1"
        />
        <button onClick={handleSaveApiKey} className="bg-indigo-600 text-white px-4 py-2 rounded">
          Save API Key
        </button>
      </div>

      {/* Connection create */}
      <div className="flex space-x-2">
        <select
          onChange={(e) => setSessionOpts((s) => ({ ...s, dbTypeInput: e.target.value }))}
          className="border p-2"
          value={sessionOpts.dbTypeInput || ""}
        >
          <option value="">DB Type</option>
          <option value="sqlite">sqlite</option>
          <option value="postgresql">postgresql</option>
          <option value="mysql">mysql</option>
        </select>
        <input
          placeholder="Connection Name"
          onChange={(e) => setSessionOpts((s) => ({ ...s, connNameInput: e.target.value }))}
          className="border p-2 flex-1"
        />
        <button onClick={handleSaveConnection} className="bg-yellow-600 text-white px-4 py-2 rounded">
          Save Connection
        </button>
      </div>

      {/* Choose connection */}
      <div className="flex space-x-2">
        <select
          value={sessionOpts.connection}
          onChange={(e) => {
            const v = e.target.value;
            setSessionOpts((s) => ({ ...s, connection: v, dbInfoName: v }));
          }}
          className="border p-2"
        >
          <option value="">Choose connection</option>
          {dedupeBy(connections, (c) => c.id ?? c.connection_name).map((c, idx) => (
            <option
              key={`conn-${(c.id ?? c.connection_name)}-${idx}`}
              value={c.connection_name}
            >
              {c.connection_name}
            </option>
          ))}
        </select>
        <button onClick={handleShowDbInfo} className="bg-teal-600 text-white px-4 py-2 rounded">
          Show DB Info
        </button>
      </div>

      {/* Chat */}
      <form onSubmit={handleSubmit} className="flex space-x-2">
        <select
          onClick={loadModels}
          onChange={(e) => setSessionOpts((s) => ({ ...s, model: e.target.value }))}
          className="border p-2"
          value={sessionOpts.model}
        >
          <option value="">Choose model</option>
          {models.map((m, idx) => (
            <option key={`model-${idx}-${m}`} value={m}>
              {m}
            </option>
          ))}
        </select>
        <input
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="Ask anything…"
          className="border p-2 flex-1 rounded-l"
        />
        <button
          type="submit"
          className="bg-green-500 text-white px-4 py-2 rounded-r"
          disabled={!!requireReady()}
          title={requireReady() || "Send"}
        >
          Send
        </button>
      </form>

      {/* Pretty results */}
      {lastResult && (
        <div className="border rounded p-3 space-y-3 bg-gray-50">
          <div className="grid md:grid-cols-2 gap-3">
            <div>
              <div className="text-sm font-semibold">Question</div>
              <div className="text-sm">{lastResult.question || lastQuestion}</div>
            </div>
            <div>
              <div className="text-sm font-semibold">SQL</div>
              <pre className="text-xs bg-white border rounded p-2 overflow-auto">
{lastResult.sql || lastResult.last_sql_query}
              </pre>
            </div>
          </div>

          <div className="flex items-center justify-between">
            <div className="text-sm">
              <span className="font-semibold">{lastResult.total_records}</span> records • Page{" "}
              <span className="font-semibold">{lastResult.page}</span> of{" "}
              <span className="font-semibold">{lastResult.total_pages}</span>
            </div>
            <div className="space-x-2">
              <button
                type="button"
                className="px-3 py-1 border rounded disabled:opacity-50"
                onClick={() => goToPage(Math.max(1, page - 1))}
                disabled={page <= 1}
              >
                Prev
              </button>
              <button
                type="button"
                className="px-3 py-1 border rounded disabled:opacity-50"
                onClick={() => goToPage(Math.min(lastResult.total_pages || 1, page + 1))}
                disabled={page >= (lastResult.total_pages || 1)}
              >
                Next
              </button>
            </div>
          </div>

          <ResultsTable data={lastResult.preview} />

          <div className="flex items-center space-x-2">
            <input
              placeholder="query_key to save"
              className="border p-2 flex-1"
              value={saveKey}
              onChange={(e) => setSaveKey(e.target.value)}
            />
            <button
              type="button"
              onClick={handleSaveCurrent}
              className="bg-gray-800 text-white px-3 py-2 rounded"
            >
              Save to S3
            </button>
          </div>
        </div>
      )}
    </div>
  );

  return (
    <ChatLayout footer={footer}>
      {messages.map((m, i) => (
        <Message key={`msg-${i}`} role={m.role} text={m.text} />
      ))}
      <div ref={bottomRef} />
    </ChatLayout>
  );
}
