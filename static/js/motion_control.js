// static/js/motion_control.js

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

function attachMotionButtons() {
  document.querySelectorAll("#motion_control_card button[data-motion]").forEach(btn => {
    const motionId = btn.dataset.motion;
    const action = btn.dataset.action;

    btn.addEventListener("pointerdown", e => {
      e.preventDefault();
      // Ensure we receive pointerup even if finger leaves the button
      btn.setPointerCapture?.(e.pointerId);

      if (action === "step") {
        motionStep(motionId);
      } else {
        motionHome(motionId);
      }
    });

    ["pointerup", "pointercancel"].forEach(ev =>
      btn.addEventListener(ev, () => motionReset(motionId))
    );
  });

  /* --------------------------------------------------
   * BOTH motion buttons (new)
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

function motionStatusClass(status) {
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

function updateMotionBadge(motionId, state) {
  const el = document.getElementById(`status-${motionId}`);
  if (!el || !state) return;

  const statusStr = (state.status || "unknown").toString();
  const actionStr = state.action != null ? state.action.toString() : null;

  el.className = "badge " + motionStatusClass(statusStr);

  const pos = state.position !== null && state.position !== undefined ? state.position : "";

  if (actionStr) {
    el.textContent = `${statusStr.toUpperCase()} ${actionStr.toUpperCase()} ${pos}`;
  } else {
    el.textContent = `${statusStr.toUpperCase()} ${pos}`;
  }
}

function onMotionStatusFromSSE(d) {
  if (!d || !d.motion_status) return;

  // motion_status can be {0:..., 1:...} OR {error:true}
  const ms = d.motion_status;
  if (ms.error) return;

  updateMotionBadge("0", ms["0"]);
  updateMotionBadge("1", ms["1"]);
}

document.addEventListener("DOMContentLoaded", () => {
  const card = document.getElementById("motion_control_card");
  if (!card) return;

  attachMotionButtons();

  // SSE-driven motion status (no polling)
  window.GaseraHub?.subscribe(onMotionStatusFromSSE);
});
