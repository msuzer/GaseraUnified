from flask import Flask, render_template
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
VENDOR_DIR = BASE_DIR / "vendor"

if VENDOR_DIR.exists():
    sys.path.insert(0, str(VENDOR_DIR))

from system.log_utils import debug
debug("starting service", version="1.0.0")

# Use CLI arg if provided, else check simulator preference, else default
from system import services
from system.device.device_init import init_preferences_service
init_preferences_service()

DEFAULT_GASERA_IP = "192.168.0.100"
if len(sys.argv) > 1 and sys.argv[1]:
    target_ip = sys.argv[1]
else:
    from system.preferences import KEY_SIMULATOR_ENABLED
    use_sim = services.preferences_service.get(KEY_SIMULATOR_ENABLED, False)
    target_ip = "127.0.0.1" if use_sim else DEFAULT_GASERA_IP

from system.device.device_init import init_all_services
init_all_services(target_ip)

services.buzzer_service.play("power_on")
services.display_controller.show(
    services.display_adapter.info("App Startup", "Initializing...")
)

# Recover any incomplete log segments from previous runs
from system.log_recovery_service import recover_incomplete_segments
recover_incomplete_segments()

from system.routes import system_bp
from gasera.routes import gasera_bp
from settings.routes import settings_bp
from gasera.motion.routes import motion_bp

app = Flask(__name__)

app.register_blueprint(gasera_bp, url_prefix="/gasera")
app.register_blueprint(system_bp, url_prefix="/system")
app.register_blueprint(settings_bp, url_prefix="/settings")
app.register_blueprint(motion_bp, url_prefix="/motion")

@app.route('/')
def index():
    return render_template('index.html')

def cleanup():
    """Clean up resources before exit."""
    debug("Cleaning up resources...")
    # services.gpio_service.cleanup()
    debug("Cleanup complete")

def signal_handler(signum, frame):
    """Handle termination signals."""
    debug(f"Received signal {signum}")
    cleanup()
    exit(0)

if __name__ == '__main__':
    import signal
    import atexit
    
    # Register cleanup handlers
    atexit.register(cleanup)
    # signal.signal(signal.SIGTERM, signal_handler)
    # signal.signal(signal.SIGINT, signal_handler)
    
    app.run(host="0.0.0.0", port=5001, debug=False, use_reloader=False)

