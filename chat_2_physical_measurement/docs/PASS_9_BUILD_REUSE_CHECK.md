# PASS 9 — BUILD / REUSE CHECK

**Проблема:** Pass 8 умеет безопасно разбирать OCR text, но не имеет provider-neutral стадии выбора области дисплея измерительного прибора до OCR.

**Есть ли готовое open-source решение:** YES. OpenCV, detector/segmentation frameworks и OCR toolkits могут находить прямоугольные области дисплея.

**Можно ли использовать:** PARTIAL.

**Что используем:** будущий detector/provider должен выдавать `DisplayRoiCandidate` с bbox, confidence и evidence context. Конкретный CV engine не входит в correctness path Pass 9.

**Что пишем сами:** deterministic `DisplayRoiSelector`, explicit `MATCH / NO_MATCH / AMBIGUOUS`, context filtering, duplicate-id/bbox validation, `DisplayRoiOcrBridge`, сохранение ROI metadata в OCR proposal и regression tests.

**Почему:** CV-библиотеки умеют находить регионы, но выбор единственного допустимого ROI для текущего view/reference/evidence context и fail-closed ambiguity policy являются MREA domain rules.

**Lock-in risk:** LOW. Detector заменяем; MREA принимает простой provider-neutral candidate object.

**Fallback:** `NO_MATCH` или `AMBIGUOUS` не создают OCR observation и не создают measurement candidate. Пользователь использует ручной/voice/device workflow либо повторяет capture.
