import type { Metadata } from "next";
import { SetupForm } from "@/components/SetupForm";

export const metadata: Metadata = { title: "Set up a simulation" };

export default function SetupPage() {
  return (<>
    <h1>Set up a simulation</h1>
    <p className="muted">Four short steps. You can change anything later.</p>
    <SetupForm />
  </>);
}
