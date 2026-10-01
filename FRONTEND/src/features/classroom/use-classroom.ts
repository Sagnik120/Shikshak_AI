"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState, useSyncExternalStore } from "react";
import { ClassroomController, type ClassroomState } from "./controller";

const noop = () => () => {};
const nil = () => null;

export function useClassroom(lessonId: string) {
  const router = useRouter();
  const [ctl, setCtl] = useState<ClassroomController | null>(null);

  useEffect(() => {
    const c = new ClassroomController(lessonId, (href) => router.replace(href));
    setCtl(c);
    void c.start();
    return () => c.dispose();
  }, [lessonId, router]);

  const state = useSyncExternalStore<ClassroomState | null>(ctl?.subscribe ?? noop, ctl?.getSnapshot ?? nil, nil);
  return { ctl, state };
}
