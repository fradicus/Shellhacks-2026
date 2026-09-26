import { SearchBox } from "@/components/search/SearchBox";

export const metadata = { title: "Search — GridBridge" };
export const dynamic = "force-dynamic";

export default function SearchPage() {
  return (
    <main>
      <h1>Semantic search</h1>
      <p>
        Ask in plain language — “projects crossing the Savannah River”, “115 kV rebuilds in service before 2029” — or
        paste a pair id (<code>DESC:…__GPC:…</code>) to see its most similar stored records. Vectors are Gemini
        embeddings of the stored corpus; the exact text, model id and dimensions are stored with every record.
      </p>
      <SearchBox />
    </main>
  );
}
