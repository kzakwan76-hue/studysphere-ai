import { useEffect, useState } from "react";
import { getToken, setToken } from "./api";
import AuthForm from "./AuthForm";
import Dashboard from "./Dashboard";
import Ask from "./Ask";

export default function App() {
  const [loggedIn, setLoggedIn] = useState(() => getToken() !== null);
  const [tab, setTab] = useState<"dashboard" | "ask">("dashboard");

  useEffect(() => {
    const onExpired = () => setLoggedIn(false);
    window.addEventListener("auth-expired", onExpired);
    return () => window.removeEventListener("auth-expired", onExpired);
  }, []);

  function logout() {
    setToken(null);
    setLoggedIn(false);
  }

  return (
    <div className="min-h-screen bg-gray-50 text-gray-900">
      {!loggedIn ? (
        <AuthForm onLoggedIn={() => setLoggedIn(true)} />
      ) : (
        <div className="mx-auto max-w-3xl space-y-6 p-6">
          <header className="flex items-center justify-between">
            <h1 className="text-2xl font-bold">StudySphere AI</h1>
            <button onClick={logout} className="text-sm text-gray-600 hover:underline">
              Log out
            </button>
          </header>
          <nav className="flex gap-2">
            {(["dashboard", "ask"] as const).map((name) => (
              <button
                key={name}
                onClick={() => setTab(name)}
                className={`rounded px-4 py-2 font-medium capitalize ${
                  tab === name ? "bg-indigo-600 text-white" : "bg-white text-gray-700 hover:bg-gray-100"
                }`}
              >
                {name}
              </button>
            ))}
          </nav>
          {tab === "dashboard" ? <Dashboard /> : <Ask />}
        </div>
      )}
    </div>
  );
}