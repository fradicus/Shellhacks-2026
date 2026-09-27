import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { PairView } from "@/components/pair/PairView";
import { ErrorState } from "@/components/ui";
import { getPair } from "@/lib/data";
import { isUnavailable } from "@/lib/types";

type Props = { params: Promise<{ id: string }> };

/** Next hands pages a partly decoded segment (in testing `%25` arrived decoded but `%3A` didn't), so neither "decode"
 * nor "don't" is right for every id. Decode only well-formed `%XX` runs; a literal `%zz` survives. */
function pairId(raw: string): string {
  return raw.replace(/(?:%[0-9A-Fa-f]{2})+/g, (run) => {
    try {
      return decodeURIComponent(run);
    } catch {
      return run;
    }
  });
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  return { title: `Pair ${pairId((await params).id)} · Common Ground` };
}

export default async function PairPage({ params }: Props) {
  const id = pairId((await params).id);
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
