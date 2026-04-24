"""Helpers for loading and validating MCCFR abstraction modules."""

import importlib
import importlib.util
import inspect
import os
import sys
from pathlib import Path

from mccfr_config import DEFAULT_ABSTRACTION_REF

CURRENT_DIR = Path(__file__).resolve().parent
LEGACY_ABSTRACTION_REFS = {
    ("rich_hand_strength_v3", None): Path("abstractions") / "rich_hand_strength_v3.py",
    ("rich_hand_strength_v3", "mccfr_abstraction"): Path("abstractions") / "rich_hand_strength_v3.py",
    ("rich_hand_strength_v3", "mccfr_abstraction.py"): Path("abstractions") / "rich_hand_strength_v3.py",
}
REQUIRED_CALLABLES = (
    "build_info_key",
    "observe_opponent_actions",
    "abstraction_state_upper_bound",
)
REQUIRED_CONSTANTS = (
    "ABSTRACTION_NAME",
    "ABSTRACTION_VERSION",
)


def canonicalize_abstraction_ref(abstraction_ref=None):
  """Return a stable abstraction reference for metadata and loading."""
  if not abstraction_ref:
    return DEFAULT_ABSTRACTION_REF

  candidate = str(abstraction_ref)
  if candidate.endswith(".py") or os.path.sep in candidate:
    path = Path(candidate)
    if not path.is_absolute():
      if path.exists():
        path = path.resolve()
      else:
        path = (CURRENT_DIR / path).resolve()
    try:
      return os.path.relpath(path, CURRENT_DIR)
    except ValueError:
      return str(path)
  return candidate


def _is_file_reference(abstraction_ref):
  return abstraction_ref.endswith(".py") or os.path.sep in abstraction_ref


def _load_module_from_file(abstraction_ref):
  path = Path(abstraction_ref)
  if not path.is_absolute():
    if path.exists():
      path = path.resolve()
    else:
      path = (CURRENT_DIR / path).resolve()
  if not path.exists():
    raise FileNotFoundError(f"Abstraction file does not exist: {path}")

  module_name = f"mccfr_custom_abstraction_{abs(hash(str(path)))}"
  spec = importlib.util.spec_from_file_location(module_name, path)
  if spec is None or spec.loader is None:
    raise ImportError(f"Could not import abstraction file: {path}")
  module = importlib.util.module_from_spec(spec)
  spec.loader.exec_module(module)
  return module


def _load_module_from_import_path(abstraction_ref):
  if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))
  return importlib.import_module(abstraction_ref)


def validate_abstraction_module(module, abstraction_ref):
  for name in REQUIRED_CONSTANTS:
    if not hasattr(module, name):
      raise AttributeError(
          f"Abstraction '{abstraction_ref}' is missing required constant {name}."
      )
  for name in REQUIRED_CALLABLES:
    value = getattr(module, name, None)
    if not callable(value):
      raise AttributeError(
          f"Abstraction '{abstraction_ref}' is missing required callable {name}()."
      )
  return module


def load_abstraction(abstraction_ref=None):
  abstraction_ref = canonicalize_abstraction_ref(abstraction_ref)
  if _is_file_reference(abstraction_ref):
    module = _load_module_from_file(abstraction_ref)
  else:
    module = _load_module_from_import_path(abstraction_ref)
  return validate_abstraction_module(module, abstraction_ref)


def abstraction_identity(module, abstraction_ref=None):
  abstraction_ref = canonicalize_abstraction_ref(abstraction_ref)
  return {
      "abstraction_ref": abstraction_ref,
      "abstraction_name": module.ABSTRACTION_NAME,
      "abstraction_version": module.ABSTRACTION_VERSION,
  }


def abstraction_is_compatible(metadata, module, abstraction_ref=None):
  """Return whether saved policy metadata matches the selected abstraction."""
  if not metadata:
    return True

  identity = abstraction_identity(module, abstraction_ref)
  saved_name = metadata.get("abstraction_name")
  saved_version = metadata.get("abstraction_version")
  saved_ref = metadata.get("abstraction_ref")
  legacy_ref = LEGACY_ABSTRACTION_REFS.get((saved_version, saved_ref))
  if legacy_ref:
    saved_ref = canonicalize_abstraction_ref(legacy_ref)

  ref_matches = saved_ref in (None, identity["abstraction_ref"])
  name_matches = saved_name in (None, identity["abstraction_name"])
  version_matches = saved_version in (None, identity["abstraction_version"])
  return ref_matches and name_matches and version_matches


def resolve_policy_abstraction_ref(metadata, explicit_abstraction_ref=None):
  """Pick the abstraction reference for a trainer/player instance."""
  if explicit_abstraction_ref:
    return canonicalize_abstraction_ref(explicit_abstraction_ref)

  if metadata:
    saved_version = metadata.get("abstraction_version")
    saved_ref = metadata.get("abstraction_ref")
    legacy_ref = LEGACY_ABSTRACTION_REFS.get((saved_version, saved_ref))
    if legacy_ref:
      return canonicalize_abstraction_ref(legacy_ref)
    if saved_ref:
      return canonicalize_abstraction_ref(saved_ref)

  return DEFAULT_ABSTRACTION_REF


def observe_opponent_action_stats(
    module,
    action_histories,
    player_uuid,
    historical_action_stats=None,
):
  """Call an abstraction's opponent-summary hook with optional match history."""
  observe = module.observe_opponent_actions
  try:
    parameters = inspect.signature(observe).parameters
  except (TypeError, ValueError):
    parameters = {}

  if "historical_action_stats" in parameters:
    return observe(
        action_histories,
        player_uuid,
        historical_action_stats=historical_action_stats,
    )
  return observe(action_histories, player_uuid)
