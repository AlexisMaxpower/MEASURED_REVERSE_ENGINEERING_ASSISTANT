# PASS 7 — BUILD / REUSE CHECK

**Проблема:** Chat 2 имел manual/raw `IMAGE_PX` anchors и canonical `feature_id`, но не имел безопасного Phase-B механизма snap-to-detected-feature.

**Есть ли готовое open-source решение:** существуют CV keypoint/edge/corner detectors и geometry libraries, но они решают детекцию, а не MREA-specific policy: deterministic candidate selection, ambiguity handling, explicit user acceptance и запрет изменения verified measurement.

**Можно ли использовать:** PARTIAL.

**Что используем:** Python standard library для selector/application policy; будущие detector providers могут использовать OpenCV/ML/другие библиотеки за provider-neutral `FeatureSnapCandidate` boundary.

**Что пишем сами:** `FeatureAnchorSelector`, `FeatureSnapCandidate`, `FeatureSnapProposal`, explicit `MATCH / NO_MATCH / AMBIGUOUS`, application gate `apply_anchor_snap()` и regression tests.

**Почему:** выбор ближайшего candidate и policy подтверждения — часть доменной истины MREA. Привязывать её к OpenCV/конкретной ML-модели нельзя. Detector должен быть заменяемым provider, а measurement truth rules должны оставаться стабильными.

**Lock-in risk:** LOW. Selector принимает простые provider-neutral candidates; CV engine не входит в domain/application contract.

**Fallback:** если detector недоступен или selection даёт `NO_MATCH / AMBIGUOUS`, исходный manual anchor остаётся без изменений. Пользователь продолжает manual workflow.
