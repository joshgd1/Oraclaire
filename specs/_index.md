# Specs Index — Oraclaire Burnout Risk Scorer

| File                        | Domain     | Description                                                                                                                                                                       |
| --------------------------- | ---------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `population-and-scoring.md` | Population | Who gets scored, how scoring tiers work, all exclusions (operational + legal-safety), opt-in/withdrawal mechanics, minimum team size, participation implications                  |
| `cost-model.md`             | Cost       | FN cost split by employee tier, FP cost with participation decay mechanism, dollar exposure formula, scaling table, participation death spiral                                    |
| `regulatory-constraints.md` | Regulation | Singapore PDPA consent, EU AI Act Annex III high-risk classification, human oversight for Critical tier, conformity assessment, transparency requirements                         |
| `product-identity.md`       | Product    | Classification not prediction, 4-tier burnout risk scorer, Random Forest + SHAP (Sprint 1, confirmed D17), provisional threshold 0.30, two-threshold serving layer, DPO hard gate |
