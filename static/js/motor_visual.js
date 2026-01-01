// ============================================================
// Motor Profile – Rover Visual Binding (GLOBAL INIT)
// ============================================================

window.initMotorVisual = function initMotorVisual() {
    if (window.__motorVisualInitialized) return;
    window.__motorVisualInitialized = true;

    const roverCard = document.getElementById("motor-rover-card");
    if (!roverCard) {
        console.warn("[motor_visual] rover card not found");
        return;
    }

    const arms = {
        0: roverCard.querySelector('.arm[data-arm="0"]'),
        1: roverCard.querySelector('.arm[data-arm="1"]')
    };

    const PHASE_CLASS_MAP = {
        [window.PHASE.IDLE]: "phase-idle",
        [window.PHASE.ARMED]: "phase-armed",
        [window.PHASE.SWITCHING]: "phase-switching",
        [window.PHASE.MEASURING]: "phase-measuring",
        [window.PHASE.PAUSED]: "phase-paused",
        [window.PHASE.HOMING]: "phase-homing",
        [window.PHASE.ABORTED]: "phase-aborted"
    };

    function clearArmStates() {
        Object.values(arms).forEach(arm => {
            arm?.classList.remove("active", "sealed", "enabled", "disabled");
        });
    }

    function applyMotorVisualState(d) {
        const phase = d.phase;
        const ch = d.current_channel ?? null;

        // Treat FINISH as IDLE visually
        if (window.taskCompleted?.(window.__prevPhase, phase)) {
            clearArmStates();
            arms[0]?.classList.add("disabled");
            arms[1]?.classList.add("disabled");
            return;
        }

        // ----- phase class on card -----
        roverCard.classList.remove(
            "phase-idle",
            "phase-armed",
            "phase-switching",
            "phase-measuring",
            "phase-paused",
            "phase-homing",
            "phase-aborted"
        );

        const cls = PHASE_CLASS_MAP[phase];
        if (cls) roverCard.classList.add(cls);

        // ----- arm state -----
        clearArmStates();

        // ---- arm enable/disable rules ----

        // Default: both disabled
        arms[0]?.classList.add("disabled");
        arms[1]?.classList.add("disabled");

        // Idle / Ready → both disabled
        if (phase === PHASE.IDLE || window.isEngineArmed(phase)) {
            return;
        }

        // Abort → both disabled
        if (phase === PHASE.ABORTED) {
            return;
        }

        // Channel-driven enable
        if (ch === 0) {
            arms[0]?.classList.remove("disabled");
            arms[0]?.classList.add("enabled", "active");
        }
        else if (ch === 1) {
            arms[1]?.classList.remove("disabled");
            arms[1]?.classList.add("enabled", "active");
        }

        // Seal only when sampling is meaningful
        if (phase === PHASE.MEASURING || phase === PHASE.PAUSED) {
            if (ch === 0) arms[0]?.classList.add("sealed");
            if (ch === 1) arms[1]?.classList.add("sealed");
        }
    }

    // ----- subscribe exactly once -----
    window.GaseraHub.subscribe(d => {
        if (!window.isMotorMode?.()) return;
        applyMotorVisualState(d);
    });

    console.log("[motor_visual] initialized");
};
