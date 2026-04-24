"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

type ErrorRow = {
  ts: string;
  request_id: string;
  method: string | null;
  path: string;
  query: string | null;
  error_class: string;
  message: string | null;
};

export default function AdminErrorsPage() {
  const [token, setToken] = useState("");
  const [rows, setRows] = useState<ErrorRow[]>([]);
  const [total, setTotal] = useState(0);
  const [err, setErr] = useState<string>("");

  async function load() {
    setErr("");
    const res = await fetch("/api/admin/errors?limit=100&window_hours=24", {
      headers: { "X-Admin-Token": token },
    });
    if (!res.ok) { setErr(`HTTP ${res.status}`); return; }
    const body = await res.json();
    setRows(body.rows);
    setTotal(body.total);
  }

  useEffect(() => {
    const stored = localStorage.getItem("admin-token");
    if (stored) setToken(stored);
  }, []);

  return (
    <main className="mx-auto max-w-6xl px-6 py-12 space-y-6">
      <Link href="/" className="btn-ghost text-sm">← Back</Link>
      <h1 className="headline-section">Errors (24h)</h1>
      <div className="card space-y-3">
        <label className="block">
          <span className="label">Admin token</span>
          <input
            type="password"
            value={token}
            onChange={(e) => { setToken(e.target.value); localStorage.setItem("admin-token", e.target.value); }}
            className="w-full rounded border border-border bg-raised px-3 py-2 font-mono text-sm"
          />
        </label>
        <button onClick={load} className="btn-primary text-xs">Load</button>
        {err && <p className="text-error text-sm">{err}</p>}
      </div>
      {total > 0 && (
        <>
          <p className="font-mono text-xs text-muted">{total} errors in the last 24h · showing latest {rows.length}</p>
          <section className="card p-0 overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="text-[10px] uppercase tracking-wide text-muted">
                <tr className="border-b border-border">
                  <th className="px-3 py-2 text-left">Time</th>
                  <th className="px-3 py-2 text-left">Path</th>
                  <th className="px-3 py-2 text-left">Error</th>
                  <th className="px-3 py-2 text-left">Message</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r) => (
                  <tr key={r.request_id} className="border-t border-border-muted">
                    <td className="px-3 py-2 font-mono text-xs text-muted">{r.ts.slice(0, 19).replace("T", " ")}</td>
                    <td className="px-3 py-2 font-mono text-xs">{r.method} {r.path}</td>
                    <td className="px-3 py-2 font-mono text-error text-xs">{r.error_class}</td>
                    <td className="px-3 py-2 text-xs text-secondary truncate max-w-md">{r.message}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        </>
      )}
    </main>
  );
}
