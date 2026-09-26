import { EmptyState } from "./index";

/** Bootstrap placeholder for a route whose feature hasn't landed yet. */
export function Placeholder({ title, feature }: { title: string; feature: string }) {
  return (
    <main>
      <h1>{title}</h1>
      <EmptyState title="Coming soon">This view is built by feature {feature}.</EmptyState>
    </main>
  );
}
