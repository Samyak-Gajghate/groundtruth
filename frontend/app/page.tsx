import Link from "next/link";

export default function HomePage() {
  return (
    <div className="flex-1 flex flex-col items-center justify-center px-6 text-center">
      <h1 className="text-3xl font-semibold tracking-tight">GroundTruth</h1>
      <p className="text-neutral-400 mt-2 max-w-md">
        Multi-tenant AI assistant grounded in your uploaded documents. Per-tenant
        RAG isolation, streaming chat, admin dashboard, and an embeddable widget.
      </p>
      <div className="mt-6 flex gap-3">
        <Link href="/login" className="rounded bg-sky-500 text-neutral-950 font-medium px-4 py-2 hover:bg-sky-400">Log in</Link>
        <Link href="/signup" className="rounded border border-neutral-700 px-4 py-2 hover:border-neutral-400">Sign up</Link>
      </div>
    </div>
  );
}
