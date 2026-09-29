# BUILD / REUSE CHECK — Chat 2 Pass 3 Hands-Free Measurement

**Directive:** `OD-2026-09-29-003`  
**Pass:** 3  
**Date:** 2026-09-29

```text
BUILD / REUSE CHECK

Проблема:
Нужен provider-independent parser/state machine для короткого hands-free measurement workflow:
trigger → candidate → confirm / reject / correct, с fail-closed обработкой неоднозначных чисел.

Есть ли готовое open-source решение:
Есть универсальные intent/NLU/state-machine библиотеки и speech SDK, но они решают существенно более широкую задачу.
Они не дают MREA-specific provenance/verification semantics и создают ненужную runtime/provider зависимость.

Можно ли использовать:
PARTIAL

Что используем:
Python standard library: re, unicodedata, Decimal, dataclasses, Enum.
Существующие MREA MeasurementSessionService, PhysicalMeasurement, provenance и canonical adapter.
Speech/OCR engines намеренно остаются внешними providers.

Что пишем сами:
Узкий deterministic command grammar;
normalization decimal comma/dot;
ambiguity rejection;
measurement candidate state machine;
application transitions для voice/OCR/device/manual fallback.

Почему:
Это небольшой MREA-specific domain protocol, а не generic speech recognition/NLU задача.
Использование крупной NLU/state-machine зависимости увеличило бы lock-in и поверхность отказов без продукта-пользы на этом gate.

Lock-in risk:
LOW. Parser принимает обычный text; OCR/device paths принимают Decimal-compatible value + canonical provenance enum.
Ни один speech/OCR vendor не импортируется в domain/application слой.

Fallback:
Любой provider может заменить текущий источник текста/значения, пока он передаёт provider-neutral text/value.
При нераспознанной/неоднозначной команде workflow fail-closed и сохраняет manual entry fallback.
```

## Решение

Не добавлять внешнюю speech/NLU/state-machine зависимость в Pass 3. Реализовать узкий deterministic parser и state machine в Chat 2, а распознавание речи/OCR оставить adapter/provider responsibility будущих проходов.
