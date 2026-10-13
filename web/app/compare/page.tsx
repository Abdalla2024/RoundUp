import type { Metadata } from "next";
import { CompareView } from "@/components/CompareView";

export const metadata: Metadata = { title: "Compare two ways of investing" };
export default function ComparePage() { return <CompareView />; }
