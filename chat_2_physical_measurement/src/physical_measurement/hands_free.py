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

_UNIT_SUFFIXES = {
    "мм",
    "mm",
    "миллиметр",
    "миллиметра",
    "миллиметров",
    "градус",
    "градуса",
    "градусов",
}

_RUSSIAN_ONES = {
    "ноль": 0,
    "один": 1,
    "одна": 1,
    "одно": 1,
    "два": 2,
    "две": 2,
    "три": 3,
    "четыре": 4,
    "пять": 5,
    "шесть": 6,
    "семь": 7,
    "восемь": 8,
    "девять": 9,
}
_RUSSIAN_TEENS = {
    "десять": 10,
    "одиннадцать": 11,
    "двенадцать": 12,
    "тринадцать": 13,
    "четырнадцать": 14,
    "пятнадцать": 15,
    "шестнадцать": 16,
    "семнадцать": 17,
    "восемнадцать": 18,
    "девятнадцать": 19,
}
_RUSSIAN_TENS = {
    "двадцать": 20,
    "тридцать": 30,
    "сорок": 40,
    "пятьдесят": 50,
    "шестьдесят": 60,
    "семьдесят": 70,
    "восемьдесят": 80,
    "девяносто": 90,
}
_RUSSIAN_HUNDREDS = {
    "сто": 100,
    "двести": 200,
    "триста": 300,
    "четыреста": 400,
    "пятьсот": 500,
    "шестьсот": 600,
    "семьсот": 700,
    "восемьсот": 800,
    "девятьсот": 900,
}
_RUSSIAN_THOUSANDS = {"тысяча", "тысячи", "тысяч"}
_RUSSIAN_WHOLE_MARKERS = {"целая", "целое", "целые", "целых"}
_RUSSIAN_FRACTION_SCALES = {
    "десятая": 10,
    "десятых": 10,
    "сотая": 100,
    "сотых": 100,
    "тысячная": 1000,
    "тысячных": 1000,
}


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
    anchor_b: FeatureAnchor | None = None
    anchor_c: FeatureAnchor | None = None
    evidence_frame_id: str | None = None
    uncertainty: Decimal | int | float | str | None = None
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


def _strip_unit_suffix(parts: list[str]) -> list[str]:
    if parts and parts[-1] in _UNIT_SUFFIXES:
        return parts[:-1]
    return parts


def _extract_spoken_sign(parts: list[str]) -> tuple[int, list[str]]:
    if not parts:
        return 1, parts
    if parts[0] == "минус":
        return -1, parts[1:]
    if parts[0] == "плюс":
        return 1, parts[1:]
    return 1, parts


def _parse_russian_under_1000(parts: list[str]) -> int | None:
    if not parts:
        return None
    if len(parts) == 1 and parts[0] == "ноль":
        return 0

    index = 0
    value = 0

    if parts[index] in _RUSSIAN_HUNDREDS:
        value += _RUSSIAN_HUNDREDS[parts[index]]
        index += 1
        if index == len(parts):
            return value

    if index < len(parts):
        token = parts[index]
        if token in _RUSSIAN_TEENS:
            value += _RUSSIAN_TEENS[token]
            index += 1
        elif token in _RUSSIAN_TENS:
            value += _RUSSIAN_TENS[token]
            index += 1
            if (
                index < len(parts)
                and parts[index] in _RUSSIAN_ONES
                and _RUSSIAN_ONES[parts[index]] != 0
            ):
                value += _RUSSIAN_ONES[parts[index]]
                index += 1
        elif token in _RUSSIAN_ONES and _RUSSIAN_ONES[token] != 0:
            value += _RUSSIAN_ONES[token]
            index += 1
        else:
            return None

    return value if index == len(parts) else None


def _parse_russian_cardinal(parts: list[str]) -> int | None:
    thousand_positions = [
        index for index, token in enumerate(parts) if token in _RUSSIAN_THOUSANDS
    ]
    if len(thousand_positions) > 1:
        return None
    if not thousand_positions:
        return _parse_russian_under_1000(parts)

    position = thousand_positions[0]
    thousands_parts = parts[:position]
    remainder_parts = parts[position + 1 :]

    thousands = 1 if not thousands_parts else _parse_russian_under_1000(thousands_parts)
    if thousands is None or not 1 <= thousands <= 999:
        return None

    remainder = 0 if not remainder_parts else _parse_russian_under_1000(remainder_parts)
    if remainder is None:
        return None
    return thousands * 1000 + remainder


def _parse_fraction_component(parts: list[str], *, scale: int) -> int | None:
    digits = len(str(scale)) - 1
    if len(parts) == digits and all(token in _RUSSIAN_ONES for token in parts):
        value = 0
        for token in parts:
            value = value * 10 + _RUSSIAN_ONES[token]
        return value

    value = _parse_russian_cardinal(parts)
    if value is None or not 0 <= value < scale:
        return None
    return value


def _parse_explicit_russian_fraction(parts: list[str]) -> Decimal | None:
    marker_positions = [
        index for index, token in enumerate(parts) if token in _RUSSIAN_WHOLE_MARKERS
    ]
    if not marker_positions:
        return None
    if len(marker_positions) != 1:
        raise AmbiguousMeasurementCommand("spoken value contains multiple whole-part markers")

    marker_position = marker_positions[0]
    if marker_position == 0 or marker_position >= len(parts) - 2:
        raise MeasurementCommandError("spoken fraction is incomplete")

    scale = _RUSSIAN_FRACTION_SCALES.get(parts[-1])
    if scale is None:
        raise MeasurementCommandError("spoken fraction requires an explicit decimal scale")

    whole = _parse_russian_cardinal(parts[:marker_position])
    fraction = _parse_fraction_component(parts[marker_position + 1 : -1], scale=scale)
    if whole is None or fraction is None:
        raise MeasurementCommandError("spoken fraction is not a supported Russian number")

    fraction_digits = len(str(scale)) - 1
    return Decimal(f"{whole}.{fraction:0{fraction_digits}d}")


def _parse_compact_two_digit_fraction(parts: list[str]) -> int | None:
    if (
        len(parts) == 2
        and parts[0] == "ноль"
        and parts[1] in _RUSSIAN_ONES
    ):
        return _RUSSIAN_ONES[parts[1]]

    value = _parse_russian_cardinal(parts)
    if value is None or not 10 <= value <= 99:
        return None
    return value


def _parse_russian_measurement_words(parts: list[str]) -> Decimal:
    explicit_fraction = _parse_explicit_russian_fraction(parts)
    if explicit_fraction is not None:
        return explicit_fraction

    candidates: set[Decimal] = set()
    for split_at in range(1, len(parts)):
        whole_candidate = _parse_russian_cardinal(parts[:split_at])
        fraction_candidate = _parse_compact_two_digit_fraction(parts[split_at:])
        if whole_candidate is None or fraction_candidate is None:
            continue
        candidates.add(Decimal(f"{whole_candidate}.{fraction_candidate:02d}"))

    if len(candidates) > 1:
        raise AmbiguousMeasurementCommand("spoken value has multiple valid interpretations")
    if len(candidates) == 1:
        return candidates.pop()
    raise MeasurementCommandError("measurement value must be numeric or supported Russian words")


def normalize_measurement_number(payload: str) -> Decimal:
    normalized = _normalize_text(payload)
    parts = _strip_unit_suffix(normalized.split())
    if not parts:
        raise MeasurementCommandError("measurement value is missing")

    had_spoken_sign = parts[0] in {"минус", "плюс"}
    spoken_sign, parts = _extract_spoken_sign(parts)
    if not parts:
        raise MeasurementCommandError("measurement value is missing")

    numeric_mentions = _NUMERIC_LIKE_RE.findall(" ".join(parts))
    if numeric_mentions:
        if len(numeric_mentions) > 1:
            raise AmbiguousMeasurementCommand("command contains multiple numeric values")
        if len(parts) != 1:
            raise MeasurementCommandError("numeric measurement value must be one token")

        token = parts[0]
        if had_spoken_sign and token.startswith(("+", "-")):
            raise AmbiguousMeasurementCommand("measurement value contains multiple signs")
        if "," in token and "." in token:
            raise AmbiguousMeasurementCommand("mixed decimal separators are ambiguous")
        if not _NUMBER_RE.fullmatch(token):
            raise MeasurementCommandError("measurement value must be numeric")

        value = Decimal(token.replace(",", "."))
        if not value.is_finite():
            raise MeasurementCommandError("measurement value must be finite")
        return value * spoken_sign

    value = _parse_russian_measurement_words(parts)
    return value * spoken_sign


class MeasurementCommandParser:
    """Provider-independent deterministic parser for measurement voice commands."""

    _CONFIRM = {"подтвердить", "подтверди", "подтверждаю"}
    _REJECT = {"отклонить", "отклони", "отмена", "отменить"}
    _CORRECT_PREFIXES = ("исправить ", "исправь ", "коррекция ")

    def parse(self, text: str) -> ParsedMeasurementCommand:
        normalized = _normalize_text(text)
        if normalized == "замер":
            return ParsedMeasurementCommand(MeasurementCommandIntent.TRIGGER, normalized)
        if normalized.startswith("замер "):
            return ParsedMeasurementCommand(
                MeasurementCommandIntent.VALUE,
                normalized,
                normalize_measurement_number(normalized.removeprefix("замер ")),
            )
        if normalized in self._CONFIRM:
            return ParsedMeasurementCommand(MeasurementCommandIntent.CONFIRM, normalized)
        if normalized in self._REJECT:
            return ParsedMeasurementCommand(MeasurementCommandIntent.REJECT, normalized)
        for prefix in self._CORRECT_PREFIXES:
            if normalized.startswith(prefix):
                return ParsedMeasurementCommand(
                    MeasurementCommandIntent.CORRECT,
                    normalized,
                    normalize_measurement_number(normalized.removeprefix(prefix)),
                )
        raise MeasurementCommandError(f"unsupported measurement command: {normalized!r}")


class HandsFreeMeasurementController:
    """State machine for candidate creation and explicit verification."""

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
            return self._submit_candidate(command.value, ProvenanceSource.VOICE_REPORTED, command)
        if command.intent is MeasurementCommandIntent.CONFIRM:
            return self._confirm(command)
        if command.intent is MeasurementCommandIntent.REJECT:
            return self._reject(command)
        if command.intent is MeasurementCommandIntent.CORRECT:
            return self._correct(command)
        raise AssertionError(f"unhandled command intent: {command.intent}")

    def submit_candidate(
        self, *, value: Decimal | int | float | str, source: ProvenanceSource
    ) -> HandsFreeTransition:
        if source not in {
            ProvenanceSource.VOICE_REPORTED,
            ProvenanceSource.OCR_MEASURED,
            ProvenanceSource.DEVICE_REPORTED,
        }:
            raise ValueError("hands-free candidate source must be voice, OCR or device")
        return self._submit_candidate(value, source, None)

    def submit_manual_fallback(
        self, *, value: Decimal | int | float | str
    ) -> HandsFreeTransition:
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
            value,
            ProvenanceSource.MANUAL_MEASURED,
            None,
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
            anchor_c=self._context.anchor_c,
            evidence_frame_id=self._context.evidence_frame_id,
            uncertainty=self._context.uncertainty,
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
            session_id=self._session_id, measurement_id=measurement_id
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
            session_id=self._session_id, measurement_id=old_measurement_id
        )
        self._state = HandsFreeMeasurementState(
            phase=HandsFreePhase.AWAITING_VALUE,
            last_verified_measurement_id=self._state.last_verified_measurement_id,
            last_rejected_measurement_id=old_measurement_id,
        )
        assert command.value is not None
        return self._submit_candidate(
            command.value, ProvenanceSource.VOICE_REPORTED, command
        )

    def _discard_current_candidate(self) -> PhysicalMeasurement:
        measurement_id = self._require_pending_candidate("replace with manual fallback")
        measurement = self._service.reject_candidate(
            session_id=self._session_id, measurement_id=measurement_id
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
