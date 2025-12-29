// ============================================================
// Phase Utilities – Phase constants and helpers
// ============================================================
// console.log("[phase_utils] loaded");

// ============================================================
// Phase Constants
// ============================================================
const PHASE = {
  IDLE: "IDLE",
  ARMED: "READY",
  HOMING: "HOMING",
  MEASURING: "MEASURING",
  PAUSED: "PAUSED",
  SWITCHING: "SWITCHING",
  ABORTED: "ABORTED"
};

window.PHASE = PHASE;

// ============================================================
// Phase Helpers
// ============================================================

window.isEnginePassive = (phase) => phase === PHASE.IDLE || phase === PHASE.ABORTED;

window.isEngineActive = (phase) => {
  return phase === PHASE.HOMING || phase === PHASE.PAUSED || 
         phase === PHASE.MEASURING || phase === PHASE.SWITCHING;
}

window.isEngineArmed = (phase) => phase === window.PHASE.ARMED; // new canonical motor-armed phase from backend

window.taskAborted = (phase) => phase === PHASE.ABORTED;

window.taskCompleted = (old_phase, new_phase) => { 
  return (old_phase === PHASE.SWITCHING && new_phase === PHASE.IDLE) ||
         (old_phase === PHASE.ARMED && new_phase === PHASE.IDLE);
}

/**
 * Get human-readable phase name
 */
window.getPhaseText = function (phase) {
  const phaseTexts = {
    [PHASE.IDLE]: "Ready",
    [PHASE.ARMED]: "Waiting",
    [PHASE.HOMING]: "Homing",
    [PHASE.MEASURING]: "Measuring",
    [PHASE.PAUSED]: "Paused",
    [PHASE.SWITCHING]: "Switching",
    [PHASE.ABORTED]: "Aborted"
  };
  return phaseTexts[phase] || "Unknown";
}
