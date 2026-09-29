from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from .models import FeatureAnchor, MeasurementType, PhysicalMeasurement, ProvenanceSource
from .service import MeasurementSessionService


_NUMBER_RE = re.compile(r"^[+-]?\d+(?:[.,]\d+)?$")
_NUMERIC_LIKE_RE = re.compile(r"[+-]?\d+(?:[.,]\d+)?")


class MeasurementCommandError(ValueError):
    """Base class for deterministic command-parse failures."""


class AmbiguousMeasurementCommand(MeasurementCommandError):
    """The command contains more than one plausible numeric interpretation."""


class InvalidMeasurementTransition(ValueError):
    """The parsed command is valid but illegal in the current state."""


class MeasurementCommandIntent(StrEnum):
    TRIGGER = "TRIGGER"
    VALUE = "VALUE"
    CONFIRM = "CONFIRM"
    REJECT = "REJECT"
    CORRECT = "CORRECT"


class HandsFreePhase(StrEnum):
    IDLE = "IDLE"
    AWAITING_VALUE = "AWAITING_VALUE"
    CANDIDATE_PENDING = "CANDIDATE_PENDING"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"


@dataclass(frozen=True, slots=True)
class ParsedMeasurementCommand:
    intent: MeasurementCommandIntent
    normalized_text: str
    value: Decimal | None = None


@dataclass(frozen=True, slots=True)
class MeasurementCandidateContext:
    measurement_type: MeasurementType
    view_id: str
    anchor_a: FeatureAnchor
    anchor_b: FeatureAnchor
    evidence_frame_id: str | None = None
    uncertainty_mm: Decimal | int | float | str | None = None
    instrument_type: str | None = None


@dataclass(frozen=True, slots=True)
class HandsFreeMeasurementState:
    phase: HandsFreePhase = HandsFreePhase.IDLE
    current_measurement_id: str | None = None
    last_verified_measurement_id: str | None = None
    last_rejected_measurement_id: str | None = None


@dataclass(frozen=True, slots=True)
class HandsFreeTransition:
    command: ParsedMeasurementCommand | None
    state: HandsFreeMeasurementState
    measurement: PhysicalMeasurement | None = None


def _normalize_text(text: str) -> str:
    if not isinstance(text, str):
        raise MeasurementCommandError("command must be text")
    normalized = unicodedata.normalize("NFKC", text).strip().lower().replace("ё", "е")
    normalized = " ".join(normalized.split())
    if not normalized:
        raise MeasurementCommandError("command must not be empty")
    return normalized


def normalize_measurement_number(payload: str) -> Decimal:
    """Normalize one explicit numeric token using dot/comma decimal separators.

    Thousands separators, exponent notation, mixed comma/dot forms and multiple
    numeric tokens are deliberately rejected so speech-provider text cannot be
    silently guessed into a physical value.
    """

    normalized = _normalize_text(payload)
    parts = normalized.split()
    if parts and parts[-1] in {"мм", "mm"}:
        parts = parts[:-1]
    if not parts:
        raise MeasurementCommandError("measurement value is missing")

    numeric_mentions = _NUMERIC_LIKE_RE.findall(" ".join(parts))
    if len(numeric_mentions) > 1:
        raise AmbiguousMeasurementCommand("command contains multiple numeric values")
    if len(parts) != 1:
        raise MeasurementCommandError("measurement value must be one numeric token")

    token = parts[0]
    if "," in token and "." in token:
        raise AmbiguousMeasurementCommand("mixed decimal separators are ambiguous")
    if not _NUMBER_RE.fullmatch(token):
        raise MeasurementCommandError("measurement value must be numeric")

    value = Decimal(token.replace(",", "."))
    if not value.is_finite():
        raise MeasurementCommandError("measurement value must be finite")
    return value


class MeasurementCommandParser:
    """Provider-independent parser for the narrow Pass 3 command vocabulary."""

    _CONFIRM = {"подтвердить", "подтверди", "подтверждаю"}
    _REJECT = {"отклонить", "отклони", "отмена", "отменить"}
    _CORRECT_PREFIXES = ("исправить ", "исправь ", "коррекция ")

    def parse(self, text: str) -> ParsedMeasurementCommand:
        normalized = _normalize_text(text)

        if normalized == "замер":
            return ParsedMeasurementCommand(
                intent=MeasurementCommandIntent.TRIGGER,
                normalized_text=normalized,
            )

        if normalized.startswith("замер "):
            value = normalize_measurement_number(normalized.removeprefix("замер "))
            return ParsedMeasurementCommand(
                intent=MeasurementCommandIntent.VALUE,
                normalized_text=normalized,
                value=value,
            )

        if normalized in self._CONFIRM:
            return ParsedMeasurementCommand(
                intent=MeasurementCommandIntent.CONFIRM,
                normalized_text=normalized,
            )

        if normalized in self._REJECT:
            return ParsedMeasurementCommand(
                intent=MeasurementCommandIntent.REJECT,
                normalized_text=normalized,
            )

        for prefix in self._CORRECT_PREFIXES:
            if normalized.startswith(prefix):
                value = normalize_measurement_number(normalized.removeprefix(prefix))
                return ParsedMeasurementCommand(
                    intent=MeasurementCommandIntent.CORRECT,
                    normalized_text=normalized,
                    value=value,
                )

        raise MeasurementCommandError(f"unsupported measurement command: {normalized!r}")


class HandsFreeMeasurementController:
    """State machine for candidate creation and explicit verification.

    The controller is deliberately speech-provider agnostic. Voice text enters via
    :meth:`process_voice_command`; OCR/device adapters can call :meth:`submit_candidate`
    directly with truthful provenance. All sources remain unverified until the
    explicit confirmation transition.
    """

    def __init__(
        self,
        *,
        service: MeasurementSessionService,
        session_id: str,
        context: MeasurementCandidateContext,
        parser: MeasurementCommandParser | None = None,
    ) -> None:
        self._service = service
        self._session_id = session_id
        self._context = context
        self._parser = parser or MeasurementCommandParser()
        self._state = HandsFreeMeasurementState()

    @property
    def state(self) -> HandsFreeMeasurementState:
        return self._state

    def process_voice_command(self, text: str) -> HandsFreeTransition:
        command = self._parser.parse(text)

        if command.intent is MeasurementCommandIntent.TRIGGER:
            return self._trigger(command)
        if command.intent is MeasurementCommandIntent.VALUE:
            assert command.value is not None
            return self._submit_candidate(
                value=command.value,
                source=ProvenanceSource.VOICE_REPORTED,
                command=command,
            )
        if command.intent is MeasurementCommandIntent.CONFIRM:
            return self._confirm(command)
        if command.intent is MeasurementCommandIntent.REJECT:
            return self._reject(command)
        if command.intent is MeasurementCommandIntent.CORRECT:
            assert command.value is not None
            return self._correct(command)
        raise AssertionError(f"unhandled command intent: {command.intent}")

    def submit_candidate(
        self,
        *,
        value: Decimal | int | float | str,
        source: ProvenanceSource,
    ) -> HandsFreeTransition:
        """Submit an OCR/device/voice candidate without coupling to its provider."""

        if source not in {
            ProvenanceSource.VOICE_REPORTED,
            ProvenanceSource.OCR_MEASURED,
            ProvenanceSource.DEVICE_REPORTED,
        }:
            raise ValueError("hands-free candidate source must be voice, OCR or device")
        return self._submit_candidate(value=value, source=source, command=None)

    def submit_manual_fallback(
        self,
        *,
        value: Decimal | int | float | str,
    ) -> HandsFreeTransition:
        """Replace any pending reported candidate with a manual candidate.

        Manual entry remains available as the authoritative fallback, but it still
        requires the same explicit confirmation transition before becoming verified.
        """

        if self._state.phase is HandsFreePhase.CANDIDATE_PENDING:
            self._discard_current_candidate()
        elif self._state.phase not in {
            HandsFreePhase.IDLE,
            HandsFreePhase.AWAITING_VALUE,
            HandsFreePhase.REJECTED,
            HandsFreePhase.VERIFIED,
        }:
            raise InvalidMeasurementTransition(
                f"manual fallback is not allowed from {self._state.phase.value}"
            )
        return self._submit_candidate(
            value=value,
            source=ProvenanceSource.MANUAL_MEASURED,
            command=None,
            allow_terminal_state=True,
        )

    def _trigger(self, command: ParsedMeasurementCommand) -> HandsFreeTransition:
        if self._state.phase not in {
            HandsFreePhase.IDLE,
            HandsFreePhase.VERIFIED,
            HandsFreePhase.REJECTED,
        }:
            raise InvalidMeasurementTransition(
                f"measurement trigger is not allowed from {self._state.phase.value}"
            )
        self._state = HandsFreeMeasurementState(
            phase=HandsFreePhase.AWAITING_VALUE,
            last_verified_measurement_id=self._state.last_verified_measurement_id,
            last_rejected_measurement_id=self._state.last_rejected_measurement_id,
        )
        return HandsFreeTransition(command=command, state=self._state)

    def _submit_candidate(
        self,
        *,
        value: Decimal | int | float | str,
        source: ProvenanceSource,
        command: ParsedMeasurementCommand | None,
        allow_terminal_state: bool = False,
    ) -> HandsFreeTransition:
        allowed = {HandsFreePhase.IDLE, HandsFreePhase.AWAITING_VALUE}
        if allow_terminal_state:
            allowed.update({HandsFreePhase.VERIFIED, HandsFreePhase.REJECTED})
        if self._state.phase not in allowed:
            raise InvalidMeasurementTransition(
                f"new candidate is not allowed from {self._state.phase.value}"
            )

        measurement = self._service.add_candidate(
            session_id=self._session_id,
            measurement_type=self._context.measurement_type,
            value=value,
            source=source,
            view_id=self._context.view_id,
            anchor_a=self._context.anchor_a,
            anchor_b=self._context.anchor_b,
            evidence_frame_id=self._context.evidence_frame_id,
            uncertainty_mm=self._context.uncertainty_mm,
            instrument_type=self._context.instrument_type,
        )
        self._state = HandsFreeMeasurementState(
            phase=HandsFreePhase.CANDIDATE_PENDING,
            current_measurement_id=measurement.measurement_id,
            last_verified_measurement_id=self._state.last_verified_measurement_id,
            last_rejected_measurement_id=self._state.last_rejected_measurement_id,
        )
        return HandsFreeTransition(command=command, state=self._state, measurement=measurement)

    def _confirm(self, command: ParsedMeasurementCommand) -> HandsFreeTransition:
        measurement_id = self._require_pending_candidate("confirm")
        measurement = self._service.confirm_measurement(
            session_id=self._session_id,
            measurement_id=measurement_id,
            explicit_user_confirmation=True,
        )
        self._state = HandsFreeMeasurementState(
            phase=HandsFreePhase.VERIFIED,
            last_verified_measurement_id=measurement.measurement_id,
            last_rejected_measurement_id=self._state.last_rejected_measurement_id,
        )
        return HandsFreeTransition(command=command, state=self._state, measurement=measurement)

    def _reject(self, command: ParsedMeasurementCommand) -> HandsFreeTransition:
        measurement_id = self._require_pending_candidate("reject")
        measurement = self._service.reject_candidate(
            session_id=self._session_id,
            measurement_id=measurement_id,
        )
        self._state = HandsFreeMeasurementState(
            phase=HandsFreePhase.REJECTED,
            last_verified_measurement_id=self._state.last_verified_measurement_id,
            last_rejected_measurement_id=measurement.measurement_id,
        )
        return HandsFreeTransition(command=command, state=self._state, measurement=measurement)

    def _correct(self, command: ParsedMeasurementCommand) -> HandsFreeTransition:
        old_measurement_id = self._require_pending_candidate("correct")
        self._service.reject_candidate(
            session_id=self._session_id,
            measurement_id=old_measurement_id,
        )
        # Correction text is itself a voice-reported value. It remains a candidate.
        self._state = HandsFreeMeasurementState(
            phase=HandsFreePhase.AWAITING_VALUE,
            last_verified_measurement_id=self._state.last_verified_measurement_id,
            last_rejected_measurement_id=old_measurement_id,
        )
        assert command.value is not None
        return self._submit_candidate(
            value=command.value,
            source=ProvenanceSource.VOICE_REPORTED,
            command=command,
        )

    def _discard_current_candidate(self) -> PhysicalMeasurement:
        measurement_id = self._require_pending_candidate("replace with manual fallback")
        measurement = self._service.reject_candidate(
            session_id=self._session_id,
            measurement_id=measurement_id,
        )
        self._state = HandsFreeMeasurementState(
            phase=HandsFreePhase.AWAITING_VALUE,
            last_verified_measurement_id=self._state.last_verified_measurement_id,
            last_rejected_measurement_id=measurement.measurement_id,
        )
        return measurement

    def _require_pending_candidate(self, action: str) -> str:
        if (
            self._state.phase is not HandsFreePhase.CANDIDATE_PENDING
            or self._state.current_measurement_id is None
        ):
            raise InvalidMeasurementTransition(
                f"cannot {action}: no pending measurement candidate"
            )
        return self._state.current_measurement_id
