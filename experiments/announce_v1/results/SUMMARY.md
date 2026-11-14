# announce_v1 (R271): NULL

- **Family:** 64 strategies; 1881 event legs, 1219 priced, 662 with no traded instrument at the event hour.
- **Clusters by type:** earn_add 143, fund_freq 35, holder_drop 3, margin_add 116, pairs_add 92, perp_launch 270, prelist 45, spot_list 31, upgrade 85.
- **Legs by venue:** mexc 107, perp 618, spot 494.
- **Reality check:** the family's max-t null has its 95th percentile at 684.11.
- **Survivors (all gates):** none.
- **Prereg sha:** 4ac89c693d78. Costs 40, 80, 120 bp round trip at 1x/2x/3x.

## Top 15 by t (1x)

| Strategy | n | 1x mean | Median | Hit | t | RC p | Halves | 2025+ (n) | 2x | 3x | Null p | Pass |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| fund_freq long 1h | 35 | +3.59% | +3.97% | 71% | 3.31 | 0.5352 | +5.43 / +1.86 | +1.86% (18) | +3.19% | +2.79% | nan | no |
| prelist short 168h | 45 | +11.48% | +18.05% | 73% | 2.03 | 0.8811 | +9.12 / +13.74 | +14.43% (37) | +11.08% | +10.68% | nan | no |
| earn_add short 168h | 143 | +3.85% | +8.68% | 64% | 1.75 | 0.9515 | +2.84 / +4.86 | +6.72% (12) | +3.45% | +3.05% | nan | no |
| margin_add short 72h | 116 | +2.14% | +3.09% | 63% | 1.63 | 0.9740 | +3.50 / +0.78 | n/a% (0) | +1.74% | +1.34% | nan | no |
| fund_freq long 24h | 35 | +11.43% | +0.21% | 51% | 1.55 | 0.9815 | +5.97 / +16.60 | +16.60% (18) | +11.03% | +10.63% | nan | no |
| fund_freq long 72h | 35 | +18.31% | -1.32% | 46% | 1.31 | 0.9965 | +1.93 / +33.78 | +33.78% (18) | +17.91% | +17.51% | nan | no |
| fund_freq long 168h | 35 | +81.49% | -1.92% | 46% | 1.29 | 0.9970 | +2.64 / +155.96 | +155.96% (18) | +81.09% | +80.69% | nan | no |
| earn_add short 24h | 143 | +1.45% | +1.29% | 57% | 1.26 | 0.9975 | +0.26 / +2.61 | +2.79% (12) | +1.05% | +0.65% | nan | no |
| earn_add short 72h | 143 | +2.11% | +4.84% | 64% | 1.20 | 0.9985 | +0.99 / +3.20 | +3.63% (12) | +1.71% | +1.31% | nan | no |
| margin_add short 24h | 116 | +1.14% | +1.75% | 57% | 1.10 | 1.0000 | +2.17 / +0.11 | n/a% (0) | +0.74% | +0.34% | nan | no |
| upgrade long 168h | 85 | +1520.67% | -3.23% | 41% | 1.00 | 1.0000 | +3075.50 / +2.00 | n/a% (0) | +1520.27% | +1519.87% | nan | no |
| prelist short 24h | 45 | +3.87% | +8.31% | 62% | 0.92 | 1.0000 | +2.18 / +5.48 | +4.16% (37) | +3.47% | +3.07% | nan | no |
| pairs_add short 168h | 92 | +1.66% | +3.63% | 60% | 0.84 | 1.0000 | +0.72 / +2.60 | n/a% (0) | +1.26% | +0.86% | nan | no |
| prelist long 1h | 45 | +0.95% | -0.47% | 42% | 0.80 | 1.0000 | +2.24 / -0.28 | +0.57% (37) | +0.55% | +0.15% | nan | no |
| prelist short 72h | 45 | +4.79% | +13.10% | 71% | 0.74 | 1.0000 | +7.22 / +2.48 | +3.15% (37) | +4.39% | +3.99% | nan | no |

## Bottom 5 by t (1x)

- perp_launch short 1h: n 270, -0.91%, t -2.26
- earn_add long 1h: n 143, -1.01%, t -2.66
- upgrade long 1h: n 85, -0.73%, t -3.06
- fund_freq short 1h: n 35, -4.39%, t -4.05
- pairs_add long 1h: n 92, -0.77%, t -4.41
