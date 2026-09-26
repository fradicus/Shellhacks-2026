import Link from "next/link";
import { Table, UtilityBadge } from "@/components/ui";
import type { Project } from "@/lib/types";
import s from "./list.module.css";

/** Every project as a plain table: the accessible fallback when map tiles fail. */
export function ProjectTable({ projects, superseded = 0 }: { projects: Project[]; superseded?: number }) {
  const rows = [...projects].sort((a, b) => a.utility.localeCompare(b.utility) || a.name.localeCompare(b.name));
  return (
    <details className={s.table}>
      <summary>
        {superseded
          ? `Current projects (${projects.length}), as a table · ${superseded} older filing version${superseded === 1 ? "" : "s"} not shown`
          : `All projects (${projects.length}), as a table`}
      </summary>
      {superseded ? (
        <p className={s.note}>
          Each project appears once, from its latest filing. Earlier versions are on{" "}
          <Link href="/changes">Filing changes</Link> and in each pair&apos;s evidence.
        </p>
      ) : null}
      <Table>
        <thead>
          <tr>
            <th scope="col">Utility</th>
            <th scope="col">Project</th>
            <th scope="col">ID</th>
            <th scope="col">In service (as filed)</th>
            <th scope="col">Center (lat, lon)</th>
            <th scope="col">Location</th>
            <th scope="col">Source</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((p) => (
            <tr key={p._id}>
              <td>
                <UtilityBadge utility={p.utility} />
              </td>
              <td>{p.name}</td>
              <td className="mono">{p.native_id}</td>
              <td className="num">
                {p.in_service.raw ?? "Not published"}
                {p.in_service.precision !== "day" ? ` (${p.in_service.precision} precision)` : ""}
              </td>
              <td className="num">
                {p.center ? `${p.center.lat.toFixed(4)}, ${p.center.lon.toFixed(4)}` : "No located endpoint"}
                {p.center?.basis === "one" ? " (one endpoint)" : ""}
              </td>
              <td>{p.location_confidence ?? "Needs review"}</td>
              <td>
                <code>{p.source.source_id}</code>
                {p.source.page ? `, p. ${p.source.page}` : ""}
              </td>
            </tr>
          ))}
        </tbody>
      </Table>
    </details>
  );
}
