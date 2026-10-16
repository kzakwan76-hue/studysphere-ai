import { useCallback, useEffect, useState } from "react";
import type { ChangeEvent, FormEvent } from "react";
import { api, messageOf } from "./api";
import type { DashboardData, DocumentSummary } from "./api";

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-xl bg-white p-4 text-center shadow">
      <p className="text-2xl font-bold">{value}</p>
      <p className="text-sm text-gray-600">{label}</p>
    </div>
  );
}

export default function Dashboard() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [newSubject, setNewSubject] = useState("");

  const refresh = useCallback(async () => {
    try {
      setData(await api.dashboard());
    } catch (e) {
      setError(messageOf(e));
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  // Runs one action, shows its error (if any), then reloads the numbers.
  async function run(action: () => Promise<unknown>) {
    setError("");
    try {
      await action();
    } catch (e) {
      setError(messageOf(e));
    }
    await refresh();
  }

  async function addSubject(event: FormEvent) {
    event.preventDefault();
    const name = newSubject.trim();
    if (!name) return;
    await run(async () => {
      await api.createSubject(name);
      setNewSubject("");
    });
  }

  async function onFiles(event: ChangeEvent<HTMLInputElement>) {
    const files = Array.from(event.target.files ?? []);
    event.target.value = "";
    if (files.length === 0) return;
    setBusy(true);
    setError("");
    const problems: string[] = [];
    for (const file of files) {
      try {
        await api.uploadDocument(file);
      } catch (e) {
        problems.push(`${file.name}: ${messageOf(e)}`);
      }
    }
    setBusy(false);
    await refresh();
    if (problems.length > 0) setError(problems.join(" | "));
  }

  async function changeSubject(doc: DocumentSummary, value: string) {
    await run(async () => {
      if (value === "") {
        if (doc.subject_id !== null) await api.unassignDocument(doc.subject_id, doc.id);
      } else {
        await api.assignDocument(Number(value), doc.id);
      }
    });
  }

  async function removeDocument(id: number) {
    if (!window.confirm("Delete this document?")) return;
    await run(() => api.deleteDocument(id));
  }

  async function removeSubject(id: number) {
    if (!window.confirm("Delete this subject? Its documents are kept.")) return;
    await run(() => api.deleteSubject(id));
  }

  if (!data) return <p className="text-gray-500">{error || "Loading..."}</p>;

  return (
    <section className="space-y-6">
      <div className="grid grid-cols-3 gap-3">
        <Stat label="Documents" value={data.document_count} />
        <Stat label="Passages" value={data.chunk_count} />
        <Stat label="Subjects" value={data.subjects.length} />
      </div>

      {error && <p className="text-sm text-red-600">{error}</p>}

      <div className="space-y-3">
        <h2 className="text-lg font-semibold">Subjects</h2>
        <form onSubmit={addSubject} className="flex gap-2">
          <input
            value={newSubject}
            onChange={(e) => setNewSubject(e.target.value)}
            maxLength={80}
            placeholder="New subject, for example Biology"
            className="flex-1 rounded border border-gray-300 p-2"
          />
          <button type="submit" className="rounded bg-indigo-600 px-4 font-medium text-white hover:bg-indigo-700">
            Add
          </button>
        </form>
        {data.subjects.length === 0 ? (
          <p className="text-gray-500">No subjects yet. Create one, then put documents in it.</p>
        ) : (
          <ul className="grid gap-3 sm:grid-cols-2">
            {data.subjects.map((subject) => (
              <li key={subject.id} className="flex items-start justify-between rounded-xl bg-white p-4 shadow">
                <div>
                  <p className="font-medium">{subject.name}</p>
                  <p className="text-xs text-gray-500">
                    {subject.document_count} document(s), {subject.chunk_count} passages
                  </p>
                </div>
                <button onClick={() => removeSubject(subject.id)} className="text-sm text-red-600 hover:underline">
                  Delete
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="space-y-3">
        <h2 className="text-lg font-semibold">Documents</h2>
        <label className="block cursor-pointer rounded-xl border-2 border-dashed border-gray-300 bg-white p-6 text-center hover:border-indigo-400">
          <span className="font-medium">{busy ? "Uploading..." : "Click to upload PDF, TXT or MD files"}</span>
          <input type="file" multiple accept=".pdf,.txt,.md" onChange={onFiles} disabled={busy} className="hidden" />
        </label>
        {data.documents.length === 0 ? (
          <p className="text-gray-500">No documents yet.</p>
        ) : (
          <ul className="divide-y rounded-xl bg-white shadow">
            {data.documents.map((doc) => (
              <li key={doc.id} className="flex flex-wrap items-center justify-between gap-2 p-3">
                <div>
                  <p className="font-medium">{doc.filename}</p>
                  <p className="text-xs text-gray-500">
                    {doc.page_count} page(s), {doc.chunk_count} passages, {(doc.size_bytes / 1024).toFixed(1)} KB
                  </p>
                </div>
                <div className="flex items-center gap-3">
                  <select
                    value={doc.subject_id ?? ""}
                    onChange={(e) => void changeSubject(doc, e.target.value)}
                    className="rounded border border-gray-300 p-1 text-sm"
                  >
                    <option value="">No subject</option>
                    {data.subjects.map((subject) => (
                      <option key={subject.id} value={subject.id}>
                        {subject.name}
                      </option>
                    ))}
                  </select>
                  <button onClick={() => removeDocument(doc.id)} className="text-sm text-red-600 hover:underline">
                    Delete
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  );
}