"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { ArrowLeft } from "lucide-react";
import { api } from "@/core/api";
import { useI18n } from "@/providers/i18n";
import { Button, type ButtonStatus } from "@/components/ui/button";
import { Input } from "@/components/ui/primitives";
import { EMAIL_RE, Field, formValues } from "@/components/ui/field";
import { AuthHeading, FormAlert, errText, pendingOtp } from "@/components/auth/auth-kit";

export default function ForgotPage() {
  const { t } = useI18n();
  const router = useRouter();
  const [fieldError, setFieldError] = useState<string | null>(null);
  const [status, setStatus] = useState<ButtonStatus>("idle");
  const [error, setError] = useState("");
  const submit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const email = (formValues(e.currentTarget).email ?? "").trim();
    if (!EMAIL_RE.test(email)) return setFieldError(t("err.email"));
    setFieldError(null);
    setError("");
    setStatus("loading");
    try {
      const r = await api.forgotPassword(email);
      pendingOtp.save({ email, code: r.dev_otp, purpose: "reset_password" });
      router.push("/reset");
    } catch (err) {
      setStatus("idle");
      setError(errText(err, t("common.error")));
    }
  };
  return (
    <>
      <Link href="/login" className="mb-6 inline-flex items-center gap-1.5 text-sm text-ink-3 hover:text-ink"><ArrowLeft className="h-4 w-4" />{t("auth.signIn")}</Link>
      <AuthHeading title={t("auth.forgotTitle")} sub={t("auth.forgotSub")} />
      <form onSubmit={submit} className="space-y-5">
        <Field id="email" label={t("auth.email")} error={fieldError}>
          <Input id="email" name="email" type="email" autoComplete="email" aria-invalid={!!fieldError} />
        </Field>
        <FormAlert>{error}</FormAlert>
        <Button type="submit" size="lg" className="w-full" status={status}>{t("auth.sendCode")}</Button>
      </form>
    </>
  );
}
