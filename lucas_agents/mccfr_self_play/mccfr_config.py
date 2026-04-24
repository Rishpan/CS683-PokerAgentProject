import os


PACKAGE_DIR = os.path.dirname(__file__)
ABSTRACTION_DIR = os.path.join(PACKAGE_DIR, "abstractions")
POLICY_DIR = os.path.join(PACKAGE_DIR, "policies")

PROFILE_PRESETS = {
    "rich_hand_strength_v4": {
        "abstraction_name": "rich_hand_strength",
        "abstraction_version": "rich_hand_strength_v4",
        "abstraction_ref": os.path.join("abstractions", "rich_hand_strength_v4.py"),
        "policy_filename": "mccfr_policy.rich_hand_strength_v4.json",
        "legacy_policy_filenames": (
            "mccfr_policy.rich_hand_strength_v4.json",
            "mccfr_policy.rich_hand_strength_v3.json",
            "mccfr_policy.json",
        ),
    },
    "rich_hand_strength_v3": {
        "abstraction_name": "rich_hand_strength",
        "abstraction_version": "rich_hand_strength_v3",
        "abstraction_ref": os.path.join("abstractions", "rich_hand_strength_v3.py"),
        "policy_filename": "mccfr_policy.rich_hand_strength_v3.json",
        "legacy_policy_filenames": (
            "mccfr_policy.rich_hand_strength_v3.json",
            "mccfr_policy.json",
        ),
    },
    "bayes_opponent_compact_v1": {
        "abstraction_name": "bayes_opponent_compact",
        "abstraction_version": "bayes_opponent_compact_v1",
        "abstraction_ref": os.path.join("abstractions", "bayes_opponent_compact_v1.py"),
        "policy_filename": "mccfr_policy.bayes_opponent_compact_v1.json",
        "legacy_policy_filenames": (
            "mccfr_policy.bayes_opponent_compact_v1.json",
        ),
    },
}

# Change this single value to switch the default abstraction-policy pair.
DEFAULT_PROFILE_KEY = "rich_hand_strength_v4"

ACTIVE_PROFILE = PROFILE_PRESETS[DEFAULT_PROFILE_KEY]
DEFAULT_ABSTRACTION_NAME = ACTIVE_PROFILE["abstraction_name"]
DEFAULT_ABSTRACTION_VERSION = ACTIVE_PROFILE["abstraction_version"]
DEFAULT_ABSTRACTION_REF = ACTIVE_PROFILE["abstraction_ref"]
DEFAULT_POLICY_FILENAME = ACTIVE_PROFILE["policy_filename"]
DEFAULT_POLICY_PATH = os.path.join(POLICY_DIR, DEFAULT_POLICY_FILENAME)
LEGACY_POLICY_PATHS = tuple(
    os.path.join(PACKAGE_DIR, filename) for filename in ACTIVE_PROFILE["legacy_policy_filenames"]
)
LEGACY_POLICY_PATH = LEGACY_POLICY_PATHS[-1]

DEFAULT_BOOTSTRAP_ITERATIONS = 500
DEFAULT_INITIAL_STACK = 1000
DEFAULT_SMALL_BLIND = 10
DEFAULT_MAX_ROUNDS = 1
DEFAULT_CHECKPOINT_INTERVAL = 100
DEFAULT_LOG_INTERVAL = 25
DEFAULT_POSTFLOP_SIMULATIONS = 64
