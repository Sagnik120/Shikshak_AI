/**
 * Six-box OTP input: auto-advance, paste, backspace, and arrow navigation.
 * Shared by the email verification and password reset flows.
 */
import { $$ } from "./ui.js";

export function wireOtpInputs(container, onComplete) {
  const boxes = $$("input", container);

  const value = () => boxes.map((b) => b.value).join("");

  const paint = () =>
    boxes.forEach((b) => b.classList.toggle("filled", Boolean(b.value)));

  const maybeComplete = () => {
    paint();
    const code = value();
    if (code.length === boxes.length && onComplete) onComplete(code);
  };

  boxes.forEach((box, index) => {
    box.addEventListener("input", () => {
      // Strip anything non-numeric so a stray character can't block the box.
      box.value = box.value.replace(/\D/g, "").slice(-1);
      if (box.value && index < boxes.length - 1) boxes[index + 1].focus();
      maybeComplete();
    });

    box.addEventListener("keydown", (event) => {
      if (event.key === "Backspace" && !box.value && index > 0) {
        boxes[index - 1].focus();
        boxes[index - 1].value = "";
        paint();
      }
      if (event.key === "ArrowLeft" && index > 0) boxes[index - 1].focus();
      if (event.key === "ArrowRight" && index < boxes.length - 1) boxes[index + 1].focus();
    });

    box.addEventListener("paste", (event) => {
      event.preventDefault();
      const digits = (event.clipboardData.getData("text") || "").replace(/\D/g, "");
      if (!digits) return;
      boxes.forEach((b, i) => (b.value = digits[i] || ""));
      boxes[Math.min(digits.length, boxes.length - 1)].focus();
      maybeComplete();
    });

    box.addEventListener("focus", () => box.select());
  });

  return {
    get value() {
      return value();
    },
    clear() {
      boxes.forEach((b) => (b.value = ""));
      paint();
      boxes[0].focus();
    },
    focus() {
      boxes[0].focus();
    },
  };
}

/** Countdown that disables a resend button until the cooldown elapses. */
export function startCooldown(button, label, seconds, onTick) {
  let remaining = seconds;
  button.disabled = true;

  const tick = () => {
    if (remaining <= 0) {
      clearInterval(timer);
      button.disabled = false;
      if (label) label.textContent = "";
      return;
    }
    if (label) label.textContent = `You can request another code in ${remaining}s`;
    onTick?.(remaining);
    remaining -= 1;
  };

  tick();
  const timer = setInterval(tick, 1000);
  return () => clearInterval(timer);
}
