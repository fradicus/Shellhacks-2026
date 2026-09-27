import { redirect } from "next/navigation";

// Keep old bookmarks useful after retiring the separate project map.
export default function MapPage() {
  redirect("/time");
}
