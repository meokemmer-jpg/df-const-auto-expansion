# DF-CONST-AUTO-EXPANSION [CRUX-MK]

Pro NEUE Konst-Klasse (z.B. K19+K20+K21+) automatisch:
- 5 Tier-Vertraege als YAML-Skelett
- 50 Klausel-Begruendungen als MD-Skelett

## Quick-Start

```bash
cd /Users/make/Projects/dark-factories/df-const-auto-expansion
PYTHONPATH=src python3 -m pytest tests/ -v
DF_BASE_DIR=/path/to/branch-hub python3 src/engine.py
```

## 5 Kern-Metriken

1. konsts_detected_count
2. konsts_expanded_count (mit neuen Files)
3. tier_files_created
4. klausel_files_created
5. idempotent_runs (zweiter Run = 0 neue Files)

## CRUX

- K_0: keine Cascade (rein write-skeleton, no LLM)
- Q_0: deterministisch + provenance-marked
- W_0: ~120k EUR/Jahr (Martin-Bandbreite + Auto-Skelett 4h/Konst eingespart)
- rho: idempotent + side-effect-class (write neue Files)
