# DDJJ_MENUDENCIAS — Step 0: read-only diagnostic (no implementation)

## Context

The new reporting-app's **Declaración Jurada Menudencias** report inflates box counts and shows extra products / alternate codes vs 3 legacy reference cases (`21-01`, `17-09`, `15-10`) and the `validate_fixes.py` case. Dates ✓, headcount ✓, per-product **Kg ✓**, but **Cajas inflated** and **extra/alternate products** present.

I have two *hypotheses* about the source/ingestion layer, **neither assumed correct yet**:

- **H-A (box count):** `fetch_salidas` sources `cantidad_cajas` from `s.nCantidad` ([sql_server.py:401](reporting-app/reporting-api/app/services/etl/sources/sql_server.py#L401) → [salidas.py:190](reporting-app/reporting-api/app/services/etl/steps/salidas.py#L190)). `nCantidad` may be a piece/unit quantity rather than a physical box count. **To be proven, not assumed.**
- **H-B (extra products):** `fetch_salidas` filters only `bEntrada=0 / bActivo=1 / bEliminado=0` and has no stock filter, whereas the legacy source (Twins **PWR054**, per `Menudencias Relevamiento.md`) runs with `Proceso productivo: TODOS` + `Filtro: En stock = NO`. **To be proven, not assumed.**

This plan covers **only the read-only diagnostic** that confirms or refutes both hypotheses and pins the exact field/expression. **No `fetch_salidas` / `salidas.py` / report changes, no stock filter, are applied in this step.** The process-exclusion filter is not touched.

## Observed deltas (the evidence the diagnostic must explain)

- Kg matches per product; Cajas inflates by a **product-specific factor** (15-10: CORAZON 32→173, LENGUA 19→218, NUEZ 31→1004, MEDULA 12→120; factor=1 for PULMON/CUAJO/GAÑOTE → those match exactly).
- Legacy `CAJAS ≈ KG ÷ a fixed per-product box weight` (MONDONGO 10, NUEZ/CORAZON/TENDON 12, PULMON 13 — constant across all 4 cases) → looks like a physical box count.
- Extra/alternate codes are purely additive (IBMCF3090 PULMON matches legacy 53 exactly, **plus** an extra IBMCFE090 PULMON 30) and they raise total Kg above legacy → legacy appears to *exclude* those rows, not consolidate them.

## Scope of this step

Build a **read-only** diagnostic (extend `reporting-api/validate_sources.py`, or a new throwaway `diagnose_cajas.py` that imports `SqlServerTwinsSource` and only issues `SELECT`s — the source already guards against non-SELECT statements). Connection/config is reused from the existing Flask config / `.env` exactly like `validate_fixes.py` (`SqlServerTwinsSource.from_flask_config`). If `MSSQL_SERVER` is not configured / unreachable, the script prints a clear message and the queries are delivered for the user to run on a Twins-connected host.

### Probe 1 — what is one "Caja"? (tests H-A)
For each reference pair, pick 2-3 worst-offender products and compute candidate box-count expressions side by side. Anchor case: **MONDONGO (IBMCFE210), fecha_emisión 2025-10-15 → legacy target 223 boxes / 2230 kg.**

For that `(date, Mercaderia_Id)`, print:
- `SUM(s.nCantidad)`            (expected ≫ 223 if H-A holds)
- `SUM(s.iPeso)/1000.0`         (expected ≈ 2230, sanity)
- `COUNT(*)` of Salida rows
- `COUNT(DISTINCT b.sCodBar)`   (barcode/label count)
- `COUNT(DISTINCT s.Identificador_Id)` and `COUNT(DISTINCT s.Movimiento_Id)`
- a `TOP 50` raw dump of **every `movimientos.Salidas` column** (+ joined Banderitas) to spot any dedicated box/bulto/cantidad-cajas field not currently selected.

Also enumerate `movimientos.Salidas` columns once (`INFORMATION_SCHEMA.COLUMNS`) to discover candidate fields. **Whichever expression returns 223 is the confirmed box-count source.** Repeat against ≥1 product per other case (e.g. NUEZ IBMCFE043 17-09 → 34; TENDON 21-01 → 17) to confirm it generalizes.

### Probe 2 — what does "En stock = NO" map to? (tests H-B)
Target the extra/alternate code **IBMCFE090 PULMON, 2025-10-15** (legacy excludes it; IBMCF3090 PULMON must stay 53). Steps:
- Enumerate stock-related columns on `movimientos.Movimientos` and `movimientos.Salidas` (`INFORMATION_SCHEMA.COLUMNS` LIKE `%stock%`, `%Stock%`, plus likely flags `bStock`, `bEnStock`, dispatch/remito linkage).
- For each candidate predicate, recompute the 15-10 product list and check: extra codes (IBMCFE090, IBMCFE240, IBMCFE290, IBMCFI250) disappear, primary codes unchanged, total → 826 / 9055.75.
- Confirm `Procesos_Id` is **not** what separates them (relevamiento says TODOS) so the process filter stays untouched.

## Deliverables after running (what I'll report back)
1. **Diagnostic evidence** — the side-by-side tables for the anchor + spot-check products and the column enumerations.
2. **Confirmed box-count source** — the exact Twins field/expression that reproduces legacy Cajas (or, if none does cleanly, what the data actually shows).
3. **Confirmed stock filter** — the exact `WHERE` predicate that reproduces legacy product inclusion/exclusion.
4. **Minimal code change to apply (proposed, not applied)** — the precise one/two-line edits to `fetch_salidas` (and comment fix in `salidas.py`), gated on the evidence above, plus the validation plan (re-run ETL + extended `validate_fixes.py` against all 4 cases: Cajas ±1, Kg ±0.10, 0 EXTRA/FALTA).

## Out of scope for this step
No edits to `fetch_salidas`, `salidas.py`, the materialized views, the report, or the UI. No stock filter applied. No change to `excluir_procesos`. Implementation happens only after you approve the confirmed findings.
