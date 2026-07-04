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
