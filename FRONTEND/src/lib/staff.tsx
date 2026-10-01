import { Brain, Gauge, Hand, Radio, Server, Sparkles, Users } from "lucide-react";
import type { MessageKey } from "@/core/i18n";
import type { User } from "@/core/types";

export type StaffTab = "overview" | "live" | "escalations" | "insights" | "quality" | "pipeline" | "learners";

/** The staff portal's sections. Teachers get the teaching views; admins also see the system ones. */
export const STAFF_TABS: Array<{ v: StaffTab; k: MessageKey; icon: React.ReactNode; adminOnly?: boolean }> = [
  { v: "overview", k: "admin.overview", icon: <Gauge className="h-[18px] w-[18px]" /> },
  { v: "live", k: "admin.live", icon: <Radio className="h-[18px] w-[18px]" /> },
  { v: "escalations", k: "admin.escalations", icon: <Hand className="h-[18px] w-[18px]" /> },
  { v: "insights", k: "admin.insights", icon: <Brain className="h-[18px] w-[18px]" /> },
  { v: "learners", k: "admin.learners", icon: <Users className="h-[18px] w-[18px]" /> },
  { v: "quality", k: "admin.quality", icon: <Sparkles className="h-[18px] w-[18px]" />, adminOnly: true },
  { v: "pipeline", k: "admin.pipeline", icon: <Server className="h-[18px] w-[18px]" />, adminOnly: true },
];

export const isStaff = (u?: Pick<User, "role"> | null) => u?.role === "admin" || u?.role === "teacher";
export const tabsFor = (u?: Pick<User, "role"> | null) => STAFF_TABS.filter((x) => !x.adminOnly || u?.role === "admin");

/** Pages that only make sense for a learner; staff are sent to their portal. */
export const LEARNER_ONLY = ["/dashboard", "/new", "/lessons", "/progress", "/learn", "/review", "/report"];
