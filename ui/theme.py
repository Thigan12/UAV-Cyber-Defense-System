# ui/theme.py — Global colour tokens and QSS stylesheet for UAV IDS Dashboard

# ═══════════════════════════════════════════
#  COLOUR TOKENS (Dark Military / Cyberpunk)
# ═══════════════════════════════════════════
BG_DARK = "#0a0f18"
PANEL_BG = "#131b26"
SIDEBAR_BG = "#0e1420"
HEADER_BG = "#0c1018"
CARD_BG = "#1a2332"

ACCENT_CYAN = "#00d4ff"
ACCENT_PURPLE = "#7c3aed"
SAFE_GREEN = "#00ff88"
ALERT_RED = "#ff003c"
WARN_ORANGE = "#ff6600"
WARN_YELLOW = "#fbbf24"

TEXT_PRIMARY = "#e2e8f0"
TEXT_MUTED = "#64748b"
TEXT_DIM = "#475569"

BORDER_DEFAULT = "#1e293b"
BORDER_ACTIVE = "#00d4ff"

# ═══════════════════════════════════════════
#  ATTACK CLASS COLOURS
# ═══════════════════════════════════════════
CLASS_COLOURS = {
    0: SAFE_GREEN,      # Normal
    1: ALERT_RED,       # RC Hijack
    2: WARN_ORANGE,     # Mode Forcing
    3: WARN_YELLOW,     # GPS Spoofing
    4: "#ff00ff",       # Disarm (magenta)
}

CLASS_NAMES = {
    0: "Normal",
    1: "RC Hijack",
    2: "Mode Forcing",
    3: "GPS Spoofing",
    4: "Disarm",
}

# ═══════════════════════════════════════════
#  FLIGHT MODE NAMES (ArduCopter)
# ═══════════════════════════════════════════
MODE_NAMES = {
    0: "STABILIZE", 1: "ACRO", 2: "ALT_HOLD", 3: "AUTO",
    4: "GUIDED", 5: "LOITER", 6: "RTL", 7: "CIRCLE",
    9: "LAND", 16: "POSHOLD",
}
