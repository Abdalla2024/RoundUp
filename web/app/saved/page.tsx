import type { Metadata } from "next";
import { SavedView } from "@/components/SavedView";

export const metadata: Metadata = { title: "Saved scenarios" };
export default function SavedPage() { return <SavedView />; }
