API_PATHS = {
    "measurement": {
        "start": "/gasera/api/measurement/start",
        "repeat": "/gasera/api/measurement/repeat",
        "abort": "/gasera/api/measurement/abort",
        "finish": "/gasera/api/measurement/finish",
        "events": "/gasera/api/measurement/events"
    },
    "logs": {
        "list": "/gasera/api/logs",
        "download": "/gasera/api/logs/",
        "delete": "/gasera/api/logs/delete/",
        "storage": "/gasera/api/logs/storage"
    },
    "settings": {
        "profile": "/system/profile",
        "read": "/system/prefs",
        "update": "/system/prefs",
        "buzzer": "/system/buzzer"
    },
    "version": {
        "local": "/system/version/local",
        "github": "/system/version/github",
        "checkout": "/system/version/checkout",
        "rollback": "/system/version/rollback"
    },
    "gasera": {
        "gas_colors": "/gasera/api/gas_colors"
    },
    "motion" : {
        "status": "/motion/status",
        "home": "/motion/home/",
        "step": "/motion/step/",
        "reset": "/motion/reset/"
    },
    // UI / device management routes (local LAN admin UI)
    "ui": {
        "status": "/settings/status",
        "service_restart": "/settings/service/restart",
        "device_restart": "/settings/device/restart",
        "device_shutdown": "/settings/device/shutdown"
    },
    // WiFi manager routes
    "wifi": {
        "scan": "/settings/wifi/scan",
        "saved": "/settings/wifi/saved",
        "connect": "/settings/wifi/connect",
        "switch": "/settings/wifi/switch",
        "forget": "/settings/wifi/forget"
    }
}
