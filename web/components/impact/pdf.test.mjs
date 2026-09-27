import assert from "node:assert/strict";
import { test } from "node:test";
import { ascii, PdfDoc, textWidth } from "./pdf.ts";

test("PDF output is structurally valid: header, xref offsets point at each object, trailer and EOF", () => {
  const doc = new PdfDoc();
  doc.paragraph("Site weather report – 10 years · 55°F (test)", 14, { bold: true });
  doc.rect(48, 600, 100, 20, [134, 229, 207]);
  doc.line(48, 590, 300, 590, [0, 0, 0], 1, true);
  for (let i = 0; i < 80; i++) doc.paragraph(`Line ${i} with enough words to wrap across the page width when repeated repeated repeated repeated`);
  const text = new TextDecoder().decode(doc.bytes());
  assert.ok(text.startsWith("%PDF-1.4\n"));
  assert.ok(text.trimEnd().endsWith("%%EOF"));
  const xref = Number(text.match(/startxref\n(\d+)\n/)[1]);
  assert.equal(text.slice(xref, xref + 4), "xref");
  const entries = [...text.slice(xref).matchAll(/^(\d{10}) 00000 n $/gm)].map((m) => Number(m[1]));
  entries.forEach((offset, i) => assert.equal(text.slice(offset, offset + `${i + 1} 0 obj`.length), `${i + 1} 0 obj`));
  const pages = Number(text.match(/\/Count (\d+)/)[1]);
  assert.ok(pages >= 2, "long content paginates");
  assert.match(text, /Page 1 of \d+/);
  for (const m of text.matchAll(/<< \/Length (\d+) >>\nstream\n/g)) {
    const start = m.index + m[0].length;
    assert.equal(text.slice(start + Number(m[1]), start + Number(m[1]) + 10), "\nendstream");
  }
});

test("text is reduced to ASCII with readable substitutions and parentheses escaped", () => {
  assert.equal(ascii("Jun – Jul · 28°F → ≈3 “days”"), 'Jun - Jul | 28 degF -> ~3 "days"');
  const doc = new PdfDoc();
  doc.text(10, 10, "a (b) \\ c");
  assert.match(new TextDecoder().decode(doc.bytes()), /\(a \\\(b\\\) \\\\ c\) Tj/);
  assert.ok(textWidth("WWW", 10) > textWidth("iii", 10));
});
