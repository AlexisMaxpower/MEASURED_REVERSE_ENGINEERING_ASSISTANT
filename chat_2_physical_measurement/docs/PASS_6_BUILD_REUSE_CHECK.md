# PASS 6 — BUILD / REUSE CHECK

**Проблема:** внутренний Chat 2 `PhysicalMeasurement` жёстко требовал ровно два anchor, тогда как canonical `PhysicalMeasurement.anchors` допускает от 1 до 3 anchor.

**Есть ли готовое open-source решение:** нет полезного внешнего решения. Это локальная доменная cardinality/invariant migration внутри MREA.

**Можно ли использовать:** NO.

**Что используем:** Python standard library, существующий `FeatureAnchor`, существующий canonical v1 schema (`anchors.minItems=1`, `maxItems=3`).

**Что пишем сами:** backward-compatible ordered anchor slots `anchor_a` / optional `anchor_b` / optional `anchor_c`, canonical `anchors` view, validation и regression tests.

**Почему:** сторонняя geometry/validation библиотека не нужна; контракт уже задаёт cardinality, а задача — честно отразить её во внутренней модели без изменения shared schema.

**Lock-in risk:** LOW. Wire representation остаётся canonical v1 array `anchors`; compatibility slots локальны для Chat 2.

**Fallback:** если позже будет одобрена breaking internal cleanup, заменить compatibility slots на единый immutable tuple/list API при сохранении того же canonical wire array.
