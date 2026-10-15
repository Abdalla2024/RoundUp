import type { Metadata } from "next";
import { Hero } from "@/components/Hero";
import { SetupForm } from "@/components/SetupForm";

export const metadata: Metadata = { title: "Set up a simulation" };

export default function SetupPage() {
  return (<>
    <Hero />
    <SetupForm />
  </>);
}
