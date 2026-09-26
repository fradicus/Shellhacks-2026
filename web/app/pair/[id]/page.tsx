import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { PairView } from "@/components/pair/PairView";
import { ErrorState } from "@/components/ui";
import { getPair } from "@/lib/data";
import { isUnavailable } from "@/lib/types";

type Props = { params: Promise<{ id: string }> };

/** Page params arrive still percent-encoded (unlike route handlers), so decode exactly once; malformed -> null. */
function pairId(raw: string): string | null {
  try {
    return decodeURIComponent(raw);
  } catch {
    return null;
  }
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  return { title: `Pair ${pairId((await params).id) ?? ""} · GridBridge` };
}

export default async function PairPage({ params }: Props) {
  const id = pairId((await params).id);
  if (!id) notFound();
  const detail = await getPair(id);
  if (isUnavailable(detail)) {
    return (
      <main>
        <h1>Pair</h1>
        <ErrorState />
      </main>
    );
  }
  if (!detail) notFound();
  return <PairView detail={detail} />;
}
