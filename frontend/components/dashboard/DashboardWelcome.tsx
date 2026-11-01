'use client';

export function DashboardWelcome() {
  return (
    <div className="mx-auto w-full max-w-2xl px-1 text-center" data-testid="dashboard-welcome">
      <h1 className="text-2xl font-semibold tracking-tight text-zinc-900 sm:text-[1.75rem]">
        How can I help you today?
      </h1>
      <p className="mx-auto mt-4 max-w-xl text-base leading-relaxed text-zinc-600">
        Your intelligent assistant for customs operations, declarations, compliance and
        classification.
      </p>
    </div>
  );
}
