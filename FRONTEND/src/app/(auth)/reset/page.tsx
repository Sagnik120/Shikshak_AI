"use client";

import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { api } from "@/core/api";
import { useI18n } from "@/providers/i18n";
import { Button, type ButtonStatus } from "@/components/ui/button";
import { PasswordInput } from "@/components/ui/primitives";
import { Field } from "@/components/ui/field";
import { OtpInput, type OtpHandle } from "@/components/ui/otp-input";
import { AuthHeading, DemoCode, FormAlert, StrengthMeter, errText, passwordOk, pendingOtp, useCooldown, type PendingOtp } from "@/components/auth/auth-kit";

export default function ResetPage() {
  const { t } = useI18n();
  const router = useRouter();
  const [pending, setPending] = useState<PendingOtp | null>(null);
  const [code, setCode] = useState("");
  const [password, setPassword] = useState("");
  const [status, setStatus] = useState<ButtonStatus>("idle");
  const [error, setError] = useState("");
  const [pwError, setPwError] = useState<string | null>(null);
  const otp = useRef<OtpHandle>(null);
  const cooldown = useCooldown(30);

  useEffect(() => {
    const p = pendingOtp.load();
    if (!p || p.purpose !== "reset_password") router.replace("/forgot");
    else setPending(p);
  }, [router]);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!pending) return;
    if (code.length !== 6) { otp.current?.shake(); return; }
    if (!passwordOk(password)) return setPwError(t("err.password"));
    setPwError(null);
    setError("");
    setStatus("loading");
    try {
      await api.resetPassword(pending.email, code, password);
      pendingOtp.clear();
      setStatus("success");
      toast.success(t("auth.resetDone"));
      router.replace("/login");
    } catch (err) {
      setStatus("idle");
      setError(errText(err, t("common.error")));
    }
  };

  const resend = async () => {
    if (!pending) return;
    try {
      const r = await api.forgotPassword(pending.email);
      const next = { ...pending, code: r.dev_otp };
      pendingOtp.save(next);
      setPending(next);
      cooldown.restart();
    } catch (err) {
      setError(errText(err, t("common.error")));
    }
  };

  if (!pending) return null;
  return (
    <>
      <AuthHeading title={t("auth.resetTitle")} sub={t("auth.verifySub", { email: pending.email })} />
      <DemoCode code={pending.code} onFill={() => pending.code && otp.current?.fill(pending.code)} />
      <form onSubmit={submit} className="space-y-5">
        <OtpInput ref={otp} value={code} onChange={setCode} />
        <Field id="pw" label={t("auth.newPassword")} error={pwError}>
          <PasswordInput id="pw" name="password" autoComplete="new-password" value={password} onChange={(e) => setPassword(e.target.value)} aria-invalid={!!pwError} showLabel={t("auth.showPassword")} hideLabel={t("auth.hidePassword")} />
        </Field>
        <StrengthMeter password={password} />
        <FormAlert>{error}</FormAlert>
        <Button type="submit" size="lg" className="w-full" status={status}>{t("auth.resetTitle")}</Button>
      </form>
      <button type="button" onClick={resend} disabled={cooldown.left > 0} className="mt-6 text-sm font-medium text-sky-700 disabled:text-ink-3">
        {cooldown.left > 0 ? t("auth.resendIn", { n: cooldown.left }) : t("auth.resend")}
      </button>
    </>
  );
}
