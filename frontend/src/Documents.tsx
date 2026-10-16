import { useCallback, useEffect, useState } from "react";
import type { ChangeEvent } from "react";
import { api, messageOf } from "./api";
import type { DocumentItem } from "./api";

export default function Documents() {
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const refresh = useCallback(async () => {
    try {
      setDocuments(await api.listDocuments());
      setError("");
    } catch (e) {
      setError(messageOf(e));
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  async function onFiles(event: ChangeEvent<HTMLInputElement>) {
    const files = Array.from(event.target.files ?? []);
    event.target.value = "";
    if (files.length === 0) return;
    setBusy(true);
    setError("");
    for (const file of files) {
      try {
        await api.uploadDocument(file);
      } catch (e) {
        setError(`${file.name}: ${messageOf(e)}`);
      }
    }
    setBusy(false);
    await refresh();
  }

  async function remove(id: number) {
    if (!window.confirm("Delete this document?")) return;
    try {
      await api.deleteDocument(id);
      await refresh();
    } catch (e) {
      setError(messageOf(e));
    }
  }

  return (
    <section className="space-y-4">
      <label className="block cursor-pointer rounded-xl border-2 border-dashed border-gray-300 bg-white p-6 text-center hover:border-indigo-400">
        <span className="font-medium">{busy ? "Uploading..." : "Click to upload PDF, TXT or MD files"}</span>
        <input type="file" multiple accept=".pdf,.txt,.md" onChange={onFiles} disabled={busy} className="hidden" />
      </label>
      {error && <p className="text-sm text-red-600">{error}</p>}
      {documents.length === 0 ? (
        <p className="text-gray-500">No documents yet.</p>
      ) : (
        <ul className="divide-y rounded-xl bg-white shadow">
          {documents.map((doc) => (
            <li key={doc.id} className="flex items-center justify-between p-3">
              <div>
                <p className="font-medium">{doc.filename}</p>
                <p className="text-xs text-gray-500">
                  {doc.page_count} page(s), {doc.chunk_count} passages, {(doc.size_bytes / 1024).toFixed(1)} KB
                </p>
              </div>
              <button onClick={() => remove(doc.id)} className="text-sm text-red-600 hover:underline">
                Delete
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}