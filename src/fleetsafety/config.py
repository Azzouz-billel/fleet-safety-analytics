"""All tunable thresholds and score weights.

Every magic number in the pipeline lives here so field tuning never
requires touching detector or scoring code.
Units are metric: speeds m/s or km/h (suffixed), accelerations m/s².
"""

# --- GPS processing -------------------------------------------------------

# Moving-average window for the smoothed speed series. The raw series is
# always kept alongside for validation and acceleration.
SPEED_SMOOTHING_WINDOW_S = 5.0

# --- Speeding (events/speeding.py) ----------------------------------------

# Flag only when speed exceeds limit * (1 + tolerance): avoids noise-driven
# flags right at the limit.
SPEEDING_TOLERANCE = 0.05
SPEEDING_MIN_DURATION_S = 5.0
# Severity by peak fraction over the limit: below "low" bound → low,
# below "medium" bound → medium, else high.
SPEEDING_SEVERITY_BOUNDS = {"low": 0.10, "medium": 0.20}

# --- Harsh braking / acceleration (events/harsh_*.py) ---------------------

HARSH_BRAKING_MPS2 = 3.5      # deceleration magnitude that triggers an event
HARSH_ACCEL_MPS2 = 3.0        # acceleration that triggers an event
HARSH_MERGE_GAP_S = 3.0       # spikes closer than this merge into one event
# Severity by peak |accel| in m/s².
HARSH_BRAKING_SEVERITY_BOUNDS = {"low": 5.0, "medium": 7.0}
HARSH_ACCEL_SEVERITY_BOUNDS = {"low": 4.5, "medium": 6.0}

# --- Tailgating (vision/tailgating.py) -------------------------------------

TAILGATING_MAX_GAP_S = 2.0        # time-gap to the lead vehicle that flags
TAILGATING_MIN_DURATION_S = 3.0   # must be sustained this long
TAILGATING_MIN_SPEED_MPS = 5.0    # ignore below ~18 km/h (queues, parking)
# Severity by minimum gap: below "high" bound → high, below "medium" → medium,
# else low (already under TAILGATING_MAX_GAP_S to be an event at all).
TAILGATING_SEVERITY_BOUNDS_S = {"high": 1.0, "medium": 1.5}
LEAD_VEHICLE_WIDTH_M = 1.8        # assumed car width for pinhole distance
CAMERA_FOCAL_WIDTH_RATIO = 0.85   # focal_px ≈ ratio × frame width (~62° hFOV)
VISION_ANALYSIS_HZ = 5.0          # target detection rate (frames sampled/s)

# --- Scoring (scoring.py) --------------------------------------------------

SCORE_WEIGHTS = {
    "speeding": 2.0,
    "harsh_braking": 3.0,
    "harsh_accel": 2.0,
    "tailgating": 3.0,  # Phase 2
}
SEVERITY_MULTIPLIER = {"low": 1.0, "medium": 2.0, "high": 3.0}
# Penalties are normalized per 100 km. Without a floor, a 5 km trip with one
# event would crater the score; short trips are normalized as if this long.
SCORE_NORMALIZATION_FLOOR_KM = 50.0
