import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { PairView } from "@/components/pair/PairView";
import { ErrorState } from "@/components/ui";
import { getPair } from "@/lib/data";
import { isUnavailable } from "@/lib/types";

type Props = { params: Promise<{ id: string }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  return { title: `Pair ${decodeURIComponent((await params).id)} · GridBridge` };
}

export default async function PairPage({ params }: Props) {
  const id = decodeURIComponent((await params).id);
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
