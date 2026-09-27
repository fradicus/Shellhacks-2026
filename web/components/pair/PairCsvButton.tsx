"use client";

import { Button } from "@/components/ui";
import type { Brief, Match, Project } from "@/lib/types";
import { pairCsv, pairCsvFilename } from "./pairCsv";

export function PairCsvButton({ match, a, b, brief }: {
  match: Match; a: Project | null; b: Project | null; brief: Brief | null;
}) {
  function download() {
    const url = URL.createObjectURL(new Blob([pairCsv(match, a, b, brief)], { type: "text/csv;charset=utf-8" }));
    const link = document.createElement("a");
    link.href = url;
    link.download = pairCsvFilename(match._id);
    document.body.append(link);
    link.click();
    link.remove();
    // Keep the Blob alive while the browser starts its download.
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  return <Button onClick={download}>Download this pair CSV</Button>;
}
