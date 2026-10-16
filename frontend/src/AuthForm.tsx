import { useState } from "react";
import type { FormEvent } from "react";
import { api, messageOf } from "./api";

export default function AuthForm({ onLoggedIn }: { onLoggedIn: () => void }) {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      if (mode === "register") await api.register(email, password);
      await api.login(email, password);
      onLoggedIn();
    } catch (e) {
      setError(messageOf(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit} className="mx-auto mt-24 max-w-sm space-y-4 rounded-xl bg-white p-6 shadow">
      <h1 className="text-2xl font-bold">StudySphere AI</h1>
      <p className="text-sm text-gray-600">{mode === "login" ? "Log in to your account" : "Create an account"}</p>
      <input
        type="email"
        required
        placeholder="Email"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        className="w-full rounded border border-gray-300 p-2"
      />
      <input
        type="password"
        required
        minLength={8}
        placeholder="Password (at least 8 characters)"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        className="w-full rounded border border-gray-300 p-2"
      />
      {error && <p className="text-sm text-red-600">{error}</p>}
      <button
        type="submit"
        disabled={busy}
        className="w-full rounded bg-indigo-600 p-2 font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
      >
        {busy ? "Please wait..." : mode === "login" ? "Log in" : "Register"}
      </button>
      <button
        type="button"
        onClick={() => setMode(mode === "login" ? "register" : "login")}
        className="w-full text-sm text-indigo-600 hover:underline"
      >
        {mode === "login" ? "No account? Register" : "Have an account? Log in"}
      </button>
    </form>
  );
}