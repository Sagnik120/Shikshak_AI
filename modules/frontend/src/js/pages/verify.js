/** Email verification: submit the OTP, then sign the learner straight in. */
import { api, tokens, ApiError } from "../api.js";
import { $, showAlert, hideAlert, setLoading, toast, redirectIfSignedIn } from "../ui.js";
import { wireOtpInputs, startCooldown } from "../otp.js";

if (!redirectIfSignedIn()) {
  const params = new URLSearchParams(window.location.search);
  const email = params.get("email") || sessionStorage.getItem("shikshak.pendingEmail") || "";

  const alertBox = $("#form-alert");
  const devNotice = $("#dev-notice");
  const submitBtn = $("#submit-btn");
  const resendBtn = $("#resend-btn");
  const resendTimer = $("#resend-timer");

  if (!email) {
    window.location.replace("/signup.html");
  } else {
    $("#target-email").textContent = email;

    const devOtp = sessionStorage.getItem("shikshak.devOtp");
    if (devOtp && devNotice) {
      devNotice.textContent = `Your verification code is: ${devOtp}`;
      devNotice.hidden = false;
    }

    const otp = wireOtpInputs($("#otp-inputs"), () => submit());
    otp.focus();
    startCooldown(resendBtn, resendTimer, 60);

    async function submit() {
      const code = otp.value;
      if (code.length !== 6) {
        showAlert(alertBox, "Enter all six digits.", "error");
        return;
      }

      hideAlert(alertBox);
      setLoading(submitBtn, true);
      try {
        const session = await api.verifyEmail(email, code);
        tokens.save(session);
        sessionStorage.removeItem("shikshak.pendingEmail");
        sessionStorage.removeItem("shikshak.devOtp");
        window.location.href = "/dashboard.html?welcome=1";
      } catch (error) {
        showAlert(alertBox, error.message, "error");
        otp.clear();
        setLoading(submitBtn, false, "Verify and continue");
        if (error instanceof ApiError && error.status === 400 && /already verified/i.test(error.message)) {
          setTimeout(() => (window.location.href = "/login.html"), 1600);
        }
      }
    }

    $("#verify-form").addEventListener("submit", (event) => {
      event.preventDefault();
      submit();
    });

    resendBtn.addEventListener("click", async () => {
      hideAlert(alertBox);
      setLoading(resendBtn, true);
      try {
        const response = await api.resendOtp(email, "verify_email");
        toast("A new code is on its way.", "success");
        if (response.dev_otp && devNotice) {
          devNotice.textContent = `Your verification code is: ${response.dev_otp}`;
          devNotice.hidden = false;
        }
        otp.clear();
        startCooldown(resendBtn, resendTimer, 60);
      } catch (error) {
        showAlert(alertBox, error.message, "error");
      } finally {
        setLoading(resendBtn, false, "Resend code");
      }
    });
  }
}
