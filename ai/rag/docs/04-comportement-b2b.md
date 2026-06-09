# Analyse : comportement d'achat B2B et profil clients

**Dataset :** Online Retail (UK B2B)  
**Type de clientèle :** entreprises (B2B) avec quelques consommateurs  
**Source :** `sales_clean` (PII hashée : `customer_id_hash`)  
**Devise :** GBP (£)

## Résumé exécutif

Ce dataset ne ressemble pas à de l'e-commerce B2C classique. Les commandes sont des **paniers massifs** (~85 lignes par facture en moyenne, ~350 lignes/mois en phase stable), avec un petit nombre de factures mensuelles (~100) générant un volume énorme de lignes (~35 000/mois). C'est le profil d'un **grossiste** vendant à des revendeurs ou des comptes professionnels.

## Métriques comportementales

| Indicateur | Valeur |
|------------|--------|
| Lignes nettoyées | 8 601 |
| Factures distinctes | 101 |
| Clients distincts (brut) | ~4 302 |
| Clients par pays (nettoyé) | ~1 415–1 495 par marché |
| Lignes moyennes par facture | **~85,2** |
| Lignes par facture en phase stable | **~350** (35k lignes / 100 factures) |

## Signature B2B : gros paniers, peu de commandes

### Comparaison B2C vs ce dataset

| Critère | E-commerce B2C typique | Ce dataset |
|---------|------------------------|------------|
| Lignes par commande | 1–5 | **85–350** |
| Commandes par mois | milliers | **~100** |
| Saisonnalité | Noël, soldes | Plateau stable toute l'année 2011 |
| Type d'acheteur | particuliers | **comptes professionnels** |

### Ce que ça implique

- Les KPIs **panier moyen** et **fréquence de commande** doivent être interprétés en logique **wholesale**, pas retail.
- Un client avec `customer_id_hash` donné peut apparaître sur de nombreuses lignes d'une même facture — c'est normal.
- Les analyses RFM (Recency, Frequency, Monetary) sont possibles via `customer_id_hash`, mais le grain facture/ligne doit être bien compris.

## Anonymisation PII

Le pipeline remplace `CustomerID` brut par `customer_id_hash` (SHA-256 + salt) dans `transform.py` :

- La colonne `customer_id` **n'existe pas** dans `sales_clean`.
- Toute requête SQL ou analyse client doit utiliser `customer_id_hash`.
- ~4 300 clients distincts dans le brut, ~1 400–1 500 par pays après nettoyage.

## Pattern de facturation

En phase stable (2011), chaque mois compte **~100 factures** pour **~35 000 articles vendus**. Chaque facture couvre donc en moyenne **~350 références produit** — un bon de commande grossiste, pas un achat impulsif.

Le nombre de factures est **identique par pays** (101 chacun), ce qui renforce l'hypothèse d'une structure de comptes régionaux plutôt que d'une acquisition organique de clients.

## Recommandations analytiques

1. **Ne pas appliquer de benchmarks B2C** (taux de conversion, abandon panier) à ce dataset.
2. **Segmenter par `customer_id_hash`** pour identifier les comptes les plus actifs (requête SQL custom sur `sales_clean`).
3. **Agréger au niveau facture** (`invoice_no`) avant d'analyser la taille des commandes.
4. **Mentionner le grain** dans tout rapport : une ligne ≠ une commande, c'est un article dans une commande.

## Colonnes utiles dans `sales_clean`

| Colonne | Usage B2B |
|---------|-----------|
| `invoice_no` | Identifiant de commande / bon de commande |
| `customer_id_hash` | Compte client anonymisé |
| `quantity` | Volume d'achat (toujours > 0 après nettoyage) |
| `country` | Marché du compte client |
| `sale_month` | Rythme de commande mensuel |
