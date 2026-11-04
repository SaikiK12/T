"""Check consistency of caller-declared equation-input metadata, without values.

Every timestamp, role, digest and provenance label is an unverified caller claim.
All timestamps must already use ``common_clock_id``; this module neither maps
venue clocks nor proves historical availability, causality, source identity,
execution eligibility or an economic effect. It reads no files or market data.

``received_ns`` denotes the declared collector receipt and ``available_ns`` the
declared usable time. Snapshot freshness uses ``observation_ns``, closed-interval
freshness its exclusive end, and publication freshness ``publication_ns``.
Derived freshness uses the oldest ancestor observation, never its new receipt.
Zero default age/skew tolerances are deliberately strict caller policies, not
calibrated venue limits. A caller must explicitly choose any nonzero tolerance.
"""

from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
import re
from collections.abc import Mapping


_KINDS = {"snapshot", "closed_interval", "publication", "derived"}
_ROLES = {"observed", "proxy", "latent"}
_PROVENANCE = {"recorded_receipt": 0, "current_archive": 1, "unknown": 2}
_REVISIONS = {"none_as_recorded", "known", "unknown"}
_TIME_FIELDS = ("observation_ns", "first_seen_ns", "received_ns", "available_ns",
                "revision_first_seen_ns", "interval_start_ns", "interval_end_ns",
                "publication_ns")


@dataclass(frozen=True)
class InputRecord:
    name: str
    role: str
    unit: str
    source_sha256: str
    provenance: str
    clock_id: str
    first_seen_ns: int
    received_ns: int
    available_ns: int
    kind: str = "snapshot"
    observation_ns: int | None = None
    currency: str | None = None
    scale: str | int | None = None
    multiplier: str | int | None = None
    revision_status: str = "unknown"
    revision_first_seen_ns: int | None = None
    interval_start_ns: int | None = None
    interval_end_ns: int | None = None
    interval_semantics: str | None = None
    interval_complete: bool | None = None
    publication_ns: int | None = None
    parents: tuple[str, ...] = ()


@dataclass(frozen=True)
class InputRequirement:
    unit: str
    currency: str | None = None
    scale: str | int | None = None
    multiplier: str | int | None = None
    allow_proxy: bool = False
    allowed_provenance: tuple[str, ...] = ("recorded_receipt",)
    max_age_ns: int = 0
    kind: str | None = None


@dataclass(frozen=True)
class DeclarationIssue:
    code: str
    name: str | None
    detail: str


@dataclass(frozen=True)
class DeclarationReport:
    issues: tuple[DeclarationIssue, ...]
    input_roles: tuple[tuple[str, str], ...]
    source_identity_authenticated: bool = field(default=False, init=False)
    clock_mapping_verified: bool = field(default=False, init=False)
    point_in_time_verified: bool = field(default=False, init=False)
    clock_transform_verified: bool = field(default=False, init=False)
    historical_availability_proven: bool = field(default=False, init=False)
    causal_identification_established: bool = field(default=False, init=False)
    actual_order_allowed: bool = field(default=False, init=False)
    activation_allowed: bool = field(default=False, init=False)

    @property
    def declaration_checks_passed(self):
        return not self.issues


def _ns(value):
    return type(value) is int and 0 <= value <= 2**63 - 1


def _text(value):
    return isinstance(value, str) and bool(value.strip()) and value == value.strip()


def _positive_decimal(value):
    # These are metadata constants, not measurements. No binary floats/bools.
    if type(value) not in (str, int):
        return None
    try:
        result = Decimal(value)
    except (InvalidOperation, ValueError):
        return None
    return result if result.is_finite() and result > 0 else None


def check_input_contracts(records, requirements, *, decision_ns,
                          common_clock_id, max_join_skew_ns=0):
    """Return declaration issues; passing never authenticates any input.

    Requirements are keyed by input name and must cover parents as well as
    formula inputs. ``kind=derived`` describes construction; its role must still
    be observed/proxy/latent. A proxy requires explicit ``allow_proxy=True`` and
    retains that role. Latent inputs and unknown revision status are refused.
    ``current_archive`` requires an explicit provenance allowance, which still
    cannot establish that the data existed at an earlier decision time.

    Max join skew compares observation anchors of non-derived inputs, not
    download/receipt times. Units are exact declared labels, not a dimensional
    or instrument-specification proof. Source digests receive syntax checks only.
    """
    issues = []

    def issue(code, name, detail):
        issues.append(DeclarationIssue(code, name, detail))

    if not _ns(decision_ns):
        issue("invalid_decision_time", None, "decision_ns must be a nonnegative integer")
    if not _text(common_clock_id):
        issue("invalid_common_clock", None, "an explicit common clock declaration is required")
    if not _ns(max_join_skew_ns):
        issue("invalid_join_tolerance", None, "max_join_skew_ns must be a nonnegative integer")
    if not isinstance(requirements, Mapping):
        raise TypeError("requirements must be keyed by input name")

    rows = {}
    for index, record in enumerate(records):
        if index >= 128:
            issue("input_limit", None, "at most128 input/ancestor records are supported")
            break
        if not isinstance(record, InputRecord):
            issue("invalid_record", None, "expected InputRecord metadata")
            continue
        if not isinstance(record.name, str) or not re.fullmatch(r"[a-z][a-z0-9_]*", record.name):
            issue("invalid_name", None, "input names must be lower-case identifiers")
            continue
        if record.name in rows:
            issue("duplicate_input", record.name, "input names must be unique")
            continue
        rows[record.name] = record

    if not rows:
        issue("empty_inputs", None, "no input declarations were supplied")

    for name in requirements:
        if name not in rows:
            issue("missing_input", name, "required input has no record; it is not zero")
    for name, record in rows.items():
        req = requirements.get(name)
        if not isinstance(req, InputRequirement):
            issue("missing_requirement", name, "every input and parent needs an InputRequirement")
            req = None
        if not isinstance(record.role, str) or record.role not in _ROLES:
            issue("invalid_role", name, "declare observed/proxy/latent; derived is a construction kind")
        elif record.role == "latent":
            issue("latent_input", name, "a latent quantity cannot supply an observed measurement")
        elif record.role == "proxy" and (req is None or req.allow_proxy is not True):
            issue("proxy_not_allowed", name, "proxy use requires an explicit allowance and retained label")
        if not _text(record.unit) or (req is not None and record.unit != req.unit):
            issue("unit_mismatch", name, "input unit must match the declared requirement")
        if record.currency is not None and not _text(record.currency):
            issue("invalid_currency", name, "currency, when supplied, must be a nonempty label")
        if not isinstance(record.source_sha256, str) or not re.fullmatch(r"[a-fA-F0-9]{64}", record.source_sha256):
            issue("invalid_digest", name, "source_sha256 must contain 64 hexadecimal characters")
        policy = req.allowed_provenance if req is not None else ()
        valid_policy = (isinstance(policy, tuple) and bool(policy)
                        and all(isinstance(p, str) and p in ("recorded_receipt", "current_archive") for p in policy))
        if not isinstance(record.provenance, str) or record.provenance not in _PROVENANCE or record.provenance == "unknown":
            issue("unknown_provenance", name, "an unknown provenance label cannot establish availability")
        elif req is not None and valid_policy and record.provenance not in policy:
            issue("provenance_not_allowed", name, "acquisition provenance is outside caller policy")
        if not _text(record.clock_id) or record.clock_id != common_clock_id:
            issue("clock_mismatch", name, "timestamps must already declare the caller's common clock")
        if not isinstance(record.kind, str) or record.kind not in _KINDS:
            issue("invalid_kind", name, "unknown input construction kind")
        if not isinstance(record.revision_status, str) or record.revision_status not in _REVISIONS or record.revision_status == "unknown":
            issue("unknown_revision", name, "omitted or unknown revision status remains unknown")
        elif record.revision_status == "known" and record.revision_first_seen_ns is None:
            issue("missing_revision_time", name, "a known revision requires its first-seen declaration")
        elif record.revision_status == "none_as_recorded" and record.revision_first_seen_ns is not None:
            issue("revision_contradiction", name, "a revision time contradicts none_as_recorded")

        for attr in _TIME_FIELDS:
            value = getattr(record, attr)
            required = attr in ("first_seen_ns", "received_ns", "available_ns")
            if value is None and not required:
                continue
            if not _ns(value):
                issue("invalid_timestamp", name, f"{attr} must be a nonnegative integer")
            elif _ns(decision_ns) and value > decision_ns:
                issue("future_timestamp", name, f"{attr} is after the decision cutoff")
        if all(_ns(getattr(record, attr)) for attr in ("first_seen_ns", "received_ns", "available_ns")):
            if not record.first_seen_ns <= record.received_ns <= record.available_ns:
                issue("availability_order", name, "require first_seen <= received <= available")
            for attr in ("observation_ns", "interval_end_ns", "publication_ns"):
                value = getattr(record, attr)
                if _ns(value) and value > record.first_seen_ns:
                    issue("before_observation", name, f"first_seen precedes {attr}")
            if _ns(record.revision_first_seen_ns) and record.revision_first_seen_ns > record.received_ns:
                issue("before_revision", name, "receipt precedes this revision's first-seen time")

        if record.kind == "snapshot" and not _ns(record.observation_ns):
            issue("missing_observation_time", name, "snapshot freshness needs its observation time")
        if record.kind == "publication" and not _ns(record.publication_ns):
            issue("missing_publication_time", name, "publication input needs a publication time")
        if record.kind == "closed_interval":
            if not (_ns(record.interval_start_ns) and _ns(record.interval_end_ns)
                    and record.interval_start_ns < record.interval_end_ns):
                issue("invalid_interval", name, "closed interval needs start < exclusive end")
            if record.interval_semantics != "start_inclusive_end_exclusive" or record.interval_complete is not True:
                issue("incomplete_interval", name, "declare interval boundaries and completed contents explicitly")

        if not isinstance(record.parents, tuple) or any(not _text(p) for p in record.parents):
            issue("invalid_parents", name, "parents must be a tuple of input names")
        elif len(set(record.parents)) != len(record.parents):
            issue("duplicate_parent", name, "a parent cannot be named twice")
        if record.kind == "derived" and not record.parents:
            issue("missing_parents", name, "derived inputs require explicit parents")
        elif record.kind != "derived" and record.parents:
            issue("unexpected_parents", name, "only derived construction declares parents")

        for attr in ("scale", "multiplier"):
            value = getattr(record, attr)
            if value is not None and _positive_decimal(value) is None:
                issue("invalid_" + attr, name, f"{attr} must be an exact positive decimal declaration")
        if req is not None:
            if not _text(req.unit) or type(req.allow_proxy) is not bool or not _ns(req.max_age_ns):
                issue("invalid_requirement", name, "unit, proxy policy or age tolerance is invalid")
            if not valid_policy:
                issue("invalid_requirement", name, "provenance policy must list explicit known labels")
            if req.kind is not None and (not isinstance(req.kind, str) or req.kind not in _KINDS or req.kind != record.kind):
                issue("kind_mismatch", name, "input construction differs from requirement")
            if req.currency is not None and (not _text(req.currency) or record.currency != req.currency):
                issue("currency_mismatch", name, "required currency is absent or mismatched")
            for attr in ("scale", "multiplier"):
                expected = getattr(req, attr)
                if expected is not None:
                    want, actual = _positive_decimal(expected), _positive_decimal(getattr(record, attr))
                    if want is None or actual is None or want != actual:
                        issue(attr + "_mismatch", name, f"required {attr} is absent, invalid or mismatched")

    anchors, visiting = {}, set()

    def anchor(name):
        if name in anchors:
            return anchors[name]
        if name in visiting:
            issue("dependency_cycle", name, "derived ancestry contains a cycle")
            return None
        visiting.add(name)
        record = rows[name]
        result = None
        if record.kind == "derived":
            parent_anchors = []
            parents = record.parents if isinstance(record.parents, tuple) else ()
            for parent_name in parents:
                if not isinstance(parent_name, str) or parent_name not in rows:
                    issue("missing_parent", name, "a named parent has no input record")
                    continue
                parent = rows[parent_name]
                value = anchor(parent_name)
                if value is not None:
                    parent_anchors.append(value)
                if parent.role in ("proxy", "latent") and record.role != parent.role:
                    issue("role_laundering", name, "derived construction cannot clear a parent's measurement class")
                child_provenance = _PROVENANCE.get(record.provenance, -1) if isinstance(record.provenance, str) else -1
                parent_provenance = _PROVENANCE.get(parent.provenance, 2) if isinstance(parent.provenance, str) else 2
                if child_provenance < parent_provenance:
                    issue("provenance_laundering", name, "derived construction cannot improve parent provenance")
                if parent.revision_status in ("known", "unknown") and record.revision_status != parent.revision_status:
                    issue("revision_laundering", name, "derived construction cannot clear parent revision status")
                for attr in ("first_seen_ns", "received_ns", "available_ns"):
                    child_time, parent_time = getattr(record, attr), getattr(parent, attr)
                    if _ns(child_time) and _ns(parent_time) and child_time < parent_time:
                        issue("before_parent", name, f"derived {attr} precedes a parent")
                if parent.revision_status == "known" and _ns(parent.revision_first_seen_ns):
                    if _ns(record.revision_first_seen_ns) and record.revision_first_seen_ns < parent.revision_first_seen_ns:
                        issue("before_parent_revision", name, "derived revision predates a parent revision")
            if parents and len(parent_anchors) == len(parents):
                result = min(parent_anchors)
        else:
            attr = ({"snapshot": "observation_ns", "closed_interval": "interval_end_ns",
                     "publication": "publication_ns"}.get(record.kind)
                    if isinstance(record.kind, str) else None)
            if attr is not None and _ns(getattr(record, attr)):
                result = getattr(record, attr)
        visiting.remove(name)
        anchors[name] = result
        return result

    for name, record in rows.items():
        value = anchor(name)
        req = requirements.get(name)
        if value is not None and _ns(decision_ns) and isinstance(req, InputRequirement) and _ns(req.max_age_ns):
            if decision_ns - value > req.max_age_ns:
                issue("stale_input", name, "observation/ancestor age exceeds caller tolerance")
    leaf_anchors = [anchors[name] for name, record in rows.items()
                    if record.kind != "derived" and anchors[name] is not None]
    if leaf_anchors and _ns(max_join_skew_ns) and max(leaf_anchors) - min(leaf_anchors) > max_join_skew_ns:
        issue("join_skew", None, "non-derived observation anchors exceed caller join tolerance")
    return DeclarationReport(tuple(issues), tuple((name, r.role) for name, r in rows.items()))
