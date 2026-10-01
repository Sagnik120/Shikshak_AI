"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";
import { ShieldCheck, Sparkles } from "lucide-react";
import { api, ApiError } from "@/core/api";
import { useAuth } from "@/providers/auth";
import { useI18n } from "@/providers/i18n";
import { Button, type ButtonStatus } from "@/components/ui/button";
import { Input, PasswordInput } from "@/components/ui/primitives";
import { EMAIL_RE, Field, formValues } from "@/components/ui/field";
import { AuthHeading, FormAlert, errText, pendingOtp } from "@/components/auth/auth-kit";

const DEMO = {
  student: { email: "demo@shikshak.ai", password: "DemoStudent@123" },
  staff: { email: "admin@shikshak.ai", password: "DemoStudent@123" },
};

function safeNext(fallback: string) {
  const n = new URLSearchParams(window.location.search).get("next") || "";
  return n.startsWith("/") && !n.startsWith("//") ? n : fallback;
}

/** Student and staff sign-in share one form; staff mode only admits admins/teachers and opens the portal. */
export function LoginForm({ staff = false }: { staff?: boolean }) {
  const { t } = useI18n();
  const { signIn } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [status, setStatus] = useState<ButtonStatus>("idle");
  const [error, setError] = useState("");
  const [errors, setErrors] = useState<{ email?: string; password?: string }>({});

  const submit = async (e?: React.FormEvent<HTMLFormElement>, demoCreds?: { email: string; password: string }) => {
    e?.preventDefault();
    // Read what the browser actually holds (autofill included), not just React state.
    const v = e ? formValues(e.currentTarget) : {};
    const creds = demoCreds ?? { email: (v.email ?? email).trim(), password: v.password ?? password };
    const next: { email?: string; password?: string } = {};
    if (!EMAIL_RE.test(creds.email)) next.email = t("err.email");
    if (!creds.password) next.password = t("err.passwordEmpty");
    setErrors(next);
    if (Object.keys(next).length) return;
    setError("");
    setStatus("loading");
    try {
      const tok = await api.login(creds.email.trim(), creds.password);
      const isStaff = tok.user.role === "admin" || tok.user.role === "teacher";
      if (staff && !isStaff) {
        void api.revokeRefresh(tok.refresh_token);
        setStatus("idle");
        setError(t("staff.notStaff"));
        return;
      }
      signIn(tok);
      setStatus("success");
      toast.success(t("auth.signedIn"));
      router.replace(staff || isStaff ? safeNext("/admin") : safeNext("/dashboard"));
    } catch (err) {
      setStatus("error");
      if (err instanceof ApiError && err.status === 403 && /verify/i.test(err.message)) {
        const r = await api.resendOtp(creds.email.trim()).catch(() => null);
        pendingOtp.save({ email: creds.email.trim(), code: r?.dev_otp, purpose: "verify_email", staff });
        router.push("/verify");
        return;
      }
      setError(errText(err, t("common.error")));
      setTimeout(() => setStatus("idle"), 1200);
    }
  };

  const demo = staff ? DEMO.staff : DEMO.student;
  return (
    <>
      {staff && <p className="mb-2 inline-flex items-center gap-1.5 rounded-full bg-ink px-3 py-1 text-xs font-semibold text-white"><ShieldCheck className="h-3.5 w-3.5" />{t("staff.kicker")}</p>}
      <AuthHeading title={staff ? t("staff.loginTitle") : t("auth.welcomeBack")} sub={staff ? t("staff.loginSub") : t("auth.loginSub")} />
      <form onSubmit={submit} className="space-y-5" noValidate>
        <Field id="email" label={t("auth.email")} error={errors.email} index={0}>
          <Input id="email" name="email" type="email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} aria-invalid={!!errors.email} />
        </Field>
        <Field id="password" label={t("auth.password")} error={errors.password} index={1}
          hint={<Link href="/forgot" className="text-sm text-sky-700 hover:underline">{t("auth.forgot")}</Link>}>
          <PasswordInput id="password" name="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} aria-invalid={!!errors.password} showLabel={t("auth.showPassword")} hideLabel={t("auth.hidePassword")} />
        </Field>
        <FormAlert>{error}</FormAlert>
        <Button type="submit" className="w-full" size="lg" variant={staff ? "ink" : "primary"} status={status} loadingLabel={t("auth.signingIn")}>
          {t("auth.signIn")}
        </Button>
        <Button type="button" variant="soft" className="w-full" icon={<Sparkles className="h-4 w-4" />}
          onClick={() => { setEmail(demo.email); setPassword(demo.password); void submit(undefined, demo); }}>
          {t("auth.demo")}
        </Button>
      </form>
      <div className="mt-8 space-y-2 text-center text-sm text-ink-2">
        <p>
          {staff ? t("staff.newAccount") : t("auth.noAccount")}{" "}
          <Link href={staff ? "/staff/signup" : "/signup"} className="font-medium text-sky-700 hover:underline">{t("auth.createOne")}</Link>
        </p>
        <p><Link href={staff ? "/login" : "/staff/login"} className="text-ink-3 hover:text-ink">{staff ? t("staff.studentLink") : t("staff.link")}</Link></p>
      </div>
    </>
  );
}
