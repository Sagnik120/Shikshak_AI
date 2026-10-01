import type { Metadata } from "next";
import { Landing } from "@/components/landing/landing";

export const metadata: Metadata = {
  title: "Shikshak — the teacher who notices",
  description: "An AI teacher that explains on video, pauses to check you understood, and explains again — differently — the moment you didn't. English & हिन्दी.",
};

export default function Page() {
  return <Landing />;
}
