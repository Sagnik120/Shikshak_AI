"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import { AnimatePresence } from "motion/react";
import { api } from "@/core/api";
import { useAuth } from "@/providers/auth";
import { useI18n } from "@/providers/i18n";
import { Button, type ButtonStatus } from "@/components/ui/button";
import { OtpInput, type OtpHandle } from "@/components/ui/otp-input";
import { AuthHeading, DemoCode, FormAlert, errText, pendingOtp, useCooldown, type PendingOtp } from "@/components/auth/auth-kit";
import { NamasteOverlay } from "@/components/auth/namaste";

export default function VerifyPage() {
  const { t } = useI18n();
  const { signIn } = useAuth();
  const router = useRouter();
  const [pending, setPending] = useState<PendingOtp | null>(null);
  const [code, setCode] = useState("");
  const [status, setStatus] = useState<ButtonStatus>("idle");
  const [error, setError] = useState("");
  const [done, setDone] = useState(false);
  const [dest, setDest] = useState("/dashboard");
  const otp = useRef<OtpHandle>(null);
  const cooldown = useCooldown(30);

  useEffect(() => {
    const p = pendingOtp.load();
    if (!p || p.purpose !== "verify_email") router.replace(p?.staff ? "/staff/signup" : "/signup");
    else setPending(p);
  }, [router]);

  const verify = async (value = code) => {
    if (!pending || value.length !== 6 || status === "loading") return;
    setError("");
    setStatus("loading");
    try {
      const tok = await api.verifyEmail(pending.email, value);
      signIn(tok);
      setDest(tok.user.role === "admin" || tok.user.role === "teacher" ? "/admin" : "/dashboard");
      pendingOtp.clear();
      setStatus("success");
      setDone(true);
    } catch (err) {
      setStatus("idle");
      setError(errText(err, t("common.error")));
      otp.current?.shake();
    }
  };

  const resend = async () => {
    if (!pending) return;
    try {
      const r = await api.resendOtp(pending.email, "verify_email");
      const next = { ...pending, code: r.dev_otp };
      pendingOtp.save(next);
      setPending(next);
      cooldown.restart();
      otp.current?.clear();
    } catch (err) {
      setError(errText(err, t("common.error")));
    }
  };

  const finish = useCallback(() => router.replace(dest), [router, dest]);
  if (!pending) return null;

  return (
    <>
      <AuthHeading title={t("auth.verifyTitle")} sub={t("auth.verifySub", { email: pending.email })} />
      <DemoCode code={pending.code} onFill={() => pending.code && otp.current?.fill(pending.code)} />
      <form onSubmit={(e) => { e.preventDefault(); void verify(); }} className="space-y-5">
        <OtpInput ref={otp} value={code} onChange={setCode} onComplete={(v) => void verify(v)} disabled={status === "loading" || done} />
        <FormAlert>{error}</FormAlert>
        <Button type="submit" size="lg" className="w-full" status={status} loadingLabel={t("auth.verifying")} disabled={code.length !== 6}>{t("auth.verify")}</Button>
      </form>
      <div className="mt-6 flex items-center justify-between text-sm">
        <Link href={pending.staff ? "/staff/signup" : "/signup"} className="text-ink-3 hover:text-ink">{t("common.back")}</Link>
        <button type="button" onClick={resend} disabled={cooldown.left > 0} className="font-medium text-sky-700 disabled:text-ink-3">
          {cooldown.left > 0 ? t("auth.resendIn", { n: cooldown.left }) : t("auth.resend")}
        </button>
      </div>
      <AnimatePresence>{done && <NamasteOverlay onDone={finish} />}</AnimatePresence>
    </>
  );
}
