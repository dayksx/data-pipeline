# Analyse : tendances de revenus mensuels

**Dataset :** Online Retail (UK B2B)  
**Période :** janvier 2010 → décembre 2011 (extract tronqué au 11/12/2011)  
**Source :** `sales_clean` après nettoyage (`spark/jobs/transform.py`)  
**Devise :** GBP (£)

## Résumé exécutif

Le chiffre d'affaires total nettoyé s'élève à **£10 982 247,11** sur **24 mois calendaires**. La série mensuelle présente **deux régimes distincts** : une phase de démarrage quasi nulle (jan–nov 2010), puis un plateau stable à ~£840k–£980k/mois (déc 2010–nov 2011). Toute analyse de tendance doit traiter ces deux phases séparément.

## Statistiques mensuelles clés

| Indicateur | Valeur |
|------------|--------|
| Revenu mensuel moyen | £457 593,63 |
| Revenu mensuel médian | £547 494,00 |
| Mois le plus fort | **Août 2011** — £980 746,72 (101 factures) |
| Mois le plus faible | **Mai 2010** — £4 363,21 (5 factures) |
| Écart-type mensuel | £441 542,87 |

> **Attention :** l'écart-type est proche de la moyenne car les mois de 2010 tirent la série vers le bas. La **médiane** est un indicateur central plus fiable une fois la phase de ramp-up comprise.

## Chronologie mois par mois

### Phase 1 — Ramp-up (jan–nov 2010)

| Mois | Revenu | Factures | Articles vendus |
|------|--------|----------|-----------------|
| 2010-01 | £4 525,92 | 7 | 267 |
| 2010-02 | £6 603,81 | 3 | 169 |
| 2010-03 | £16 988,08 | 13 | 552 |
| 2010-05 | £4 363,21 | 5 | 164 |
| 2010-11 | £6 106,94 | 6 | 330 |

Revenus compris entre **£4k et £17k** par mois, avec **3 à 13 factures**. Activité incompatible avec le rythme opérationnel observé ensuite.

### Phase 2 — Plateau opérationnel (déc 2010–nov 2011)

| Mois | Revenu | Factures | Articles vendus |
|------|--------|----------|-----------------|
| 2010-12 | £848 247,18 | 101 | 33 783 |
| 2011-01 | £866 166,80 | 101 | 34 634 |
| 2011-08 | £980 746,72 | 101 | 37 435 |
| 2011-10 | £941 209,01 | 100 | 36 261 |
| 2011-11 | £853 838,63 | 101 | 34 085 |

Revenus stables autour de **£840k–£980k**, avec **~100 factures/mois** et **~35 000 lignes/mois**. Pas de saisonnalité B2C marquée — plutôt un rythme de commandes grossistes récurrentes.

## Anomalies identifiées

### 1. Saut structurel de décembre 2010

Revenu : **£6 107 (nov 2010) → £848 247 (déc 2010)** — multiplication par **~140×**. Factures : 6 → 101.

Hypothèses possibles :
- changement de périmètre de l'extract ;
- démarrage effectif d'un canal de vente ;
- migration vers un nouveau système de facturation.

**Impact analytique :** ne pas utiliser jan–nov 2010 comme baseline pour des comparaisons YoY.

### 2. Décembre 2011 incomplet

Revenu de seulement **£252 388** (90 factures) alors que les mois précédents tournent autour de £850k–£940k. L'extract CSV s'arrête le **11 décembre 2011**. Ce mois est **tronqué** et ne reflète pas une baisse réelle d'activité.

### 3. Dérive haussière légère en 2011

Dans le plateau, le revenu progresse de ~£866k (jan 2011) à un pic de ~£981k (août 2011), puis oscille. Tendance légèrement positive, sans rupture brutale avant la fin de l'extract.

## Recommandations pour le reporting

1. Segmenter les dashboards en **pré-déc 2010** vs **post-déc 2010**.
2. Exclure ou annoter **décembre 2011** dans les graphiques de tendance.
3. Privilégier la **médiane** plutôt que la moyenne pour les KPIs mensuels.
4. Utiliser la table gold `monthly_sales` pour les tendances pré-calculées.

## Tables Postgres associées

- `public.monthly_sales` — série mensuelle (revenu, factures, articles)
- `public.monthly_stats` — statistiques descriptives sur la série mensuelle
- `public.total_revenue` — agrégat global (£10 982 247,11)
