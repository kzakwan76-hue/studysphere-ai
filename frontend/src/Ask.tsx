import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { api, messageOf } from "./api";
import type { AnswerResponse, SubjectItem } from "./api";

const STATUS_STYLE: Record<string, string> = {
  answered: "bg-green-100 text-green-800",
  passages_only: "bg-blue-100 text-blue-800",
  not_found: "bg-gray-200 text-gray-800",
  unverified: "bg-yellow-100 text-yellow-800",
  unavailable: "bg-yellow-100 text-yellow-800",
};

export default function Ask() {
  const [question, setQuestion] = useState("");
  const [subjects, setSubjects] = useState<SubjectItem[]>([]);
  const [scope, setScope] = useState("");
  const [result, setResult] = useState<AnswerResponse | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api
      .listSubjects()
      .then(setSubjects)
      .catch(() => setSubjects([]));
  }, []);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      setResult(await api.ask(question, scope === "" ? undefined : Number(scope)));
    } catch (e) {
      setResult(null);
      setError(messageOf(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="space-y-4">
      <form onSubmit={submit} className="space-y-2">
        <select
          value={scope}
          onChange={(e) => setScope(e.target.value)}
          className="rounded border border-gray-300 p-2 text-sm"
        >
          <option value="">All my documents</option>
          {subjects.map((subject) => (
            <option key={subject.id} value={subject.id}>
              Subject: {subject.name}
            </option>
          ))}
        </select>
        <div className="flex gap-2">
          <input
            required
            minLength={3}
            maxLength={500}
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="Ask a question about your documents"
            className="flex-1 rounded border border-gray-300 p-2"
          />
          <button
            type="submit"
            disabled={busy}
            className="rounded bg-indigo-600 px-4 font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
          >
            {busy ? "Thinking..." : "Ask"}
          </button>
        </div>
      </form>

      {error && <p className="text-sm text-red-600">{error}</p>}

      {result && (
        <div className="space-y-3">
          <div className="rounded-xl bg-white p-4 shadow">
            <span className={`rounded px-2 py-0.5 text-xs font-medium ${STATUS_STYLE[result.status] ?? ""}`}>
              {result.status}
            </span>
            <p className="mt-2 text-sm text-gray-600">{result.message}</p>
            {/* React escapes this text, so it is safe to show. Never use dangerouslySetInnerHTML for it. */}
            {result.answer && <p className="mt-3 whitespace-pre-wrap">{result.answer}</p>}
            {result.warnings.map((warning) => (
              <p key={warning} className="mt-2 text-sm text-yellow-700">
                Warning: {warning}
              </p>
            ))}
            {result.support !== null && (
              <p className="mt-2 text-xs text-gray-500">Support score: {result.support} (a heuristic, not proof)</p>
            )}
          </div>

          {result.sources.map((source) => (
            <div
              key={source.number}
              className={`rounded-xl bg-white p-4 shadow ${source.cited ? "ring-2 ring-green-400" : ""}`}
            >
              <p className="text-sm font-medium">
                [{source.number}] {source.filename}, page {source.page_number}
                {source.cited && <span className="ml-2 text-green-700">cited</span>}
              </p>
              <p className="mt-1 whitespace-pre-wrap text-sm text-gray-700">{source.text}</p>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}