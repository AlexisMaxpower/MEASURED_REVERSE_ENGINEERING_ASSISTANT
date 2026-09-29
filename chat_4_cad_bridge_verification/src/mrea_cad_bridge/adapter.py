from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .model import CadSketch


@dataclass(frozen=True, slots=True)
class CadArtifact:
    format_name: str
    file_extension: str
    media_type: str
    content: str


class CadExporter(Protocol):
    format_name: str
    file_extension: str
    media_type: str

    def export(self, sketch: CadSketch) -> CadArtifact:
        ...
