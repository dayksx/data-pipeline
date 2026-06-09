# Analyse : qualité des données et impact du nettoyage

**Dataset :** Online Retail (UK B2B)  
**Pipeline :** bronze → silver (`spark/jobs/transform.py`)  
**Table cible :** `public.sales_clean`  
**Devise :** GBP (£)

## Résumé exécutif

Le fichier source `data/retails.csv` contient **10 500 lignes** pour un revenu brut de ~£12,5M. Après nettoyage, il reste **8 601 lignes** pour **£10 982 247,11** de revenu. Environ **18 % des lignes** sont exclues — principalement des annulations, des quantités invalides et des données de test. Le nettoyage est **critique** : les KPIs bruts surestiment le chiffre d'affaires réel.

## Profil du fichier source

| Métrique | Valeur brute |
|----------|-------------|
| Lignes totales | 10 500 |
| Période | 12 jan 2010 → 11 déc 2011 |
| Factures distinctes (hors annulations) | ~102 |
| Clients distincts | ~4 302 |
| Produits distincts | ~7 122 |
| Pays | 6 (dont Utopia = test) |
| Revenu brut (toutes lignes) | ~£12,5M |

## Problèmes de qualité identifiés

### 1. Annulations (~5 % des lignes)

| Problème | Volume | Règle de nettoyage |
|----------|--------|-------------------|
| Factures annulées (`InvoiceNo` commence par `C`) | **521 lignes (5,0 %)** | Exclues dans `transform.py` |

Les annulations fausseraient le revenu net si incluses. En B2B, les avoirs et annulations sont fréquents — ils doivent être traités séparément, pas mélangés aux ventes.

### 2. Valeurs manquantes (~1–2 % par colonne)

| Colonne | Lignes nulles |
|---------|--------------|
| InvoiceNo | 116 |
| StockCode | 114 |
| Quantity | 117 |
| InvoiceDate | 117 |
| UnitPrice | 115 |
| CustomerID | 116 |
| Country | 114 |
| Revenue | 232 |

Les lignes avec des nulls sur les colonnes clés sont **supprimées** — elles casseraient les jointures et les métriques client/produit.

### 3. Quantités invalides (~2,2 %)

| Problème | Volume | Impact |
|----------|--------|--------|
| Quantité ≤ 0 | **235 lignes** | Retours, ajustements ou erreurs de saisie |

Seules les lignes avec `quantity > 0` sont conservées. Les retours ne sont pas modélisés séparément dans la couche silver.

### 4. Géographie de test

| Problème | Volume | Règle |
|----------|--------|-------|
| `country = 'Utopia'` | **115 lignes** | Exclues — valeur de test |

Inclure Utopia fausserait les rapports par marché.

### 5. Prix négatifs

Quelques lignes avec `unit_price < 0` existent dans le brut. Le filtre `unit_price >= 0` les exclut.

### 6. Doublons

Déduplication sur la clé : `(customer_id_hash, invoice_no, stock_code, invoice_date, quantity)`.

## Impact du nettoyage sur les KPIs

| Métrique | Avant nettoyage | Après nettoyage | Delta |
|----------|----------------|-----------------|-------|
| Lignes | 10 500 | 8 601 | **−18 %** |
| Revenu | ~£12,5M (brut) / ~£11,7M (exclusions basiques) | **£10 982 247,11** | ~−12 à −15 % |

> Le revenu nettoyé est **recomputé** : `revenue = round(quantity × unit_price, 2)` — le pipeline ne fait pas confiance à la colonne `Revenue` source.

## Règles appliquées dans `transform.py`

1. Exclure `InvoiceNo` commençant par `C` (annulations)
2. Supprimer les nulls sur les colonnes clés
3. Filtrer `quantity > 0` et `unit_price >= 0`
4. Exclure `country = 'Utopia'`
5. Dédupliquer sur la clé composite
6. Hasher `CustomerID` → `customer_id_hash` (SHA-256 + salt, PII supprimée)
7. Recalculer `revenue`, dériver `sale_date` et `sale_month`

## Recommandations

1. **Toujours interroger `sales_clean`**, jamais le CSV brut, pour les KPIs officiels.
2. **Documenter les exclusions** dans tout rapport — 18 % de lignes en moins change les conclusions.
3. **Traiter les annulations séparément** si un KPI « revenu net après retours » est requis.
4. **Vérifier la cohérence** : `total_revenue` gold = `SUM(revenue)` sur `sales_clean`.

## Tables Postgres associées

- `public.sales_clean` — couche silver nettoyée (source de vérité)
- `public.total_revenue` — sanity check : doit égaler la somme de `sales_clean.revenue`
