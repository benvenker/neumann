const apiBase =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8001";

export default function Home() {
  return (
    <main className="max-w-5xl mx-auto px-6 py-16 space-y-10 font-[family-name:var(--font-geist-sans)]">
      <div className="space-y-3">
        <p className="text-xs uppercase tracking-[0.28em] text-slate-500">
          Neumann
        </p>
        <h1 className="text-3xl sm:text-4xl font-semibold text-slate-900">
          Frontend scaffold is ready
        </h1>
        <p className="text-base text-slate-600 leading-relaxed">
          This page is a placeholder for the hybrid search UI. Configure the API
          base URL in <code className="px-1 py-0.5 rounded bg-slate-100 font-mono text-sm">.env.local</code>
          , and ensure the backend CORS allows requests from http://localhost:3000.
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
          <p className="text-xs uppercase font-semibold text-slate-500 mb-2">
            API base
          </p>
          <p className="font-mono text-sm text-slate-900 break-all">{apiBase}</p>
        </div>
        <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
          <p className="text-xs uppercase font-semibold text-slate-500 mb-2">
            Next steps
          </p>
          <ul className="text-sm text-slate-700 space-y-1">
            <li>Implement shared types in src/lib/types.ts (nm-8gm).</li>
            <li>Add dependencies/tooling from plan section 11 (nm-jlj).</li>
          </ul>
        </div>
        <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
          <p className="text-xs uppercase font-semibold text-slate-500 mb-2">
            App router
          </p>
          <p className="text-sm text-slate-700">
            Uses the Next.js 14 App Router with Tailwind. Start the dev server
            via <code className="font-mono">npm run dev</code> in the frontend
            directory.
          </p>
        </div>
      </div>
    </main>
  );
}
