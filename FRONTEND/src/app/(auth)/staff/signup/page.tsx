"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { ShieldCheck } from "lucide-react";
import { api } from "@/core/api";
import { useI18n } from "@/providers/i18n";
import { Button, type ButtonStatus } from "@/components/ui/button";
import { Input, PasswordInput, Tabs } from "@/components/ui/primitives";
import { EMAIL_RE, Field, formValues } from "@/components/ui/field";
import { AuthHeading, FormAlert, StrengthMeter, errText, passwordOk, pendingOtp } from "@/components/auth/auth-kit";

export default function StaffSignupPage() {
  const { t, lang } = useI18n();
  const router = useRouter();
  const [password, setPassword] = useState("");
  const [errors, setErrors] = useState<Partial<Record<"name" | "email" | "password" | "code", string>>>({});
  const [role, setRole] = useState<"admin" | "teacher">("admin");
  const [status, setStatus] = useState<ButtonStatus>("idle");
  const [error, setError] = useState("");
  const submit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const f = formValues(e.currentTarget);
    const next: typeof errors = {};
    if ((f.full_name ?? "").trim().length < 2) next.name = t("err.name");
    if (!EMAIL_RE.test((f.email ?? "").trim())) next.email = t("err.email");
    if (!passwordOk(f.password ?? "")) next.password = t("err.password");
    if (!(f.access_code ?? "").trim()) next.code = t("err.code");
    setErrors(next);
    if (Object.keys(next).length) return;
    setError("");
    setStatus("loading");
    try {
      const email = f.email.trim();
      const r = await api.signupStaff({ full_name: f.full_name.trim(), email, password: f.password, role, access_code: f.access_code.trim(), preferred_language: lang });
      pendingOtp.save({ email, code: r.dev_otp, purpose: "verify_email", staff: true });
      setStatus("success");
      router.push("/verify");
    } catch (err) {
      setStatus("error");
      setError(errText(err, t("common.error")));
      setTimeout(() => setStatus("idle"), 1200);
    }
  };

  return (
    <>
      <p className="mb-2 inline-flex items-center gap-1.5 rounded-full bg-ink px-3 py-1 text-xs font-semibold text-white"><ShieldCheck className="h-3.5 w-3.5" />{t("staff.kicker")}</p>
      <AuthHeading title={t("staff.signupTitle")} sub={t("staff.signupSub")} />
      <form onSubmit={submit} className="space-y-5" noValidate>
        <Field label={t("staff.role")} index={0}>
          <Tabs value={role} onChange={setRole} items={[{ value: "admin", label: t("staff.admin") }, { value: "teacher", label: t("staff.teacher") }]} />
        </Field>
        <Field id="name" label={t("auth.fullName")} error={errors.name} index={1}>
          <Input id="name" name="full_name" autoComplete="name" aria-invalid={!!errors.name} />
        </Field>
        <Field id="email" label={t("auth.email")} error={errors.email} index={2}>
          <Input id="email" name="email" type="email" autoComplete="email" aria-invalid={!!errors.email} />
        </Field>
        <Field id="pw" label={t("auth.password")} error={errors.password} index={3}>
          <PasswordInput id="pw" name="password" autoComplete="new-password" value={password} onChange={(e) => setPassword(e.target.value)} aria-invalid={!!errors.password} showLabel={t("auth.showPassword")} hideLabel={t("auth.hidePassword")} />
        </Field>
        <StrengthMeter password={password} />
        <Field id="code" label={t("staff.code")} hint={t("staff.codeHint")} error={errors.code} index={4}>
          <Input id="code" name="access_code" autoComplete="off" aria-invalid={!!errors.code} />
        </Field>
        <FormAlert>{error}</FormAlert>
        <Button type="submit" size="lg" variant="ink" className="w-full" status={status} loadingLabel={t("auth.creating")}>{t("auth.create")}</Button>
      </form>
      <div className="mt-8 space-y-2 text-center text-sm text-ink-2">
        <p>{t("staff.haveAccount")} <Link href="/staff/login" className="font-medium text-sky-700 hover:underline">{t("auth.signIn")}</Link></p>
        <p><Link href="/signup" className="text-ink-3 hover:text-ink">{t("auth.createTitle")} →</Link></p>
      </div>
    </>
  );
}
