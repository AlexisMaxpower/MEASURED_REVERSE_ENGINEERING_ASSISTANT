# Build / Reuse Check — Ring 5 Dimensioned View

**Date:** 2026-09-30  
**Ring:** 5  
**Branch:** `chat-3/pass-5`  
**Base:** frozen Ring 4 head `aa53603b4f845b63a0962ddacd921ea4dbf01b54`  
**Authorization:** explicit user-requested continuation; no newer Chat 6 worker directive for Chat 3 was present when Ring 5 started.

## Goal

Implement the Chat 3-owned **Dimensioned View** described by the product SSOT:

```text
Clean Reference Image
+
Geometry Overlay
+
Dimension Lines
+
Physical Measurements
+
Confidence / Provenance
```

The view is a derived visualization. It must not become another source of metric truth and must not replace the canonical `SketchPackage v1` boundary to Chat 4.

## Reuse decision

No new rendering dependency is introduced.

Ring 5 reuses:

- canonical `SketchPackage v1` as the complete geometry/dimension input;
- existing Chat 3 entity/dimension provenance;
- SVG as the established open vector interchange/display format already named in the product SSOT/CAD bridge roadmap;
- Python standard library only for deterministic text/XML generation and escaping.

## Why not add a graphics framework

The required artifact is a deterministic 2D engineering overlay, not a general-purpose design canvas.

Adding a UI/rendering framework (`svgwrite`, Cairo, Qt, browser automation, etc.) would add dependency and platform surface without providing needed product semantics. The hard part is MREA-specific traceability/layout policy, which must remain explicit in our code regardless of library choice.

## MREA-specific logic built in this pass

`DimensionedViewRenderer` owns:

- deterministic geometry projection from `MAT_XY_MM` to SVG pixels;
- rendering of v1 `POINT`, `LINE`, `CIRCLE`, `ARC` entities;
- rendering of `DISTANCE`, `DIAMETER`, `RADIUS`, `ANGLE` dimensions;
- visible dimension value/unit;
- `measurement_id`, provenance and verified state traceability;
- geometry provenance/confidence summary;
- unresolved-state summary;
- deterministic annotation lanes;
- optional clean-reference image composition only when explicit `MAT_XY_MM` image bounds are supplied.

## Explicit anti-guess rule for reference imagery

A clean image cannot be aligned from `SketchPackage` alone because pixel registration is not part of that contract.

Therefore Ring 5 does **not** infer image bounds from pixel dimensions or geometry extents.

Optional background composition requires a slice-local `ReferenceImageLayer` containing:

- image `href`;
- `min_x_mm`, `min_y_mm`, `max_x_mm`, `max_y_mm`;
- opacity.

Invalid/non-positive bounds fail closed.

## Truth hierarchy

The renderer is read-only.

It does not:

- recalculate verified dimension values;
- modify `measurement_id`;
- upgrade provenance;
- resolve conflicts;
- promote unresolved geometry;
- move sketch entities.

It displays what `SketchPackage` already says.

## Output ownership

The SVG/artifact model is **slice-local** and is not a new shared wire contract.

Downstream CAD continues to consume:

```text
SketchPackage v1
```

No changes are required under `core/contracts/`, shared fixtures, integration tests, or Chat 4.

## Dependencies

New Ring 5 dependencies: **none**.

Existing OpenCV dependency remains unchanged for Ring 3 vision extraction.

## Decision

**REUSE SVG + Python standard library; BUILD only the MREA-specific deterministic dimensioned-view and traceability policy.**
