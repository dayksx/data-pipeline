# Analyse : répartition géographique et mix marchés

**Dataset :** Online Retail (UK B2B)  
**Champ clé :** `country` (pays du client)  
**Source :** `sales_clean`  
**Devise :** GBP (£)

## Résumé exécutif

Malgré une entreprise basée au **Royaume-Uni**, les revenus sont **remarquablement équilibrés** entre les cinq marchés principaux — chacun contribue environ **£2,1M–£2,3M**. Le UK n'est pas dominant : ~20 % des lignes seulement. C'est un profil **export / wholesale international**, pas un retailer domestique classique.

## Revenus par pays (données nettoyées)

| Pays | Revenu total | Lignes | Clients distincts | Factures |
|------|-------------|--------|-------------------|----------|
| **Germany** | £2 300 324,44 | 1 768 | 1 479 | 101 |
| **Australia** | £2 182 974,86 | 1 671 | 1 415 | 101 |
| **France** | £2 175 057,11 | 1 694 | 1 439 | 101 |
| **Norway** | £2 170 439,14 | 1 761 | 1 495 | 101 |
| **United Kingdom** | £2 153 451,56 | 1 707 | 1 436 | 101 |

**Total nettoyé :** £10 982 247,11 — la somme des cinq pays couvre 100 % du revenu post-nettoyage.

## Observations clés

### 1. Parité entre marchés

L'écart entre le pays le plus élevé (Allemagne, £2,30M) et le plus bas (UK, £2,15M) est de **~7 %** seulement. Aucun marché ne représente plus de 21 % du total.

### 2. Même nombre de factures par pays

Chaque pays compte exactement **101 factures** distinctes. Cela suggère une **répartition structurelle** des commandes — possiblement un pattern d'extract ou de répartition B2B par compte régional, pas une distribution organique de la demande.

### 3. UK = marché domestique mais pas leader

Le Royaume-Uni, marché d'origine de l'entreprise, arrive **en dernière position** en revenu. Pour le reporting exécutif, le narratif « leader domestique » ne s'applique pas à ce dataset.

### 4. Pays exclu : Utopia

**115 lignes** avec `country = 'Utopia'` ont été filtrées lors du nettoyage (`transform.py`). C'est une valeur de test / junk qui fausserait les KPIs géographiques si conservée.

## Focus : Australie et moyenne mobile 3 mois

L'Australie suit le même pattern global — saut en déc 2010, plateau en 2011.

| Mois | Revenu Australie | Moyenne mobile 3 mois |
|------|-----------------|----------------------|
| 2010-11 | £180,70 | £1 671,34 |
| 2010-12 | £161 546,37 | £55 341,99 |
| 2011-06 | £211 471,81 | £177 569,01 |
| 2011-08 | £166 334,90 | £194 846,85 |
| 2011-12 | £47 848,06 | £137 396,85 |

En 2011, le revenu australien mensuel se stabilise autour de **£155k–£212k**, avec une moyenne mobile autour de **£175k–£195k** en milieu d'année. Décembre 2011 est incomplet (extract tronqué).

## Implications métier

1. **Campagnes marketing :** traiter les 5 marchés comme des segments **égaux en importance**, pas UK-first.
2. **Logistique :** la répartition multi-pays implique des coûts d'expédition internationaux à modéliser.
3. **Analyse par pays :** filtrer `sales_clean` avec `WHERE country = '...'` pour des breakdowns custom.
4. **Attention aux 101 factures/pays :** vérifier si c'est un artefact de l'extract avant de tirer des conclusions opérationnelles.

## Tables et requêtes

- Table : `public.sales_clean` (colonne `country`)
- Requête rolling average Australie : `postgres/queries/analysis.sql` (2ᵉ requête)
- Pas de table gold dédiée par pays — analyse ad-hoc via SQL
