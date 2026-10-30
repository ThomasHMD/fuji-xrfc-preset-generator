# Écrire une recette dans C1 à C7 (macOS, X-T4)

> ⚠️ **Cet outil écrit dans votre boîtier.** Il a été écrit pour mon X-T4 et vérifié sur lui seul : les sept emplacements C1 à C7, écrits le 30/10/2026 et relus par USB après extinction et rallumage (16 ou 17 réglages par emplacement, 0 écart), firmware 2.12. Il est fourni tel quel, **sans aucune garantie**. Avant tout essai : une sauvegarde complète des réglages avec l'application officielle de Fujifilm, un seul emplacement à la fois, et une vérification dans le menu après chaque écriture.

## Ce qu'il faut

- Un Mac, avec les outils en ligne de commande d'Apple (`xcode-select --install`) pour avoir `swiftc`. Rien d'autre à installer : l'outil passe par ImageCaptureCore, la bibliothèque de macOS.
- Un **X-T4**. L'outil refuse d'écrire sur un autre modèle. Le firmware testé est le 2.12 (le dernier).
- Un câble USB. Sur le seul Mac essayé, le boîtier n'apparaissait pas branché sur les ports de l'ordinateur et apparaissait aussitôt par un hub USB (celui de l'écran) : si rien ne répond, essayez un hub.
- Le boîtier en mode **USB RAW CONV./BACKUP RESTORE** : menu RÉGLAGES > PARAM.CONNEXION > MODE DE CONNEXION (dans le menu français : **REST RETR/CONV RAW USB**).
- Photos et Transfert d'images fermés (dans Transfert d'images, réglez la connexion du boîtier sur « Aucune application ») : un seul programme à la fois peut parler au boîtier.

## Pas à pas

```sh
# 1. compiler (une fois), dans un dossier de travail hors du dépôt
swiftc -O -swift-version 5 outils/x-t4/xt4_recettes.swift -o <dossier de travail>/xt4_recettes
cd <dossier de travail>

# 2. sans boîtier : voir ce qui serait écrit pour une recette
./xt4_recettes traduire "<dépôt>/presets/recettes-2026/TH Tri-X 400.FP1"

# 3. boîtier branché : lecture seule, l'outil dit si tout est en place
./xt4_recettes sonde

# 4. copie de la sauvegarde des réglages du boîtier (lecture seule)
./xt4_recettes sauvegarder sauvegarde-avant.bin

# 5. simulation : rien n'est envoyé
./xt4_recettes ecrire 1 "<dépôt>/presets/recettes-2026/TH Tri-X 400.FP1"

# 6. écriture réelle d'UN emplacement (ici C1), puis relecture et comparaison
./xt4_recettes ecrire 1 "<dépôt>/presets/recettes-2026/TH Tri-X 400.FP1" --vraiment --sauvegarde sauvegarde-avant.bin
```

7. **Éteignez le boîtier avec son interrupteur avant de le débrancher.** Il n'enregistre ses réglages perso qu'à l'extinction : sur mon X-T4, la sauvegarde ne changeait qu'après extinction et rallumage.
8. Rallumez, rebranchez et relisez l'emplacement contre sa recette : `./xt4_recettes relire 1 "<dépôt>/presets/recettes-2026/TH Tri-X 400.FP1"`. Ouvrez aussi l'emplacement dans le menu et comparez.

Recommencez de 5 à 8 pour chaque emplacement, un à la fois.

## Revenir en arrière

Avant d'écrire, l'outil relit l'ancien contenu de l'emplacement (nom et réglages) et le garde dans son dossier de sortie, dans un fichier `emplacement-N-avant.json`. Pour remettre l'emplacement tel qu'il était :

```sh
./xt4_recettes remettre 1 <dossier de sortie>/emplacement-1-avant.json            # simulation
./xt4_recettes remettre 1 <dossier de sortie>/emplacement-1-avant.json --vraiment
```

L'outil ne restaure **jamais** une sauvegarde complète du boîtier. Pour ça, passez par l'application officielle de Fujifilm (XApp ou TETHER APP), avec la sauvegarde faite avant le premier essai.

## Les garde-fous de l'outil

- `sonde`, `sauvegarder`, `lire` et `balayer` ne peuvent rien écrire : toute opération hors lecture est refusée par le programme.
- `ecrire` ne fait qu'une simulation sans `--vraiment`. Avec `--vraiment`, il refuse si le boîtier n'est pas un X-T4, s'il n'est pas en mode USB RAW CONV./BACKUP RESTORE, si le `.FP1` n'est pas pour un X-T4, ou sans `--sauvegarde <fichier>`.
- Il n'écrit que le sélecteur d'emplacement, le nom et les réglages de la recette : jamais l'état de prise de vue courant, jamais la taille ni la qualité d'image, jamais de firmware.
- Le fichier de sauvegarde contient **le numéro de série du boîtier en clair** : ne le partagez pas et ne le mettez jamais dans un dépôt. L'outil, lui, ne l'affiche jamais.

## Ce qu'il faut savoir

- **Ce que le X-T4 ne prend pas.** Cinq réglages de la recette n'existent pas sur le X-T4 testé et sont sautés : taille et qualité d'image, Smooth Skin, optimiseur de modulation, espace colorimétrique.
- **Le nom de l'emplacement** fait 25 caractères au plus : un nom plus long est tronqué (onze des 161 recettes de 2022 sont dans ce cas). Les recettes mesurées tiennent toutes dans cette limite.
- **Les recettes de 2022 passent toutes** (161 sur 161 se traduisent), mais 68 d'entre elles portent une valeur que X RAW Studio 1.28 n'écrit pas et que l'outil interprète, avec un avertissement : plage dynamique `AUTO` (48 fichiers), `WEAK` ou `STRONG` (7, lus comme la priorité D-Range faible ou forte), simulation `NEGA` (16, lue Pro Neg. Std) et `AcrosY` (3, lue Acros + filtre jaune). Pour celles-là, vérifiez l'emplacement dans le menu après l'écriture.
- **Le grain « off »** s'écrit 1 et le boîtier relit 6 : c'est normal.
- **Le boîtier refuse certaines valeurs selon l'état** : la température en Kelvin hors balance « Température », les réglages de virage hors simulation monochrome. L'outil les signale et continue, comme X RAW Studio.
- **Pourquoi d'autres outils n'y arrivent pas sur le X-T4.** Le X-T4 ne déclare pas ces réglages, mais il les lit et les écrit. Les projets qui se fient à cette déclaration (FilmKit, grawji, FujiSync) renoncent donc sur ce boîtier.
- **Autres boîtiers.** Des rapports publics disent que l'écriture des emplacements marche sur X-H2, X-T5, X100VI, X-E5, X-S20 et X100V, et qu'elle échoue sur X-T3, X-T30 et X-Pro3. Je ne l'ai vérifiée que sur le X-T4, et l'outil n'écrit que sur lui.

## Toutes les commandes

| Commande | Ce qu'elle fait |
|---|---|
| `xt4_recettes traduire <fichier.FP1 \| dossier>` | sans boîtier : montre les écritures qui seraient faites, et les avertissements |
| `xt4_recettes sonde` | lecture seule : session, modèle, mode USB, présence des réglages perso |
| `xt4_recettes sauvegarder <fichier>` | lecture seule : copie la sauvegarde des réglages du boîtier |
| `xt4_recettes ecrire <1-7> <fichier.FP1>` | simulation, rien n'est envoyé |
| `xt4_recettes ecrire <1-7> <fichier.FP1> --vraiment --sauvegarde <fichier>` | écrit un emplacement, relit, compare |
| `xt4_recettes relire <1-7> <fichier.FP1> […]` | relit chaque emplacement contre son `.FP1`, par exemple après extinction et rallumage ; seul le sélecteur d'emplacement est écrit, puis remis |
| `xt4_recettes remettre <1-7> <emplacement-N-avant.json> [--vraiment]` | remet l'emplacement tel qu'il était avant `ecrire` |
| `xt4_recettes lire <code> […]`, `xt4_recettes balayer` | lecture seule de réglages du boîtier (dépannage) |
| `xt4_recettes convertir <fichier.RAF> <sortie.jpg> [--profil <d185.bin>]` | le boîtier développe un RAF du X-T4 et rend un JPEG, sans rien écrire dans ses réglages |
| `xt4_recettes autotest` | sans boîtier : contrôle des encodages |
| `python3 outils/x-t4/xt4_d185.py lire <d185.bin>` / `modifier …` | lit ou modifie le profil de conversion (`0xD185`) utilisé par `convertir` |
