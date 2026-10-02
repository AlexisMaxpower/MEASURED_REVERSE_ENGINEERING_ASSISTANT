# Pass 19 — SOLIDWORKS part-document startup gate

## Scope

Chat 4B vendor-only hardening for SOLIDWORKS 2026 session startup.

## Problem

`SolidWorksSession.Open()` resolved a part template and called `NewDocument(...)`, but after a non-null return it did not verify the actual document type. A misconfigured explicit/default template could therefore create a non-Part document and still proceed toward FRONT-plane discovery and sketch startup.

This is a vendor-host truth problem: the worker must not treat “NewDocument returned something” as equivalent to “a SOLIDWORKS Part was created.”

## Implementation

After `NewDocument(...)` succeeds, the C# agent now reads the real `IModelDoc2.GetType()` result and requires:

```text
swDocumentTypes_e.swDocPART
```

The gate executes before FRONT-plane selection and before sketch creation. Any other document type throws from the existing startup `try` block, so `CleanupFailedOpen(...)` closes/releases the partial document and the normal startup failure response remains fail-closed.

The message deliberately contains `template`, so the existing startup classifier reports `PART_TEMPLATE_UNAVAILABLE` rather than a transfer success/failure after CAD mutation.

## API basis

SOLIDWORKS API defines `IModelDoc2.GetType()` as returning the document type from `swDocumentTypes_e`; `swDocPART` is the Part value. No extension-based inference is used.

## Ownership

Changed only Chat 4B-owned SOLIDWORKS worker/test/docs surfaces. No canonical contracts, Python verification policy, shared CI, or lifecycle semantics were changed.

## Verification boundary

Ordinary CI/static regression can prove ordering and failure-path wiring. It cannot prove the behavior of a real installed SOLIDWORKS 2026 host. Because `SolidWorksSession.cs` is part of the fingerprinted host boundary, any prior positive standing host qualification is reusable only if its recorded fingerprint matches the resulting integrated boundary.
