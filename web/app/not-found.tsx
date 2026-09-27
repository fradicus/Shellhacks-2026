import Link from "next/link";
import s from "@/components/brand/notFound.module.css";

export const metadata = { title: "No such page · GridBridge" };

/** 404 in the product's own grammar: two service rings that don't overlap. */
export default function NotFound() {
  return (
    <main className={s.page}>
      <svg className={s.rings} viewBox="0 0 220 110" aria-hidden="true">
        <circle cx="55" cy="55" r="40" stroke="var(--desc)" />
        <circle cx="165" cy="55" r="40" stroke="var(--gpc)" />
        <line x1="95" y1="55" x2="125" y2="55" />
      </svg>
      <p className={s.eyebrow}>404 · no such page</p>
      <h1 className={s.title}>No overlap here.</h1>
      <p className={s.lede}>This address doesn&apos;t match a page in GridBridge. The leads are on the overlap view.</p>
      <div className={s.actions}>
        <Link href="/time" className={s.primary}>
          Go to Overlaps →
        </Link>
        <Link href="/" className={s.secondary}>
          Home
        </Link>
      </div>
    </main>
  );
}
