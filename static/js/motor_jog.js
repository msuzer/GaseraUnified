// static/js/motor_jog.js

function motionStep(unitId) {
  return safeFetch(`${API_PATHS.motion.step}${unitId}`, { method: "POST" });
}

function motionHome(unitId) {
  return safeFetch(`${API_PATHS.motion.home}${unitId}`, { method: "POST" });
}

function motionReset(unitId) {
  return safeFetch(`${API_PATHS.motion.reset}${unitId}`, { method: "POST" });
}

function motionStepBoth() {
  return safeFetch(`${API_PATHS.motion.step_both}`, { method: "POST" });
}

function motionHomeBoth() {
  return safeFetch(`${API_PATHS.motion.home_both}`, { method: "POST" });
}

function motionResetBoth() {
  return safeFetch(`${API_PATHS.motion.reset_both}`, { method: "POST" });
}

function attachJogButtons() {
  document.querySelectorAll("#motor-jog-card button[data-motor]").forEach(btn => {
    const motorId = btn.dataset.motor;
    const action = btn.dataset.action;

    btn.addEventListener("pointerdown", e => {
      e.preventDefault();
      // Ensure we receive pointerup even if finger leaves the button
      btn.setPointerCapture?.(e.pointerId);

      if (action === "step") {
        motionStep(motorId);
      } else {
        motionHome(motorId);
      }
    });

    ["pointerup", "pointercancel"].forEach(ev =>
      btn.addEventListener(ev, () => motionReset(motorId))
    );
  });

  /* --------------------------------------------------
   * BOTH motors jog buttons (new)
   * -------------------------------------------------- */
  const bothStep = document.getElementById("btn-both-step");
  const bothHome = document.getElementById("btn-both-home");

  if (bothStep && bothHome) {
    bothStep.addEventListener("pointerdown", e => {
      e.preventDefault();
      // Ensure we receive pointerup even if finger leaves the button
      bothStep.setPointerCapture?.(e.pointerId);
      motionStepBoth();
    });

    bothHome.addEventListener("pointerdown", e => {
      e.preventDefault();
      // Ensure we receive pointerup even if finger leaves the button
      bothHome.setPointerCapture?.(e.pointerId);
      motionHomeBoth();
    });

    ["pointerup", "pointercancel"].forEach(ev => {
      bothStep.addEventListener(ev, () => motionResetBoth());
      bothHome.addEventListener(ev, () => motionResetBoth());
    });
  }

  window.addEventListener("blur", () => {
    motionResetBoth().catch(() => { });
  });

  document.addEventListener("visibilitychange", () => {
    if (document.hidden) {
      motionResetBoth().catch(() => { });
    }
  });
}

function motorStatusClass(status) {
  switch (status) {
    case "idle":
      return "bg-secondary";
    case "moving":
      return "bg-primary";
    case "timeout":
      return "bg-danger";
    case "limit":
      return "bg-warning text-dark";
    case "user_stop":
      return "bg-info text-dark";
    default:
      return "bg-dark";
  }
}

function updateMotorBadge(motorId, state) {
  const el = document.getElementById(`status-${motorId}`);
  if (!el || !state) return;

  el.className = "badge " + motorStatusClass(state.status || "unknown");

  if (state.action) {
    el.textContent =
      `${state.status.toUpperCase()} ${state.action.toUpperCase()}`;
  } else {
    el.textContent = state.status.toUpperCase();
  }
}

function onMotorStatusFromSSE(d) {
  if (!d || !d.motor_status) return;

  // motor_status can be {0:..., 1:...} OR {error:true}
  const ms = d.motor_status;
  if (ms.error) return;

  updateMotorBadge("0", ms["0"]);
  updateMotorBadge("1", ms["1"]);
}

document.addEventListener("DOMContentLoaded", () => {
  const card = document.getElementById("motor-jog-card");
  if (!card) return;

  attachJogButtons();

  // SSE-driven motor status (no polling)
  window.GaseraHub?.subscribe(onMotorStatusFromSSE);
});
