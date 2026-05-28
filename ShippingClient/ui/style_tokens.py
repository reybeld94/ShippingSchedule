"""Design tokens compartidos (Microsoft Fluent 2 inspired)."""

# ============================================================================
# Spacing scale (Fluent uses a 4px base grid)
# ============================================================================
SPACE_2 = 2
SPACE_4 = 4
SPACE_8 = 8
SPACE_12 = 12
SPACE_16 = 16
SPACE_20 = 20
SPACE_24 = 24
SPACE_32 = 32

# ============================================================================
# Corner radii (Fluent uses small radii: 4px for controls, 8px for cards)
# ============================================================================
RADIUS_SM = 4
RADIUS_MD = 6
RADIUS_LG = 8
RADIUS_XL = 12

# ============================================================================
# Control sizing
# ============================================================================
CONTROL_HEIGHT = 32         # Fluent standard control height
CONTROL_HEIGHT_COMPACT = 28
CONTROL_HEIGHT_LARGE = 40

# ============================================================================
# Typography — Segoe UI Variable (Fluent default on Windows 11)
# ============================================================================
FONT_FAMILY_PRIMARY = "Segoe UI Variable Text"
FONT_FAMILY_DISPLAY = "Segoe UI Variable Display"
FONT_FAMILY_FALLBACK = "Segoe UI, Inter, Helvetica Neue, Arial, sans-serif"

# Type ramp (Fluent)
FONT_SIZE_CAPTION = 12
FONT_SIZE_BODY = 14
FONT_SIZE_BODY_STRONG = 14
FONT_SIZE_SUBTITLE = 16
FONT_SIZE_TITLE = 20
FONT_SIZE_TITLE_LARGE = 28
FONT_SIZE_DISPLAY = 40

# ============================================================================
# Surfaces — Fluent layered neutrals
# ============================================================================
COLOR_BG_APP = "#F3F3F3"            # NeutralBackground3 — app canvas
COLOR_BG_SUBTLE = "#FAFAFA"         # NeutralBackground2 — subtle surface
COLOR_SURFACE = "#FFFFFF"           # NeutralBackground1 — primary surface
COLOR_SURFACE_ALT = "#F9F9F9"       # Card / elevated alt surface
COLOR_SURFACE_LAYER = "#FFFFFFF2"   # Layered popovers

# ============================================================================
# Borders — Fluent neutral strokes
# ============================================================================
COLOR_BORDER = "#E5E5E5"            # NeutralStroke2
COLOR_BORDER_STRONG = "#D1D1D1"     # NeutralStroke1 — for emphasized borders
COLOR_DIVIDER = "#EDEDED"           # Subtle row dividers / gridlines

# ============================================================================
# Typography colors
# ============================================================================
COLOR_TEXT_PRIMARY = "#1B1B1B"      # NeutralForeground1
COLOR_TEXT_SECONDARY = "#616161"    # NeutralForeground2
COLOR_TEXT_TERTIARY = "#8A8A8A"     # NeutralForeground3 — placeholders, hints
COLOR_TEXT_DISABLED = "#BDBDBD"
COLOR_TEXT_ON_ACCENT = "#FFFFFF"

# ============================================================================
# Brand — Fluent Communication Blue
# ============================================================================
COLOR_PRIMARY = "#0F6CBD"           # Brand 80 — primary accent
COLOR_PRIMARY_HOVER = "#115EA3"     # Brand 70
COLOR_PRIMARY_PRESSED = "#0F548C"   # Brand 60
COLOR_PRIMARY_SUBTLE_BG = "#EBF3FC" # Brand background subtle
COLOR_PRIMARY_SUBTLE_BORDER = "#B4D6F5"
COLOR_PRIMARY_SUBTLE_TEXT = "#0F548C"

# Selection / highlights
COLOR_SELECTION_BG = "#CFE4FA"      # Subtle selection in lists/tables
COLOR_SELECTION_TEXT = "#0F2A57"

# Focus ring (Fluent uses a 2px focus outline)
COLOR_FOCUS_RING = "#0F6CBD"
FOCUS_RING_WIDTH = 2

# ============================================================================
# State colors — Fluent semantic palette
# ============================================================================
# Success — Fluent green
COLOR_SUCCESS = "#107C10"
COLOR_SUCCESS_HOVER = "#0E700E"
COLOR_SUCCESS_PRESSED = "#0B5A0B"
COLOR_SUCCESS_SOFT_BG = "#DFF6DD"
COLOR_SUCCESS_SOFT_BORDER = "#9FD89F"
COLOR_SUCCESS_SOFT_TEXT = "#0E700E"

# Danger — Fluent red
COLOR_DANGER = "#C42B1C"
COLOR_DANGER_HOVER = "#A82A1F"
COLOR_DANGER_PRESSED = "#8E2218"
COLOR_DANGER_SOFT_BG = "#FDE7E9"
COLOR_DANGER_SOFT_BORDER = "#EEACB2"
COLOR_DANGER_SOFT_TEXT = "#A82A1F"

# Warning — Fluent yellow/orange
COLOR_WARNING = "#9D5D00"
COLOR_WARNING_HOVER = "#8A5200"
COLOR_WARNING_PRESSED = "#754500"
COLOR_WARNING_SOFT_BG = "#FFF4CE"
COLOR_WARNING_SOFT_BORDER = "#FDE293"
COLOR_WARNING_SOFT_TEXT = "#8A5200"

# Info / neutral badge
COLOR_INFO_SOFT_BG = "#EBF3FC"
COLOR_INFO_SOFT_BORDER = "#B4D6F5"
COLOR_INFO_SOFT_TEXT = "#0F548C"

COLOR_NEUTRAL_SOFT_BG = "#F5F5F5"
COLOR_NEUTRAL_SOFT_BORDER = "#E0E0E0"
COLOR_NEUTRAL_SOFT_TEXT = "#424242"

# ============================================================================
# Toast / notification colors — intentionally vivid so they grab attention
# against the muted Fluent body palette. Use these only for ephemeral popups
# and live status indicators (connection dots), not for surfaces or text.
# ============================================================================
COLOR_TOAST_INFO = "#0EA5E9"        # Cyan — neutral notifications
COLOR_TOAST_SUCCESS = "#16A34A"     # Vivid green — confirmed actions
COLOR_TOAST_WARNING = "#F59E0B"     # Amber — cautions, partial states
COLOR_TOAST_DANGER = "#EF4444"      # Red — errors, disconnections

# ============================================================================
# Special-purpose marks
# ============================================================================
# Highlights cells that were just edited locally so the user can verify the
# change persisted. Distinct from the brand accent to avoid confusion with
# selection/focus.
COLOR_LOCAL_EDIT_MARK = "#1E90FF"

# Sill issue status row backgrounds — softer than the Fluent success/warning
# soft palette so entire rows don't drown the table content.
COLOR_SILL_ISSUE_COMPLETE_BG = "#DCFCE7"
COLOR_SILL_ISSUE_PARTIAL_BG = "#FEF9C3"
# Manual "Hold" status row background — a light amber, warmer/more golden than
# the partial-issue yellow so the two are distinguishable at a glance.
COLOR_SILL_HOLD_BG = "#FDE68A"

# ============================================================================
# Elevation / shadow (Fluent uses subtle layered shadows)
# ============================================================================
# Qt doesn't render CSS box-shadow on QFrame, so these are reference values
# for QGraphicsDropShadowEffect.
ELEVATION_2_BLUR = 4
ELEVATION_2_Y = 2
ELEVATION_4_BLUR = 8
ELEVATION_4_Y = 4
ELEVATION_8_BLUR = 16
ELEVATION_8_Y = 6
COLOR_SHADOW = "#00000022"          # 13% black — Fluent ambient shadow tone
