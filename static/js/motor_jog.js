// static/js/motor_jog.js

let activeJog = null;
let bothJogActive = false;

function motorJogBoth(action, direction = null) {
  if (bothJogActive && action === "start") {
    // Already jogging both motors
    return Promise.resolve({ status: "already_jogging" });
  } else if (!bothJogActive && action === "stop") {
    // Both motors not jogging
    return Promise.resolve({ status: "not_jogging" });
  }

  let body = direction ? `direction=${direction}` : "";
  return safeFetch(`${API_PATHS.motor.jog_both}${action}`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body
  }).then(r => {
    bothJogActive = action === "start";
    return r.json()
  });
}

function motorJog(action, motorId, direction) {
  if (activeJog && action === "start") return Promise.resolve();
  if (!activeJog && action === "stop") return Promise.resolve();

  return safeFetch(`${API_PATHS.motor.jog}${action}`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: `motor_id=${motorId}&direction=${direction}`
  }).then(r => {
    activeJog = action === "start" ? { motorId, direction } : null;  
    return r.json()
  });
}


function stopJog() {
  if (!activeJog) return;
  const { motorId, direction } = activeJog;
  motorJog("stop", motorId, direction).catch(console.error);
}

function startJog(motorId, direction) {
  motorJog("start", motorId, direction).catch(() => {});
}

function attachJogButtons() {
  document.querySelectorAll("#motor-jog-card button[data-motor]").forEach(btn => {
    const motorId = btn.dataset.motor;
    const direction = btn.dataset.dir;

    btn.addEventListener("pointerdown", e => {
      e.preventDefault();
      // Ensure we receive pointerup even if finger leaves the button
      btn.setPointerCapture?.(e.pointerId);
      startJog(motorId, direction);
    });

    ["pointerup", "pointercancel"].forEach(ev =>
      btn.addEventListener(ev, stopJog)
    );
  });

  /* --------------------------------------------------
   * BOTH motors jog buttons (new)
   * -------------------------------------------------- */
  const bothCW = document.getElementById("btn-both-cw");
  const bothCCW = document.getElementById("btn-both-ccw");

  if (bothCW && bothCCW) {
    bothCW.addEventListener("pointerdown", e => {
      e.preventDefault();
      // Ensure we receive pointerup even if finger leaves the button
      bothCW.setPointerCapture?.(e.pointerId);
      motorJogBoth("start", "cw");
    });

    bothCCW.addEventListener("pointerdown", e => {
      e.preventDefault();
      // Ensure we receive pointerup even if finger leaves the button
      bothCCW.setPointerCapture?.(e.pointerId);
      motorJogBoth("start", "ccw");
    });

    ["pointerup", "pointercancel"].forEach(ev => {
      bothCW.addEventListener(ev, () => motorJogBoth("stop"));
      bothCCW.addEventListener(ev, () => motorJogBoth("stop"));
    });
  }

  window.addEventListener("blur", () => {
    stopJog();
    motorJogBoth("stop").catch(() => {});
  });

  document.addEventListener("visibilitychange", () => {
    if (document.hidden) {
      stopJog();
      motorJogBoth("stop").catch(() => {});
    }
  });
}

let motorPollingTimer = null;
let motorServiceAvailable = true;

function stopMotorPolling() {
  if (motorPollingTimer !== null) {
    clearInterval(motorPollingTimer);
    motorPollingTimer = null;
    console.info("[MOTOR] Polling stopped");
  }
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

  if (state.direction) {
    el.textContent =
      `${state.status.toUpperCase()} ${state.direction.toUpperCase()}`;
  } else {
    el.textContent = state.status.toUpperCase();
  }
}

function updateMotorStatus() {
  if (!motorServiceAvailable) {
    return;
  }

  safeFetch(API_PATHS?.motor?.status)
    .then(response => {
      if (response.status === 503) {
        // Motor service explicitly not available
        motorServiceAvailable = false;
        window.switchToMuxMode?.();
        stopMotorPolling();
        throw new Error("motor-service-unavailable");
      }

      if (!response.ok) {
        throw new Error(`motor-status-http-${response.status}`);
      }

      return response.json();
    })
    .then(data => {
      window.switchToMotorMode?.();
      updateMotorBadge("0", data["0"]);
      updateMotorBadge("1", data["1"]);
    })
    .catch(err => {
      if (err.message === "motor-service-unavailable") {
        console.info("[MOTOR] Service not available, UI disabled");
        return;
      }

      // Other errors are logged but do NOT stop polling
      console.warn("[MOTOR] Status error:", err.message);
    });
}

document.addEventListener("DOMContentLoaded", () => {
  const card = document.getElementById("motor-jog-card");
  if (!card) return;

  attachJogButtons();

  // Initial probe
  updateMotorStatus();

  // Start polling only if service still available
  motorPollingTimer = setInterval(updateMotorStatus, 1500);
});
