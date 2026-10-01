"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { motion } from "motion/react";
import { ArrowRight } from "lucide-react";
import { api } from "@/core/api";
import { useI18n } from "@/providers/i18n";
import { Button, type ButtonStatus } from "@/components/ui/button";
import { Input, PasswordInput } from "@/components/ui/primitives";
import { EMAIL_RE, Field, formValues } from "@/components/ui/field";
import { AuthHeading, FormAlert, StrengthMeter, errText, passwordOk, pendingOtp } from "@/components/auth/auth-kit";
import { cn } from "@/lib/utils";

const LEVELS = ["beginner", "intermediate", "advanced"] as const;
type Level = (typeof LEVELS)[number];
type Errors = Partial<Record<"name" | "email" | "password" | "mentor_email", string>>;

export default function SignupPage() {
  const { t, lang } = useI18n();
  const router = useRouter();
  const [password, setPassword] = useState("");
  const [level, setLevel] = useState<Level>("beginner");
  const [status, setStatus] = useState<ButtonStatus>("idle");
  const [error, setError] = useState("");
  const [errors, setErrors] = useState<Errors>({});

  const submit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const v = formValues(e.currentTarget);
    const next: Errors = {};
    if ((v.full_name ?? "").trim().length < 2) next.name = t("err.name");
    if (!EMAIL_RE.test((v.email ?? "").trim())) next.email = t("err.email");
    if (!passwordOk(v.password ?? "")) next.password = t("err.password");
    if (v.mentor_email?.trim() && !EMAIL_RE.test(v.mentor_email.trim())) next.mentor_email = t("err.mentorEmail");
    setErrors(next);
    if (Object.keys(next).length) return;
    setError("");
    setStatus("loading");
    try {
      const email = v.email.trim();
      const r = await api.signup({
        full_name: v.full_name.trim(), email, password: v.password,
        grade: v.grade?.trim() || null, preferred_language: lang, preferred_level: level,
        mentor_name: v.mentor_name?.trim() || null, mentor_email: v.mentor_email?.trim() || null,
      });
      pendingOtp.save({ email, code: r.dev_otp, purpose: "verify_email" });
      setStatus("success");
      router.push("/verify");
    } catch (err) {
      setStatus("error");
      setError(errText(err, t("common.error")));
      setTimeout(() => setStatus("idle"), 1200);
    }
  };

  const opt = t("common.optionalTag");
  return (
    <>
      <AuthHeading title={t("auth.createTitle")} sub={t("auth.createSub")} />
      <form onSubmit={submit} className="space-y-5" noValidate>
        <Field id="name" label={t("auth.fullName")} error={errors.name} index={0}>
          <Input id="name" name="full_name" autoComplete="name" aria-invalid={!!errors.name} />
        </Field>
        <Field id="email" label={t("auth.email")} error={errors.email} index={1}>
          <Input id="email" name="email" type="email" autoComplete="email" aria-invalid={!!errors.email} />
        </Field>
        <Field id="pw" label={t("auth.password")} error={errors.password} index={2}>
          <PasswordInput id="pw" name="password" autoComplete="new-password" value={password} onChange={(e) => setPassword(e.target.value)} aria-invalid={!!errors.password} showLabel={t("auth.showPassword")} hideLabel={t("auth.hidePassword")} />
        </Field>
        <StrengthMeter password={password} />
        <div className="grid gap-5 sm:grid-cols-[1fr_1.4fr]">
          <Field id="grade" label={t("auth.grade")} optional={opt} index={3}>
            <Input id="grade" name="grade" />
          </Field>
          <Field label={t("auth.level")} index={4}>
            <div role="radiogroup" className="relative grid grid-cols-3 rounded-2xl border border-line bg-paper-2 p-1">
              {LEVELS.map((l) => (
                <button key={l} type="button" role="radio" aria-checked={level === l} onClick={() => setLevel(l)}
                  className={cn("relative z-10 rounded-xl px-1 py-2 text-xs font-medium transition-colors", level === l ? "text-ink" : "text-ink-3")}>
                  {level === l && <motion.span layoutId="level-pill" className="absolute inset-0 -z-10 rounded-xl bg-surface shadow-[var(--shadow-soft)]" />}
                  {t(`auth.level${l[0].toUpperCase()}${l.slice(1)}` as "auth.levelBeginner")}
                </button>
              ))}
            </div>
          </Field>
        </div>
        <fieldset className="rounded-2xl border border-dashed border-line-2 p-4">
          <legend className="px-1 font-hand text-lg text-sky-700">{t("auth.mentorHint")}</legend>
          <div className="grid gap-4 sm:grid-cols-2">
            <Field id="mn" label={t("auth.mentorName")} optional={opt} index={5}>
              <Input id="mn" name="mentor_name" autoComplete="off" />
            </Field>
            <Field id="me" label={t("auth.mentorEmail")} optional={opt} error={errors.mentor_email} index={6}>
              <Input id="me" name="mentor_email" type="email" autoComplete="off" aria-invalid={!!errors.mentor_email} />
            </Field>
          </div>
        </fieldset>
        <FormAlert>{error}</FormAlert>
        <Button type="submit" size="lg" className="w-full" status={status} loadingLabel={t("auth.creating")} icon={<ArrowRight className="h-4 w-4" />}>{t("auth.create")}</Button>
      </form>
      <p className="mt-8 text-center text-sm text-ink-2">
        {t("auth.haveAccount")} <Link href="/login" className="font-medium text-sky-700 hover:underline">{t("auth.signIn")}</Link>
      </p>
      <p className="mt-2 text-center text-sm"><Link href="/staff/signup" className="text-ink-3 hover:text-ink">{t("staff.signupLink")}</Link></p>
    </>
  );
}
