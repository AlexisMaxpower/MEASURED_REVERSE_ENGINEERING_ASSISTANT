# PASS 8 — BUILD / REUSE CHECK

**Проблема:** Chat 2 уже умел принимать `OCR_MEASURED` как источник measurement candidate, но не имел provider-neutral OCR pipeline: строгого разбора текста, unit consistency, ambiguity handling и evidence-bound перехода в state machine.

**Есть ли готовое open-source решение:** YES. Tesseract, EasyOCR, PaddleOCR и другие библиотеки умеют извлекать текст из изображения. Они не определяют MREA-specific physical-truth policy.

**Можно ли использовать:** PARTIAL.

**Что используем:** внешний OCR engine в будущем должен поставлять `OcrObservation` (`raw_text`, confidence, provider name, view/reference/evidence context). В Pass 8 runtime dependency на конкретный OCR engine не добавляется.

**Что пишем сами:** `OcrMeasurementReader`, deterministic `OcrReadStatus`, `OcrMeasurementProposal`, `OcrMeasurementPipeline`, unit/evidence/context validation и regression tests.

**Почему:** распознавание текста можно переиспользовать, но решение «является ли этот текст единственным допустимым физическим значением для текущего measurement type и можно ли создать candidate» является доменной ответственностью MREA.

**Lock-in risk:** LOW. OCR provider не входит в measurement contract; pipeline принимает простой provider-neutral observation.

**Fallback:** `NO_VALUE`, `AMBIGUOUS`, `INVALID`, `UNIT_MISMATCH` не создают measurement candidate. Пользователь продолжает manual/voice/device workflow. Даже `confidence=1.0` не верифицирует значение автоматически.
