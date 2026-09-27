/**
 * Minimal PDF 1.4 writer: Letter pages, built-in Helvetica / Helvetica-Bold, text, filled rectangles and lines.
 * No dependency (tech-stack: new packages need a contract PR). Text is reduced to printable ASCII so the standard
 * fonts render it without embedding; the report's wording is written with that in mind.
 */
export type Rgb = [number, number, number];
type Op = string;

export const PAGE = { w: 612, h: 792, margin: 48 };

export function ascii(text: string): string {
  return text
    .replace(/[–—]/g, "-").replace(/[·•]/g, "|").replace(/°/g, " deg").replace(/→/g, "->").replace(/≈/g, "~")
    .replace(/[“”]/g, '"').replace(/[‘’]/g, "'").replace(/…/g, "...").replace(/×/g, "x").replace(/≥/g, ">=").replace(/≤/g, "<=")
    .normalize("NFKD").replace(/[^\x20-\x7e]/g, "");
}
const esc = (t: string) => ascii(t).replace(/\\/g, "\\\\").replace(/\(/g, "\\(").replace(/\)/g, "\\)");
const n = (v: number) => (Math.round(v * 100) / 100).toString();
const rgb = ([r, g, b]: Rgb) => `${n(r / 255)} ${n(g / 255)} ${n(b / 255)}`;

/** Helvetica advance widths (per 1000 em) for ASCII 32..126, from the standard Adobe font metrics. */
const W = [278, 278, 355, 556, 556, 889, 667, 191, 333, 333, 389, 584, 278, 333, 278, 278, 556, 556, 556, 556, 556, 556, 556, 556, 556, 556, 278, 278, 584, 584, 584, 556, 1015, 667, 667, 722, 722, 667, 611, 778, 722, 278, 500, 667, 556, 833, 722, 778, 667, 778, 722, 667, 611, 722, 667, 944, 667, 667, 611, 278, 278, 278, 469, 556, 333, 556, 556, 500, 556, 556, 278, 556, 556, 222, 222, 500, 222, 833, 556, 556, 556, 556, 333, 500, 278, 556, 500, 722, 500, 500, 500, 334, 260, 334, 584];
export function textWidth(text: string, size: number, bold = false): number {
  let w = 0;
  for (const ch of ascii(text)) w += W[ch.charCodeAt(0) - 32] ?? 556;
  return (w * size * (bold ? 1.05 : 1)) / 1000;
}

export class PdfDoc {
  private pages: Op[][] = [[]];
  y = PAGE.h - PAGE.margin;

  private get ops() { return this.pages[this.pages.length - 1]; }
  newPage() { this.pages.push([]); this.y = PAGE.h - PAGE.margin; }
  /** Start a new page when fewer than `needed` points remain above the bottom margin. */
  ensure(needed: number) { if (this.y - needed < PAGE.margin) this.newPage(); }

  text(x: number, y: number, text: string, size = 10, opts: { bold?: boolean; color?: Rgb } = {}) {
    this.ops.push(`BT /${opts.bold ? "F2" : "F1"} ${n(size)} Tf ${rgb(opts.color ?? [20, 24, 32])} rg ${n(x)} ${n(y)} Td (${esc(text)}) Tj ET`);
  }
  rect(x: number, y: number, w: number, h: number, fill: Rgb) { this.ops.push(`${rgb(fill)} rg ${n(x)} ${n(y)} ${n(w)} ${n(h)} re f`); }
  line(x1: number, y1: number, x2: number, y2: number, color: Rgb, width = 0.5, dash = false) {
    this.ops.push(`${rgb(color)} RG ${n(width)} w ${dash ? "[3 2] 0 d" : "[] 0 d"} ${n(x1)} ${n(y1)} m ${n(x2)} ${n(y2)} l S`);
  }

  /** Word-wrapped paragraph at the cursor; advances `y`. */
  paragraph(text: string, size = 10, opts: { bold?: boolean; color?: Rgb; x?: number; width?: number; gap?: number } = {}) {
    const x = opts.x ?? PAGE.margin, width = opts.width ?? PAGE.w - 2 * PAGE.margin, lh = size * 1.35;
    let line = "";
    const flush = () => { this.ensure(lh); this.text(x, this.y - size, line, size, opts); this.y -= lh; line = ""; };
    for (const word of ascii(text).split(/\s+/).filter(Boolean)) {
      const next = line ? `${line} ${word}` : word;
      if (textWidth(next, size, opts.bold) > width && line) { flush(); line = word; } else line = next;
    }
    if (line) flush();
    this.y -= opts.gap ?? 4;
  }

  bytes(): Uint8Array {
    const objects: string[] = [];
    const add = (body: string) => { objects.push(body); return objects.length; };
    const catalog = add(""), pagesId = add("");
    const f1 = add("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>");
    const f2 = add("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>");
    const kids: number[] = [];
    this.pages.forEach((ops, i) => {
      const footer = `BT /F1 8 Tf 0.45 0.45 0.45 rg ${PAGE.margin} 24 Td (${esc(`Page ${i + 1} of ${this.pages.length}`)}) Tj ET`;
      const stream = [...ops, footer].join("\n");
      const content = add(`<< /Length ${stream.length} >>\nstream\n${stream}\nendstream`);
      kids.push(add(`<< /Type /Page /Parent ${pagesId} 0 R /MediaBox [0 0 ${PAGE.w} ${PAGE.h}] /Resources << /Font << /F1 ${f1} 0 R /F2 ${f2} 0 R >> >> /Contents ${content} 0 R >>`));
    });
    objects[catalog - 1] = `<< /Type /Catalog /Pages ${pagesId} 0 R >>`;
    objects[pagesId - 1] = `<< /Type /Pages /Kids [${kids.map((k) => `${k} 0 R`).join(" ")}] /Count ${kids.length} >>`;
    let out = "%PDF-1.4\n";
    const offsets: number[] = [];
    objects.forEach((body, i) => { offsets.push(out.length); out += `${i + 1} 0 obj\n${body}\nendobj\n`; });
    const xref = out.length;
    out += `xref\n0 ${objects.length + 1}\n0000000000 65535 f \n${offsets.map((o) => `${String(o).padStart(10, "0")} 00000 n \n`).join("")}`;
    out += `trailer\n<< /Size ${objects.length + 1} /Root ${catalog} 0 R >>\nstartxref\n${xref}\n%%EOF\n`;
    return new TextEncoder().encode(out); // ASCII only, so string offsets equal byte offsets
  }
}
