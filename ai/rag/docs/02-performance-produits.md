# Analyse : performance produits et bestsellers

**Dataset :** Online Retail (UK B2B)  
**Grain :** une ligne = un article sur une facture  
**Source :** `sales_clean` / table gold `top_products`  
**Devise :** GBP (£)

## Résumé exécutif

Le catalogue compte **~7 100 codes produits** (stock codes) distincts dans les données brutes, réduit après nettoyage. Les ventes sont **très concentrées** : le top 10 par quantité représente une part significative du volume total. Le classement par **quantité** et par **revenu** diverge — les produits les plus vendus en unités ne sont pas forcément les plus rentables.

## Top 10 produits par quantité vendue (global)

| Rang | Stock code | Description | Quantité | Revenu |
|------|------------|-------------|----------|--------|
| 1 | 80595 | Product 80595 | 332 | £10 037,26 |
| 2 | 80502 | Product 80502 | 324 | £5 295,78 |
| 3 | 71319 | Product 71319 | 307 | £6 416,71 |
| 4 | 73901 | Product 73901 | 305 | £5 808,28 |
| 5 | 76668 | Product 76668 | 298 | £7 847,02 |

**Observation :** le produit #1 (80595) génère le plus de volume **et** le plus de revenu dans le top 5. Le produit #2 (80502) vend presque autant d'unités mais génère **moitié moins** de revenu — prix unitaire nettement inférieur.

## Prix unitaire moyen

Sur les lignes de vente valides, le prix unitaire moyen est d'environ **£25**. Positionnement milieu de gamme cadeaux / articles ménagers, cohérent avec le positionnement B2B du distributeur.

## Leaders mensuels par revenu (6 derniers mois)

Les bestsellers **changent chaque mois** quand on classe par revenu — contrairement au top global par quantité qui est stable.

### Juillet 2011

| Rang | Stock code | Revenu mensuel |
|------|------------|----------------|
| 1 | 81364 | £6 751,16 |
| 2 | 79000 | £4 871,00 |
| 3 | 79886 | £4 831,40 |

### Août 2011 (mois record)

| Rang | Stock code | Revenu mensuel |
|------|------------|----------------|
| 1 | 76117 | £8 269,94 |
| 2 | 75635 | £7 262,48 |
| 3 | 81323 | £6 241,93 |

### Octobre 2011

| Rang | Stock code | Revenu mensuel |
|------|------------|----------------|
| 1 | 79778 | £6 114,33 |
| 2 | 76365 | £5 514,11 |
| 3 | 80946 | £5 310,34 |

**Insight :** aucun produit ne domine durablement le classement mensuel par revenu. Le portefeuille est **rotatif** — typique d'un grossiste avec un large assortiment et des commandes récurrentes variées.

## Implications métier

1. **Planification stock :** le top global par quantité (80595, 80502) mérite une attention prioritaire pour la disponibilité.
2. **Pricing :** écarter les produits à fort volume / faible revenu unitaire (80502) pour des actions de marge.
3. **Reporting :** distinguer KPIs **volume** (quantité) et **valeur** (revenu) — les deux répondent à des questions différentes.
4. **Analyse ad-hoc :** utiliser `sales_clean` groupé par `stock_code` et `sale_month` pour des classements personnalisés.

## Requêtes utiles

- KPI fixe : `run_gold_query("top_products_by_quantity")` → table `public.top_products`
- Classement mensuel : requête SQL sur `sales_clean` avec `ROW_NUMBER() OVER (PARTITION BY sale_month ORDER BY revenue DESC)`

## Tables Postgres associées

- `public.top_products` — top 10 global par quantité
- `public.sales_clean` — grain ligne pour analyses produit custom
