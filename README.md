# fuji-xrfc-preset-generator

Des recettes de simulation de film pour les boîtiers Fujifilm, au format **`.FP1`** de **Fujifilm X RAW Studio (XRFC)**, et, depuis 2026, un outil qui les écrit **directement dans les réglages perso C1 à C7 d'un X-T4**, sans X RAW Studio.

Le pack s'est construit en trois temps :

- **V1 (janvier 2022)** : un tableur Excel et sa macro VBA qui fabriquent les `.FP1` en lot, et 161 recettes communautaires (FujiXWeekly, Henri-Pierre Chavaz, le Discord « Team Fuji », mes propres réglages) déjà générées pour le X-T4 ;
- **V1.1** : le correctif de la balance des blancs en Kelvin ;
- **2026 (v2.0.0)** : 14 recettes « TH » **mesurées** sur le X-T4 (le boîtier développe lui-même mes RAF, et chaque réglage est comparé à une cible de film, zone par zone), et les outils pour macOS qui ont servi à les mesurer et qui les écrivent dans C1 à C7.

---

## Télécharger

### ➜ [**presets-fp1-x-t4.zip** - les 161 `.FP1` de 2022, les 14 recettes TH et mes 7 profils, pour X-T4](https://github.com/ThomasHMD/fuji-xrfc-preset-generator/releases/latest/download/presets-fp1-x-t4.zip)

### ➜ [**DemoPresetV1.1.xlsm** - le tableur et sa macro (dernière release)](https://github.com/ThomasHMD/fuji-xrfc-preset-generator/releases/latest/download/DemoPresetV1.1.xlsm)

Les outils de 2026 sont du code source, dans [`xt4/outils/`](xt4/outils/) : ils se compilent sur votre Mac (voir [§ Écrire une recette dans C1 à C7](#écrire-une-recette-dans-c1-à-c7-macos-x-t4)).

Pour un **autre boîtier** (X-T3, X-T2, X-H1, X100V, X-S10, X-Pro3, X-T5, GFX…) : voir [§ Adapter à un autre boîtier](#adapter-à-un-autre-boîtier).

Toutes les versions et leur changelog : [Releases](https://github.com/ThomasHMD/fuji-xrfc-preset-generator/releases).

---

## Ce que contient le pack

| Dossier | Ce que c'est | Depuis |
|---|---|---|
| [`V1/`](V1/) | `DemoPreset.xlsm` (le premier tableur, macro `GenererFP1`), `DemoPreset.xml` (un `.FP1` d'exemple, chaque champ commenté en français), `FP1/` (161 `.FP1` pour X-T4) | V1, janvier 2022 |
| [`V1.1/`](V1.1/) | `DemoPresetV1.1.xlsm` (le tableur corrigé, **à utiliser**), `FP1/` (les mêmes 161 recettes, régénérées : 14 fichiers changent, ceux qui ont une balance en Kelvin) | V1.1 |
| [`Les presets FP1 du discord/`](Les%20presets%20FP1%20du%20discord/) | le pack d'Henri-Pierre Chavaz décliné pour 14 boîtiers (171 `.FP1` chacun), et pour X-T4, X-T2, X-H1, X100V et X-S10 un dossier `Base` (pack de référence) et un dossier `Discord` (contributions des membres) | 2022 |
| [`xt4/recettes/`](xt4/recettes/) | les 14 recettes « TH » mesurées sur le X-T4, au format `.FP1`, et dans `emplacements/` mes sept profils C1 à C7, prêts à écrire | 2026 |
| [`xt4/outils/`](xt4/outils/) | l'outil qui écrit un `.FP1` dans C1 à C7 par USB (`xt4_recettes.swift`), la lecture du profil de conversion (`xt4_d185.py`), et la chaîne de mesure qui a produit les recettes TH et la doc | 2026 |
| [`docs/`](docs/) | [Le traitement des couleurs du X-T4, réglage par réglage](docs/traitement-couleur-x-t4.md) : ce que fait chaque réglage du boîtier, mesuré, avec ses figures | 2026 |

Les deux fichiers de la release reprennent ce contenu : `presets-fp1-x-t4.zip` (les 161 `.FP1` de `V1.1/FP1/`, les recettes TH de `xt4/recettes/` et les sept profils de `xt4/recettes/emplacements/`) et `DemoPresetV1.1.xlsm`.

### Comment le pack a évolué

1. **Janvier 2022, V1.** X RAW Studio sait développer un RAF avec le processeur du boîtier branché, mais chaque profil se règle à la main dans son interface. J'ai lu le format des `.FP1` (du XML), monté un tableur de 161 recettes et une macro qui écrit un `.FP1` par ligne. C'est ce que montre la vidéo.
2. **V1.1.** La V1 écrivait mal les balances en Kelvin (`5300K` dans la colonne donnait `<WhiteBalance>5300K</WhiteBalance>`). La V1.1 écrit `Temperature` et met la valeur dans `WBColorTemp`, comme X RAW Studio. Le zip V1.1 est en ligne sur le site depuis février 2024.
3. **Avril 2026, open source.** Le tableur, les 161 `.FP1` et les packs du Discord arrivent sur GitHub (release v1.1.0).
4. **2026, v2.0.0.** Deux nouveautés, toutes deux pour le X-T4 :
   - **des recettes mesurées** : au lieu de régler une recette à l'œil, je laisse le boîtier développer mes RAF avec des milliers de réglages candidats, et je garde celui qui colle le mieux à la cible du film ;
   - **l'écriture directe dans C1 à C7**, en ligne de commande, sans X RAW Studio.

---

## Mise à jour 2026 (v2.0.0)

### En bref

- **14 recettes TH** dans [`xt4/recettes/`](xt4/recettes/), une par film visé, notées contre mes 161 recettes de 2022. Mes sept emplacements C1 à C7 en gardent quatre, à côté de trois recettes de 2022 qui font mieux ; les autres s'échangent selon le voyage, la saison, le projet.
- **Un outil pour macOS**, `xt4_recettes`, qui lit un `.FP1` et l'écrit dans un emplacement C1 à C7 du X-T4, par USB, puis relit l'emplacement pour vérifier.
- **Ce que fait chaque réglage du boîtier, mesuré** : simulations de film, hautes lumières et ombres, couleur, Color Chrome, FX Blue, balance, filtres N&B, grain, avec des figures. [Le traitement des couleurs du X-T4, réglage par réglage](docs/traitement-couleur-x-t4.md).
- **La chaîne de mesure complète** (code source), pour savoir d'où viennent les chiffres et la rejouer.
- **Limites, à lire avant tout** : macOS seulement, X-T4 seulement, firmware 2.12 seul testé, mode USB « RAW CONV./BACKUP RESTORE » obligatoire. Écrire dans le boîtier n'est pas sans risque : voir [§ Avertissement](#avertissement).

### Les recettes TH

Quatorze recettes, une par film visé. Pour chacune : l'écart à sa cible sur 20 photos qui n'ont servi ni à la chercher ni à la choisir, et la meilleure de mes 161 recettes de 2022 sur les mêmes photos.

| Recette (fichier `.FP1`) | Ce qu'elle vise | Réglage à faire en plus | Écart à la cible (ΔE2000, ou \|ΔL\*\| en noir et blanc), médiane (p90) | Meilleure de mes 161 recettes de 2022, sur les mêmes photos | Verdict |
|---|---|---|---|---|---|
| `TH Tri-X 400` | Kodak Tri-X 400, d'après un preset acheté que j'aimais beaucoup | aucun | 2,6 (11,3) | RR Acros Push Process 2,1 (12,1) | Aucun gain solide |
| `TH HP5 Plus +2-3 IL` | Ilford HP5 Plus, telle que je l'aime sur mes scans | exposer **+2/3** IL | 4,5 (16,9) | EM Acros exposée +1 IL 8,3 (20,5) | Gain confirmé |
| `TH FP4 Plus` | Ilford FP4 Plus (fiche Ilford, tirage sur papier grade 2) | aucun | 6,1 (20,1) | RR Dramatic Monochrome 6,5 (22,6) | Gain probable |
| `TH Portra 400` | Kodak Portra 400, d'après un preset acheté que j'aimais beaucoup, rapproché de mes scans | aucun | 4,6 (10,6) | NZD Ektar 100 exposée +1/3 IL 2,9 (6,3) | Aucun gain solide |
| `TH Classic Chrome` | Classic Chrome, d'après la LUT officielle de Fujifilm | aucun | 3,4 (8,3) | DC Classic Chrome I 3,1 (6,2) | Aucun gain solide |
| `TH Classic Chrome 1.15` | la même LUT, saturée de 15 % | aucun | 3,7 (9,2) | DC Classic Chrome I 3,2 (6,5) | Aucun gain solide |
| `TH Classic Chrome 1.3` | la même LUT, saturée de 30 % | aucun | 4,1 (10,4) | DC Classic Chrome I 4,0 (7,2) | Aucun gain solide |
| `TH CC 1.3 contraste` | la même LUT, saturée de 30 %, contraste +15 % au gris | aucun | 4,4 (10,4) | DC Classic Chrome II 4,0 (7,4) | Aucun gain solide |
| `TH Provia 100F` | Fujichrome Provia 100F, simulée par spektrafilm | aucun | 3,5 (7,0) | DC Classic Chrome II 4,0 (9,0) | Gain confirmé |
| `TH Ektar 100` | Kodak Ektar 100, simulée par spektrafilm | aucun | 3,9 (7,8) | DC Classic Chrome II 4,4 (9,3) | Gain probable |
| `TH Pro 400H` | Fujicolor Pro 400H, d'après un preset acheté que j'aimais beaucoup | aucun | 6,8 (12,3) | MT Eterna exposée +1/3 IL 5,5 (11,7) | Aucun gain solide |
| `TH Velvia 100` | Fujichrome Velvia 100, simulée par spektrafilm | aucun | 4,0 (9,5) | NZD Ektar 100 4,8 (10,2) | Gain confirmé |
| `TH Ektachrome E100` | une simulation spektrafilm de l'Ektachrome E100, elle-même un peu trop chaude pour ce film froid et neutre : la recette colle à la simulation, pas forcément au film | aucun | 4,3 (8,0) | DC Classic Chrome II 3,7 (8,6) | Aucun gain solide |
| `TH Kodachrome 64` | Kodachrome 64, simulée par spektrafilm | aucun | 4,0 (8,6) | MT Provia 4,7 (8,0) | Gain probable |

**Verdict.** « Gain confirmé » : la recette TH fait mieux sur les deux moitiés de la recherche et sur les photos nouvelles. « Gain probable » : mieux sur les photos nouvelles, mais partagé sur les moitiés, ou vu sur les photos nouvelles sans contrôle croisé des moitiés. « Aucun gain solide » : elle perd sur les photos nouvelles, ou ne gagne que d'un souffle quand une autre recette de 2022 fait nettement mieux.

**Mes sept emplacements, C1 à C7.** Choisis après comparaison sur mes photos, écrits sur mon X-T4, tous en DR100 : quatre recettes TH et trois recettes de 2022.

| Emplacement | Nom sur le boîtier | Recette | Écart sur les 20 photos, médiane (p90) | Réglage à faire en plus |
|---|---|---|---|---|
| C1 | Classic Chrome punchy | `DC Classic Chrome II` (2022) | 4,0 (7,4) | aucun |
| C2 | Portra 400 +1/3 | `NZD Ektar 100` (2022), en DR100 au lieu de DR Auto | 2,9 (6,3) | exposer **+1/3** IL |
| C3 | Provia 100F | `TH Provia 100F` | 3,5 (7,0) | aucun |
| C4 | Ektar 100 | `TH Ektar 100` | 3,9 (7,8) | aucun |
| C5 | Velvia 100 | `TH Velvia 100` | 4,0 (9,5) | aucun |
| C6 | Tri-X 400 | `RR Acros Push Process` (2022), en DR100 au lieu de DR200 | 2,1 (12,1) | aucun |
| C7 | HP5 Plus +2/3 | `TH HP5 Plus +2-3 IL` | 4,5 (16,9) | exposer **+2/3** IL |

Chaque écart est mesuré contre la cible du film nommé ; pour C1, contre celle de `TH CC 1.3 contraste`. Les sept profils sont prêts, à ces noms et déjà en DR100, dans [`xt4/recettes/emplacements/`](xt4/recettes/emplacements/) (`C1 Classic Chrome punchy.FP1`, `C2 Portra 400 +1-3 IL.FP1`…) et dans le dossier `C1-C7/` du zip. Hors emplacements, je garde sous la main `MT Eterna` exposée +1/3 IL pour la Pro 400H, `TH Kodachrome 64`, `DC Classic Chrome I` et `TH FP4 Plus`. Pour l'Ektachrome, `DC Classic Chrome II` est seulement la plus proche de ma cible, et cette cible est douteuse (voir la méthode, plus bas).

**Comment lire les écarts.** Le ΔE2000 mesure l'écart entre deux couleurs tel que l'œil le perçoit : sous 1, on ne voit pas de différence ; entre 2 et 3, il faut mettre les deux images côte à côte ; au-delà de 5, ça saute aux yeux. En noir et blanc, seule la clarté compte : l'écart est |ΔL\*|, sur la même échelle. La médiane dit l'écart typique, le p90 l'écart des zones difficiles (90 % des zones font mieux). Les chiffres du tableau sont mesurés sur 20 photos qui n'ont servi ni à chercher ni à choisir les recettes (24 prises, dont 4 écartées faute de zones assez uniformes). Une recette s'inspire de sa cible, elle ne la copie pas : l'écart à la cible est du même ordre que l'écart entre deux recettes ([ordres de grandeur](docs/traitement-couleur-x-t4.md)).

**« Réglage à faire en plus ».** Les réglages perso C1 à C7 ne gardent pas la correction d'exposition. Quand une recette en demande une, c'est à vous de la régler à la prise de vue (molette de correction). Son nom le rappelle : le fichier `TH HP5 Plus +2-3 IL.FP1` s'affiche `TH HP5 Plus +2/3`, et mes emplacements C2 et C7 s'appellent `Portra 400 +1/3` et `HP5 Plus +2/3`.

**Le réglage de chaque recette**, pour ceux qui veulent le saisir à la main dans le menu (sur un X-T4, ou à vos risques sur un autre boîtier à capteur X-Trans IV : la mesure n'a été faite que sur le X-T4) :

| Recette | Simulation | Plage dyn. | Grain | Color Chrome / FX Blue | Balance (décalage R, B) | Hautes lumières | Ombres | Couleur | Netteté | Réduction du bruit | Clarté |
|---|---|---|---|---|---|---|---|---|---|---|---|
| TH Tri-X 400 | Acros | DR100 | fort, gros | off / off | Auto (R +1, B +6) | +3,5 | +2,5 | 0 | 0 | −4 | 0 |
| TH HP5 Plus +2/3 | Acros + G | DR100 | fort, gros | off / off | Auto (R +9, B +6) | +4 | +0,5 | 0 | 0 | −4 | 0 |
| TH FP4 Plus | Monochrome | DR100 | fort, petit | off / off | Auto (R +8, B 0) | +3 | +3 | 0 | 0 | −4 | 0 |
| TH Portra 400 | Astia | DR100 | faible, petit | off / faible | Auto (R +1, B −1) | +3 | −2 | +1 | 0 | −4 | 0 |
| TH Classic Chrome | Classic Chrome | DR100 | off | off / faible | Auto (R 0, B 0) | −1 | 0 | 0 | 0 | −4 | 0 |
| TH Classic Chrome 1.15 | Classic Chrome | DR100 | off | off / faible | Auto (R 0, B 0) | −1 | −0,5 | +2 | 0 | −4 | 0 |
| TH Classic Chrome 1.3 | Classic Chrome | DR100 | off | off / faible | Auto (R 0, B 0) | −1 | −0,5 | +4 | 0 | −4 | 0 |
| TH CC 1.3 contraste | Classic Chrome | DR100 | off | off / faible | Auto (R 0, B 0) | 0 | +0,5 | +4 | 0 | −4 | 0 |
| TH Provia 100F | Classic Chrome | DR100 | off | off / fort | Auto (R +1, B 0) | +1 | −1 | +1 | 0 | −4 | 0 |
| TH Ektar 100 | Classic Chrome | DR100 | off | fort / off | Auto (R 0, B +2) | 0 | −1 | +4 | 0 | −4 | 0 |
| TH Pro 400H | Classic Chrome | DR100 | faible, petit | off / off | Auto (R +2, B 0) | 0 | −2 | −3 | 0 | −4 | +4 |
| TH Velvia 100 | Provia | DR100 | off | off / fort | Auto (R +1, B 0) | +3 | 0 | +3 | 0 | −4 | 0 |
| TH Ektachrome E100 | Classic Chrome | DR100 | off | faible / fort | Auto (R 0, B −1) | 0 | −1 | +1 | 0 | −4 | 0 |
| TH Kodachrome 64 | Classic Chrome | DR100 | off | fort / faible | Auto (R +1, B +2) | −0,5 | 0 | +2 | 0 | −4 | 0 |


### Ce que fait chaque réglage du X-T4

Pour chercher les recettes, le boîtier a développé les mêmes RAF des milliers de fois, un seul réglage changé à la fois : 21 658 développements de 16 photos. Ces rendus disent aussi, chiffres à l'appui, ce que fait chaque réglage du menu. Quelques résultats :

- **Hautes lumières et Ombres ne touchent pas les tons moyens.** La première agit au-dessus de L\* 60 environ, la seconde sous L\* 45 ; entre les deux, rien ne bouge. Seule l'exposition déplace les tons moyens.
- **Couleur multiplie la saturation**, d'environ 5 % par cran, partout pareil (× 1,20 à +4).
- **Color Chrome Effect assombrit les couleurs saturées sans les saturer**, dans les ombres et les tons moyens seulement. **FX Blue** ne fonce que les bleus, jusqu'à −26 L\* sur un bleu très saturé.
- **En noir et blanc, le décalage de balance n'est pas un filtre** : il éclaircit ou fonce toute l'image, presque autant pour toutes les couleurs. Pour foncer un ciel, il faut le filtre jaune ou rouge.
- **Classic Chrome tourne les bleus vers le cyan** (−13°), d'où ses ciels ; **Classic Neg.** éclaircit l'image de 1/3 à 1/2 IL et fait tourner trois familles de couleur à la fois.

Tout le détail, avec les tableaux et une figure par réglage : [Le traitement des couleurs du X-T4, réglage par réglage](docs/traitement-couleur-x-t4.md).

---

## Écrire une recette dans C1 à C7 (macOS, X-T4)

> ⚠️ **Cet outil écrit dans votre boîtier.** Il a été écrit pour mon X-T4 et vérifié sur lui seul : les sept emplacements C1 à C7, écrits le 30/10/2026 et relus par USB après extinction et rallumage (16 ou 17 réglages par emplacement, 0 écart), firmware 2.12. Il est fourni tel quel, **sans aucune garantie**. Avant tout essai : une sauvegarde complète des réglages avec l'application officielle de Fujifilm, un seul emplacement à la fois, et une vérification dans le menu après chaque écriture.

### Ce qu'il faut

- Un Mac, avec les outils en ligne de commande d'Apple (`xcode-select --install`) pour avoir `swiftc`. Rien d'autre à installer : l'outil passe par ImageCaptureCore, la bibliothèque de macOS.
- Un **X-T4**. L'outil refuse d'écrire sur un autre modèle. Le firmware testé est le 2.12 (le dernier).
- Un câble USB. Sur le seul Mac essayé, le boîtier n'apparaissait pas branché sur les ports de l'ordinateur et apparaissait aussitôt par un hub USB (celui de l'écran) : si rien ne répond, essayez un hub.
- Le boîtier en mode **USB RAW CONV./BACKUP RESTORE** : menu RÉGLAGES > PARAM.CONNEXION > MODE DE CONNEXION (dans le menu français : **REST RETR/CONV RAW USB**).
- Photos et Transfert d'images fermés (dans Transfert d'images, réglez la connexion du boîtier sur « Aucune application ») : un seul programme à la fois peut parler au boîtier.

### Pas à pas

```sh
# 1. compiler (une fois), dans un dossier de travail hors du dépôt
swiftc -O -swift-version 5 xt4/outils/xt4_recettes.swift -o <dossier de travail>/xt4_recettes
cd <dossier de travail>

# 2. sans boîtier : voir ce qui serait écrit pour une recette
./xt4_recettes traduire "<dépôt>/xt4/recettes/TH Tri-X 400.FP1"

# 3. boîtier branché : lecture seule, l'outil dit si tout est en place
./xt4_recettes sonde

# 4. copie de la sauvegarde des réglages du boîtier (lecture seule)
./xt4_recettes sauvegarder sauvegarde-avant.bin

# 5. simulation : rien n'est envoyé
./xt4_recettes ecrire 1 "<dépôt>/xt4/recettes/TH Tri-X 400.FP1"

# 6. écriture réelle d'UN emplacement (ici C1), puis relecture et comparaison
./xt4_recettes ecrire 1 "<dépôt>/xt4/recettes/TH Tri-X 400.FP1" --vraiment --sauvegarde sauvegarde-avant.bin
```

7. **Éteignez le boîtier avec son interrupteur avant de le débrancher.** Il n'enregistre ses réglages perso qu'à l'extinction : sur mon X-T4, la sauvegarde ne changeait qu'après extinction et rallumage.
8. Rallumez, rebranchez et relisez l'emplacement contre sa recette : `./xt4_recettes relire 1 "<dépôt>/xt4/recettes/TH Tri-X 400.FP1"`. Ouvrez aussi l'emplacement dans le menu et comparez.

Recommencez de 5 à 8 pour chaque emplacement, un à la fois.

### Revenir en arrière

Avant d'écrire, l'outil relit l'ancien contenu de l'emplacement (nom et réglages) et le garde dans son dossier de sortie, dans un fichier `emplacement-N-avant.json`. Pour remettre l'emplacement tel qu'il était :

```sh
./xt4_recettes remettre 1 <dossier de sortie>/emplacement-1-avant.json            # simulation
./xt4_recettes remettre 1 <dossier de sortie>/emplacement-1-avant.json --vraiment
```

L'outil ne restaure **jamais** une sauvegarde complète du boîtier. Pour ça, passez par l'application officielle de Fujifilm (XApp ou TETHER APP), avec la sauvegarde faite avant le premier essai.

### Les garde-fous de l'outil

- `sonde`, `sauvegarder`, `lire` et `balayer` ne peuvent rien écrire : toute opération hors lecture est refusée par le programme.
- `ecrire` ne fait qu'une simulation sans `--vraiment`. Avec `--vraiment`, il refuse si le boîtier n'est pas un X-T4, s'il n'est pas en mode USB RAW CONV./BACKUP RESTORE, si le `.FP1` n'est pas pour un X-T4, ou sans `--sauvegarde <fichier>`.
- Il n'écrit que le sélecteur d'emplacement, le nom et les réglages de la recette : jamais l'état de prise de vue courant, jamais la taille ni la qualité d'image, jamais de firmware.
- Le fichier de sauvegarde contient **le numéro de série du boîtier en clair** : ne le partagez pas et ne le mettez jamais dans un dépôt. L'outil, lui, ne l'affiche jamais.

### Ce qu'il faut savoir

- **Ce que le X-T4 ne prend pas.** Cinq réglages de la recette n'existent pas sur le X-T4 testé et sont sautés : taille et qualité d'image, Smooth Skin, optimiseur de modulation, espace colorimétrique.
- **Le nom de l'emplacement** fait 25 caractères au plus : un nom plus long est tronqué (onze des 161 recettes de 2022 sont dans ce cas). Les recettes TH tiennent toutes dans cette limite.
- **Les recettes de 2022 passent toutes** (161 sur 161 se traduisent), mais 68 d'entre elles portent une valeur que X RAW Studio 1.28 n'écrit pas et que l'outil interprète, avec un avertissement : plage dynamique `AUTO` (48 fichiers), `WEAK` ou `STRONG` (7, lus comme la priorité D-Range faible ou forte), simulation `NEGA` (16, lue Pro Neg. Std) et `AcrosY` (3, lue Acros + filtre jaune). Pour celles-là, vérifiez l'emplacement dans le menu après l'écriture.
- **Le grain « off »** s'écrit 1 et le boîtier relit 6 : c'est normal.
- **Le boîtier refuse certaines valeurs selon l'état** : la température en Kelvin hors balance « Température », les réglages de virage hors simulation monochrome. L'outil les signale et continue, comme X RAW Studio.
- **Pourquoi d'autres outils n'y arrivent pas sur le X-T4.** Le X-T4 ne déclare pas ces réglages, mais il les lit et les écrit. Les projets qui se fient à cette déclaration (FilmKit, grawji, FujiSync) renoncent donc sur ce boîtier.
- **Autres boîtiers.** Des rapports publics disent que l'écriture des emplacements marche sur X-H2, X-T5, X100VI, X-E5, X-S20 et X100V, et qu'elle échoue sur X-T3, X-T30 et X-Pro3. Je ne l'ai vérifiée que sur le X-T4, et l'outil n'écrit que sur lui.

### Toutes les commandes

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
| `python3 xt4/outils/xt4_d185.py lire <d185.bin>` / `modifier …` | lit ou modifie le profil de conversion (`0xD185`) utilisé par `convertir` |

---

## La méthode en clair

Une recette mesurée, c'est un réglage du boîtier choisi parce qu'il colle le mieux, chiffres à l'appui, à ce qu'aurait donné un film. Six étapes :

1. **Le boîtier développe lui-même mes RAF.** En mode USB RAW CONV., on envoie au X-T4 un de ses RAF et un profil de conversion (simulation, tons, couleur, grain…) ; il rend un JPEG avec son propre processeur, en moins d'une seconde par rendu. Aucun réglage du boîtier n'est touché pendant la mesure. C'est le rôle de `xt4_banc.swift`.
2. **Une cible par film.** Pour chaque zone d'une photo, la cible est ce que le film aurait rendu de la même scène. La scène est lue dans le RAW à travers une matrice de couleur ajustée sur les mires publiées par Imaging Resource pour le X-T3 et le X-T30, deux boîtiers au même capteur que le X-T4 (`xt4_scene.py`). Les cibles (`xt4_cibles.py`) viennent de sources différentes selon le film :
   - Tri-X 400, Portra 400 et Pro 400H : d'après un preset acheté que j'aimais beaucoup ; la Portra est rapprochée de mes propres scans ;
   - HP5 Plus : la tonalité de mes scans de HP5 ;
   - FP4 Plus : les fiches techniques d'Ilford, tirage sur papier grade 2 ;
   - Classic Chrome : la LUT officielle de Fujifilm, puis un choix de goût, plus de couleur et plus de punch ;
   - Provia 100F, Ektar 100, Velvia 100, Ektachrome E100, Kodachrome 64 : simulés par [spektrafilm](https://github.com/andreavolpato/spektrafilm) (film modeling powered by spektrafilm). Chaque cible passe un contrôle de vraisemblance (le gris et les neutres doivent tomber où le film les met). Celle de l'Ektachrome le rate : le film est froid et neutre, la simulation sort un peu chaude (gris à b\* +2,0, contre +0,2 pour la Provia). Pour cette recette, l'écart dit donc à quel point elle colle à la simulation, pas au film.
3. **On compare zone par zone.** Les zones sont des carrés de 16 × 16 pixels, uniformes et non écrêtés, jusqu'à 1 000 par photo. Écart : ΔE2000 en couleur, |ΔL\*| en noir et blanc. On garde la médiane et le p90, chaque photo pesant autant.
4. **On cherche.** Grille grossière (simulations, tons), puis on ajuste un réglage à la fois (tons au demi-cran, décalages de balance, couleur, Color Chrome…). Le boîtier rend chaque candidat : près de 26 000 rendus en tout.
5. **On vérifie que ça tient sur des photos nouvelles.** Les 16 photos de la recherche sont coupées en deux moitiés : la recette cherchée sur l'une est notée sur l'autre, et inversement. Le verdict final se fait sur 24 autres photos qui n'ont jamais servi (20 notées : les 4 autres n'ont pas assez de zones uniformes), contre mes 161 recettes de 2022 rendues sur les mêmes photos. Une première passe m'a appris pourquoi : en noir et blanc, une recherche sur 8 photos faisait moins bien, sur les 8 autres, que des recettes existantes.
6. **Le grain se choisit à part**, en comparant le grain du boîtier à la granularité publiée du film.

### Ce que le boîtier ne sait pas faire

La mesure dit aussi où le X-T4 plafonne, quelle que soit la recette :

- **Pas de vraie courbe de tons.** Le réglage des hautes lumières n'agit qu'au-dessus de L\* 60 environ, celui des ombres qu'en dessous de L\* 45, de −2 à +4 par demi-cran. Rien ne touche les tons moyens.
- **Pas de mélangeur de canaux en noir et blanc.** Les films noir et blanc voient beaucoup de bleu ; le boîtier fait son gris par un mélange fixe que ses filtres ne déplacent que vers le rouge ou le vert. Résultat : les jaunes ne se placent pas où l'on veut. En HP5 et en FP4, ils sortent trop clairs (+13 et +17 L\* en médiane, sur les photos jamais vues) ; en Tri-X, trop sombres (−9 L\*), comme avec la meilleure de mes recettes de 2022.
- **Un grain plus fin que celui de la Tri-X.** Le grain fort et gros du boîtier reste environ 2,5 fois plus faible, à l'échelle d'un tirage.
- **La correction d'exposition n'est pas gardée** par les réglages perso : d'où la colonne « Réglage à faire en plus ».
- **La plage dynamique se choisit à la prise de vue.** Un RAF se développe à sa DR de prise de vue ou en dessous ; au-dessus, l'image vire au vert. Les recettes TH restent en DR100 : aucune DR plus haute n'a gagné assez (règle fixée d'avance : 0,3 de gain moyen, sur 2 scènes sur 3).
- **La balance en Kelvin n'aide pas le noir et blanc** : elle agit comme une exposition, pas comme un filtre. Dans le duel (Tri-X, HP5, FP4, de 3 200 à 6 500 K), aucune température ne bat la balance Auto avec décalages R / B : toutes les recettes TH restent en Auto.

### Rejouer la mesure

La chaîne est dans [`xt4/outils/`](xt4/outils/) :

| Outil | Rôle |
|---|---|
| `xt4_banc.swift` | le banc : envoie un RAF au boîtier, puis des profils de conversion, et récupère chaque JPEG |
| `xt4_d185.py` | lit et modifie le profil de conversion `0xD185` |
| `xt4_scene.py` | la couleur de la scène estimée depuis le RAW |
| `xt4_cibles.py` | les cibles de film |
| `xt4_mesure.py` | la première passe : préparation des photos, blocs, échelle d'exposition, mesure, grain |
| `xt4_recherche_v2.py` | la recherche de la passe finale, le bilan, l'écriture des `.FP1` TH |
| `xt4_transfert.py` | le pré-tri : chaque proposition est d'abord rendue sur 3 photos, son rendu sur les autres est prédit, et seules les 2 meilleures sont rendues partout (environ 7 fois moins de conversions ; les décisions et les chiffres publiés viennent toujours de rendus réels) |
| `xt4_validation.py` | contrôle du banc, plage dynamique, verdict sur les photos jamais vues |
| `xt4_leviers.py` | l'effet de chaque réglage caché du profil de conversion |
| `xt4_effets.py` | l'effet de chaque réglage du menu, mesuré sur les rendus déjà faits (chiffres de la [doc](docs/traitement-couleur-x-t4.md)) |
| `xt4_illustrations.py` | les figures de la doc : le boîtier rend des photos sans personne, un réglage à la fois |

Pour la rejouer, il faut :

- un X-T4 et vos propres RAF du X-T4 (le boîtier ne développe que les RAF de son modèle) ;
- Python 3 et les paquets de [`xt4/outils/requirements.txt`](xt4/outils/requirements.txt), plus [ExifTool](https://exiftool.org/) ;
- les modules du D750 publiés dans mon dépôt [retro-ingenierie-boitiers](https://github.com/ThomasHMD/retro-ingenierie-boitiers) (`d750/outils/`) : clonez ce dépôt, puis donnez son dossier aux outils par la variable `XT4_RIB` (par exemple `export XT4_RIB=~/retro-ingenierie-boitiers`) ; ces modules restent sous la licence de leur dépôt, **CC BY-NC-SA 4.0** ; le code de `xt4/outils/` les importe sans en copier une ligne ;
- pour la cible Classic Chrome, la LUT F-Log2 de Fujifilm, à télécharger [chez Fujifilm](https://www.fujifilm-x.com/global/support/download/lut/) ;
- pour Provia, Ektar, Velvia, Ektachrome et Kodachrome, les tables fabriquées avec spektrafilm, à faire chez vous, dans le dossier donné par `D750_SPEKTRAFILM` ;
- un dossier de travail pour les rendus du boîtier et le cache, donné par `XT4_CHANTIER` (par défaut, `xt4-mesure` dans le dossier temporaire du système) ;
- pour la matrice de la scène, rien : ses coefficients sont dans `xt4_scene.py` (les RAF d'Imaging Resource ne servent qu'à la refaire) ;
- les cibles Tri-X, Portra et Pro 400H ne sont pas reproductibles avec ce dépôt : elles viennent d'un preset acheté, dont aucun fichier ni aucune table n'est publié ici.

---

## Vidéo de présentation

📺 **[160+ presets directement dans votre Fujifilm !](https://www.youtube.com/watch?v=j8YM1vs0g2Y)** (janvier 2022, 21 min) : présentation du projet, démonstration sur X-T4, le tableur, la macro et la procédure d'import dans X RAW Studio.

La vidéo date de 2022 : elle montre la voie X RAW Studio, toujours valable sur tous les boîtiers. La partie 2026 (recettes mesurées, écriture en ligne de commande) n'y est pas ; elle est dans ce README et sur la page [Presets Fujifilm](https://thomashammoudi.com/presets-fujifilm/#maj-2026) du Blog.

## Pourquoi

Fujifilm X RAW Studio n'a aucune fonction d'**import en masse** : chaque profil se règle à la main dans son interface et s'enregistre un par un. Il sait copier un profil vers un réglage perso du boîtier (CUSTOM SETTING, depuis sa version 1.8.0 d'après les notes de version de Fujifilm), mais un seul à la fois, toujours depuis son interface. Ce projet permet de :

1. décrire les **161 recettes communautaires** (FujiXWeekly, blog d'Henri-Pierre Chavaz, Discord « Team Fuji », contributions perso) dans un tableur lisible,
2. les **générer en lot** comme fichiers `.FP1` (XML XRFC) avec une macro VBA,
3. les **déposer dans XRFC** pour développer les RAF avec un choix massif de rendus,
4. depuis 2026, sur un X-T4 et un Mac, les **écrire directement dans C1 à C7** en ligne de commande, et utiliser des recettes **mesurées** plutôt que réglées à l'œil.

Historique : projet démarré en janvier 2022, [documenté publiquement](docs/documentation-v1.md), avec une communauté d'échange de `.FP1` par boîtier sur Discord.

## Arborescence

```
fuji-xrfc-preset-generator/
├── README.md
├── LICENSE                        # CC BY-NC 4.0 : tout le dépôt, code compris
├── LICENCES-TIERS.md              # sources tierces, leurs licences et les mentions dues
├── docs/
│   ├── traitement-couleur-x-t4.md # ce que fait chaque réglage du X-T4, mesuré
│   └── figures/traitement-couleur/ # figures de la doc (JPEG, 2 000 px de large au plus)
├── assets/social-preview.png
├── V1/
│   ├── DemoPreset.xlsm            # Générateur v1 - macro VBA GenererFP1
│   ├── DemoPreset.xml             # Exemple annoté du format de sortie
│   └── FP1/                       # 161 .FP1 générés (X-T4)
├── V1.1/
│   ├── DemoPresetV1.1.xlsm        # Générateur v1.1 (fix Temperature WB)
│   └── FP1/                       # 161 .FP1 générés (X-T4)
├── Les presets FP1 du discord/
│   ├── Règles de nommage.txt      # Convention communautaire
│   ├── Henri-Pierre Chavaz - FUJI X RAW STUDIO PRESETS (04-02-2022)/
│   │   └── {GFX 100,GFX 50R,GFX 50S,X Pro 2,X Pro 3,X-E3,X-H1,X-T2,
│   │        X-T20,X-T3,X-T30,X-T4,X100F,X100V}/…
│   └── X-T4, X-T2, X-H1, X100V, X-S10/{Base,Discord}
│                                  # Base = pack de référence,
│                                  # Discord = contributions persos
└── xt4/                           # 2026, X-T4 seulement
    ├── recettes/                  # 14 recettes TH mesurées (.FP1)
    │   └── emplacements/          # mes 7 profils C1 à C7 (.FP1)
    └── outils/                    # code source
        ├── requirements.txt       # paquets Python de la chaîne de mesure
        ├── xt4_recettes.swift     # écrire un .FP1 dans C1-C7, sauvegarder, convertir
        ├── xt4_d185.py            # profil de conversion 0xD185
        ├── xt4_banc.swift         # banc de mesure (le boîtier développe les RAF)
        ├── xt4_scene.py           # couleur de la scène
        ├── xt4_cibles.py          # cibles de film
        ├── xt4_mesure.py          # première passe de mesure
        ├── xt4_recherche_v2.py    # passe finale, écriture des .FP1 TH
        ├── xt4_transfert.py       # prétri des candidats
        ├── xt4_validation.py      # validation hors échantillon
        ├── xt4_leviers.py         # réglages cachés du profil de conversion
        ├── xt4_effets.py          # effet de chaque réglage (chiffres de la doc)
        └── xt4_illustrations.py   # figures de la doc
```

## Comment ça marche

La voie de 2022, pour tous les boîtiers, avec X RAW Studio :

```
  ┌─────────────────┐    VBA Sub        ┌───────────────┐
  │ DemoPreset.xlsm │ ────GenererFP1───► │ FP1/*.FP1     │
  │ 14 colonnes     │                    │ (XML XRFC)    │
  │ 161 lignes      │                    │ 1 fichier /   │
  └─────────────────┘                    │   ligne Excel │
                                         └───────┬───────┘
                                                 │ copier dans
                                                 ▼
                     ┌────────────────────────────────────────┐
                     │ ~/Library/Application Support/         │
                     │ com.fujifilm.denji/X RAW STUDIO/       │
                     │        (macOS)                         │
                     │                                        │
                     │ %AppData%/Local/com.fujifilm.denji/    │
                     │ X_RAW_STUDIO/       (Windows)          │
                     └────────────────────────────────────────┘
```

La voie de 2026, pour le X-T4, sans X RAW Studio :

```
  ┌──────────────────┐   xt4_recettes ecrire N   ┌──────────────────────┐
  │ un .FP1          │ ───── USB (PTP) ────────► │ X-T4, emplacement CN │
  │ (TH, 2022, ou le │   relecture et contrôle   │ enregistré à         │
  │  vôtre)          │ ◄──────────────────────── │ l'extinction         │
  └──────────────────┘                           └──────────────────────┘
```

## Installation (utilisateur final)

### 1. Ouvrir le tableur et générer les presets

1. Télécharger `DemoPresetV1.1.xlsm` depuis la [dernière release](https://github.com/ThomasHMD/fuji-xrfc-preset-generator/releases/latest).
2. Ouvrir dans **Excel** (Microsoft Excel - LibreOffice Calc **n'exécute pas** la macro VBA utilisée). La macro est écrite pour Windows (chemins en `\`, `Scripting.FileSystemObject`) : sur Excel pour Mac, elle ne tournera probablement pas (non essayé). Sur Mac, prenez le zip des `.FP1` déjà générés.
3. Activer les macros à l'ouverture.
4. `Alt+F8` → `GenererFP1` → `Exécuter`.
5. Un dossier `FP1/` est créé à côté du `.xlsm`. Il contient les 161 `.FP1`.

> Raccourci : les 161 `.FP1` pour X-T4 et les recettes TH sont aussi dans la release (`presets-fp1-x-t4.zip`).

### 2. Importer dans Fuji X RAW Studio

**macOS** : coller les `.FP1` dans

```
~/Library/Application Support/com.fujifilm.denji/X RAW STUDIO/
```

**Windows** :

```
C:\Users\<votre-nom>\AppData\Local\com.fujifilm.denji\X_RAW_STUDIO\
```

Ces chemins ont été relevés en 2022 : ils peuvent changer selon la version de X RAW Studio et votre système.

### 3. Brancher un boîtier Fuji et développer

X RAW Studio exige qu'un **boîtier Fuji soit connecté en USB** (même modèle que celui indiqué par `device="..."` dans les `.FP1` : voir § Adapter), en mode USB RAW CONV./BACKUP RESTORE. Une fois connecté, les presets apparaissent dans le menu *Développer avec paramètres*.

### 4. Sans X RAW Studio (macOS, X-T4)

Voir [§ Écrire une recette dans C1 à C7](#écrire-une-recette-dans-c1-à-c7-macos-x-t4).

## Adapter à un autre boîtier

Tout est déjà décliné : [**presets-fp1-autres-boitiers.zip**](https://github.com/ThomasHMD/fuji-xrfc-preset-generator/releases/latest/download/presets-fp1-autres-boitiers.zip) contient les 182 `.FP1` pour X-T2, X-T3, X-T20, X-T30, X-T5, X-H1, X-S10, X-E3, X-Pro2, X-Pro3, X100F, X100V, GFX 50R, GFX 50S et GFX 100. Je n'ai testé que le X-T4.

Les `.FP1` du dossier principal sont générés pour **X-T4**. Pour un autre modèle, modifier trois attributs dans la macro (lignes `"        <PropertyGroup device="…"`  et `TetherRAWConditonCode`) :

| Boîtier | `device=` | `TetherRAWConditonCode` |
|---|---|---|
| X-T2 | `X-T2` | `X-T2_0100` |
| X-T3 | `X-T3` | `X-T3_0100` |
| X-T4 | `X-T4` | `X-T4_0100` |
| X-T5 | `X-T5` | `X-T5_0200` |
| X-T20 | `X-T20` | `X-T20_0100` |
| X-T30 | `X-T30` | `X-T30_0100` |
| X-H1 | `X-H1` | `X-H1_0100` |
| X-S10 | `X-S10` | `X-S10_0100` |
| X-E3 | `X-E3` | `X-E3_0100` |
| X-Pro2 | `X-Pro2` | `X-Pro2_0100` |
| X-Pro3 | `X-Pro3` | `X-Pro3_0100` |
| X100F | `X100F` | `X100F_0100` |
| X100V (FW 1.x) | `X100V` | `X100V_0100` |
| X100V (FW 2.x) | `X100V` | `X100V_0200` |
| GFX 50R | `GFX 50R` | `GFX 50R_0100` |
| GFX 50S | `GFX 50S` | `GFX 50S_0100` |
| GFX 100 | `GFX 100` | `GFX 100_0100` |

Le **numéro de série** (`<SerialNumber>`) n'a **pas** besoin d'être changé : XRFC ne le contrôle pas lors du chargement (vérifié par la communauté).

Certaines recettes utilisent des **simulations qui n'existent pas sur les anciens X-Trans** (`ClassicNEGA`, `Eterna`, `BleachBypass`, `AcrosR/G/Ye`, `ColorChromeBlue`, `ChromeEffect`). Le preset sera ignoré ou affichera une erreur *« preset non applicable »*. Voir la section [Autres corrections de la doc de la v1](docs/documentation-v1.md#autres-corrections).

Ce tableau vaut pour X RAW Studio. **L'écriture directe dans C1 à C7 (`xt4_recettes`) ne marche que sur le X-T4**, et les recettes TH n'ont été mesurées que sur lui.

## Format `.FP1` - résumé

Un `.FP1` est un XML UTF-8 décrivant tous les paramètres appliqués par le moteur JPEG Fuji à un RAF :

```xml
<?xml version="1.0" encoding="utf-8"?>
<ConversionProfile application="XRFC" version="1.12.0.0">
    <PropertyGroup device="X-T4" version="X-T4_0100" label="Classic neg">
        <FilmSimulation>ClassicNEGA</FilmSimulation>
        <GrainEffect>WEAK</GrainEffect>
        <GrainEffectSize>SMALL</GrainEffectSize>
        <DynamicRange>100</DynamicRange>
        <WhiteBalance>Auto</WhiteBalance>
        <HighlightTone>1</HighlightTone>
        <ShadowTone>1</ShadowTone>
        <Color>0</Color>
        <Sharpness>0</Sharpness>
        <NoisReduction>0</NoisReduction>
        <ExposureBias>0</ExposureBias>
        …
    </PropertyGroup>
</ConversionProfile>
```

Le numéro `version="1.12.0.0"` est celui du gabarit de 2022 ; la vidéo montre X RAW Studio les lire.

### Mapping colonnes Excel → tags XML

| Colonne | Tag | Valeurs possibles |
|---|---|---|
| `Label` | `label="…"` + nom de fichier | Texte libre (`/`→`_`, `*`→`_`). 25 caractères au plus pour un emplacement C1-C7 |
| `FilmSimulation` | `<FilmSimulation>` | `Provia`, `Velvia`, `Astia`, `Classic` (Classic Chrome), `ClassicNEGA`, `NEGAhi` (Pro Neg Hi), `Eterna`, `BleachBypass`, `Acros`, `AcrosR/G/Ye`, `BW`, `BR/G/Ye`, `Sepia`. Valeurs que X RAW Studio 1.28 n'écrit pas : `NEGA` (lu Pro Neg Std par `xt4_recettes`) et `AcrosY` (lu Acros + Ye), à contrôler dans le menu |
| `Grain` | `<GrainEffect>` + `<GrainEffectSize>` | `OFF` · `WEAK` · `STRONG` · `STRONG L` (→ STRONG/LARGE) |
| `CCFx/CCFxB` | `<ChromeEffect>` + `<ColorChromeBlue>` | `OFF` · `"A/B"` splitté sur `/`, ex. `WEAK/STRONG` |
| `WhiteBalance` | `<WhiteBalance>` + `<WBColorTemp>` | Preset (`Auto`, `Daylight`, `Shade`, `FLight1`, `FLight2`, `UWater`, `Auto_White`) **ou** température (`5300K`, `6700K`…). V1.1 : `*K` → `Temperature` + `WBColorTemp` |
| `WBShiftR` | `<WBShiftR>` | `-9..+9` |
| `WBShiftB` | `<WBShiftB>` | `-8..+9` |
| `DynamicRange` | `<DynamicRange>` | `100`, `200`, `400`. Valeurs que X RAW Studio 1.28 n'écrit pas : `AUTO` (écrit en automatique par `xt4_recettes`), `WEAK`, `STRONG` (lus comme la priorité D-Range faible ou forte), à contrôler dans le menu |
| `HighlightTone` | `<HighlightTone>` | `-2..+4` |
| `ShadowTone` | `<ShadowTone>` | `-2..+4` |
| `Color` | `<Color>` | `-4..+4` |
| `Sharpness` | `<Sharpness>` | `-4..+4` |
| `NoisReduction` | `<NoisReduction>` | `-4..+4` |
| `ExposureBias` | `<ExposureBias>` | Encodage Fuji : `0`, `P0P33` (+1/3 EV), `P0P67` (+2/3), `P1P00` (+1), `M0M33` (−1/3), `M1P00` (−1). Lettre 1 = signe des EV entiers (P/M), chiffre = EV, lettre 3 = signe des tiers, chiffres = 33/67. Non transmis dans C1-C7 (le boîtier ne garde pas l'exposition dans un réglage perso) |

Champs **figés en dur** dans la macro (pour évolution ultérieure) : `SerialNumber`, `Clarity`, `BlackImageTone`, `MonochromaticColor_RG`, `SmoothSkinEffect`, `ColorSpace`, `LensModulationOpt`, `HDR`, `DigitalTeleConv`, `WideDRange`.

À savoir :
- les recettes TH remplissent aussi `Clarity` ; aucune n'utilise le virage : `BlackImageTone` et `MonochromaticColor_RG` y restent à 0 ;
- deux fichiers de 2022, `RR Split-Tones B&W 1_2` et `2_2`, ont un `&` non échappé dans leur `label` : un lecteur XML strict refuse de les ouvrir (`xt4_recettes` les lit quand même).

## Différences entre V1 et V1.1

La V1.1 corrige la gestion de la **balance des blancs en température** :

```vb
' V1  →  <WhiteBalance>5300K</WhiteBalance>  <WBColorTemp>10000K</WBColorTemp>
' V1.1 → <WhiteBalance>Temperature</WhiteBalance>  <WBColorTemp>5300K</WBColorTemp>
```

Si la valeur de la colonne `WhiteBalance` se termine par `K`, V1.1 la bascule automatiquement dans `WBColorTemp` et met `Temperature` dans `WhiteBalance` (comportement conforme à XRFC). V1 écrit la valeur brute et force `10000K` en température.

> **Recommandation** : utiliser la V1.1.

## Pistes d'évolution

* **Écriture C1-C7 sur d'autres boîtiers** : l'outil ne vise que le X-T4. Les rapports publics sur X-H2, X-T5, X100VI, X-E5, X-S20 et X100V laissent penser que c'est faisable ailleurs ; il faudrait l'essayer boîtier par boîtier.
* **Hors macOS** : l'outil passe par ImageCaptureCore, propre au Mac. Un portage par libusb (Linux, Windows) reste à faire.
* **Multi-boîtier natif dans le tableur** : ajouter des colonnes `Device`, `Firmware`, `SerialNumber` pour générer tous les packs en une passe.
* **Exposer les champs figés** (Clarity, ColorSpace, BlackImageTone…) pour couvrir les presets B&W virés et les presets AdobeRGB.
* **Validateur `.FP1`** : pour le X-T4, `xt4_recettes traduire` et `autotest` en tiennent lieu ; un validateur pour tous les boîtiers (JSON Schema, Pydantic) reste à faire.
* **UI web** (Streamlit / SvelteKit) pour saisir un preset via formulaire avec preview.
* **Support X-T5 et boîtiers récents** : voir la [section X-T5 de la doc de la v1](docs/documentation-v1.md#pour-le-x-t5) pour un début d'intégration communautaire.
* **Simulations hors X RAW Studio** : [abpy/FujifilmCameraProfiles](https://github.com/abpy/FujifilmCameraProfiles) publie les simulations Fuji en profils `.dcp` et LUT `.cube` pour Lightroom / Camera Raw. Base possible pour décliner les recettes du tableur en presets Lightroom, sans boîtier branché.

Un membre du Discord a aussi publié [`FujiSimuRecipesGen`](https://github.com/mmoqui/FujiSimuRecipesGen), un générateur en Go (MIT).

Contributions bienvenues : ouvrir une issue ou une PR.

## Contribuer

Les presets sont nommés par **préfixe auteur** (convention FujiXWeekly / Team Fuji) :

| Préfixe | Auteur |
|---|---|
| `BLP` | Blaise Pauly |
| `BT` | Benjamin Turner |
| `DC` | Daniel Craig |
| `EM` | Eric Mercurio |
| `ER` | *(inconnu, ER)* |
| `GB` | *(inconnu, GB)* |
| `HF` | *(inconnu, HF)* |
| `HH` | *(inconnu, HH)* |
| `JC` | Jerome Courtial |
| `JP` | *(inconnu, JP)* |
| `KM` | Kevin Mullins |
| `LC` | *(inconnu, LC)* |
| `MT` | Michael Turner |
| `NZD` | *(NZD)* |
| `PE` | *(PE)* |
| `PLR` | *(inconnu, PLR)* |
| `PS` | *(PS)* |
| `RR` | Ritchie Roesch ([FujiXWeekly](https://fujixweekly.com/)) |
| `RS` | *(inconnu, RS)* |
| `SS` | *(inconnu, SS)* |
| `TH` | Thomas Hammoudi (recettes mesurées sur X-T4, 2026) |
| `VM` | *(VM)* |

Pour ajouter **vos propres presets**, utiliser `Prénom_Nom - Nom du preset.FP1` (cf. `Les presets FP1 du discord/Règles de nommage.txt`) et déposer dans le dossier de votre boîtier.

## Ressources externes

* 🎥 **Vidéo YouTube** - [160+ presets directement dans votre Fujifilm !](https://www.youtube.com/watch?v=j8YM1vs0g2Y) (Thomas Hammoudi, janvier 2022 ; la voie X RAW Studio)
* 📄 **Page du Blog** - [thomashammoudi.com/presets-fujifilm/](https://thomashammoudi.com/presets-fujifilm/) (avec la section « Mise à jour 2026 »)
* 📘 **Documentation de la v1** - [docs/documentation-v1.md](docs/documentation-v1.md) (import, conversion à la main, chemins de X RAW Studio)
* 📚 **FujiXWeekly** - [fujixweekly.com](https://fujixweekly.com/) - source de la plupart des presets `RR …`
* 📚 **Henri-Pierre Chavaz** - [hpchavaz-photography.blogspot.com/p/fujifims.html](https://hpchavaz-photography.blogspot.com/p/fujifims.html) - compilation par boîtier
* 🔧 **Rétro-ingénierie de boîtiers** - [ThomasHMD/retro-ingenierie-boitiers](https://github.com/ThomasHMD/retro-ingenierie-boitiers) - la même méthode de mesure sur des Nikon et un Pentax ; les outils du X-T4 s'appuient sur ses modules du D750

## Crédits

L'outil d'écriture et la chaîne de mesure s'appuient sur le travail de projets publics, cités dans chaque fichier et détaillés dans [`LICENCES-TIERS.md`](LICENCES-TIERS.md) :

- [FilmKit](https://github.com/eggricesoy/filmkit) (eggricesoy, MIT) : la séquence USB de conversion d'un RAF par le boîtier et le profil `0xD185` ;
- [fujifilm-ptp-recipes](https://github.com/ILFforever/fujifilm-ptp-recipes) (Fuji PTP Recipes contributors, documentation CC BY 4.0, code MIT) et [fujifilm-ptp-reference](https://github.com/zgrimz/fujifilm-ptp-reference) (zgrimz, CC BY 4.0) : les réglages perso C1-C7 et leur encodage ;
- [libgphoto2](https://github.com/gphoto/libgphoto2) (LGPL-2.1) : le relevé des propriétés du X-T4 ;
- [spektrafilm](https://github.com/andreavolpato/spektrafilm) (Andrea Volpato) : film modeling powered by spektrafilm, pour les cibles Provia, Ektar, Velvia, Ektachrome et Kodachrome ;
- [Imaging Resource](https://www.imaging-resource.com/) : les mires du X-T3 et du X-T30 qui ont servi à ajuster la matrice de la scène ;
- [colour-science](https://github.com/colour-science/colour), [rawpy](https://github.com/letmaik/rawpy) / [LibRaw](https://www.libraw.org/), [OpenCV](https://opencv.org/), NumPy, SciPy, Pillow, [ExifTool](https://exiftool.org/), et la table de Robertson du SDK DNG d'Adobe ;
- outil écrit à des fins d'interopérabilité, d'après ces projets publics et des essais sur mon X-T4 ; aucun code de Fujifilm n'est copié ici.

## Licence

Tout le dépôt, recettes, tableurs, packs, textes, figures et code (`xt4/outils/`), est sous **Creative Commons Attribution-NonCommercial 4.0 International (CC BY-NC 4.0)**, cf. [`LICENSE`](./LICENSE). Chaque fichier de code le dit dans son en-tête.

**En clair** : vous pouvez utiliser, partager, modifier et redistribuer les presets et le générateur **librement pour un usage non commercial**, à condition de **créditer les auteurs** (attribution par préfixe, cf. § Contribuer). Tout usage commercial (revente du pack, intégration dans un produit payant, etc.) est **interdit** sans accord explicite. Le code de `xt4/outils/` suit la même règle.

Les **recettes de presets** (valeurs de paramètres) sont des réglages publiés par leurs auteurs respectifs (voir § Contribuer). Elles ont été compilées depuis des sources publiques (FujiXWeekly, blogs, Discord francophone Team Fuji). Si vous êtes l'auteur d'un preset et souhaitez un retrait ou une correction d'attribution, ouvrir une issue.

Les licences des sources tierces (dont la licence CC BY-SA 4.0 des profils de spektrafilm, que les tables de cible prennent si vous les fabriquez) sont dans [`LICENCES-TIERS.md`](LICENCES-TIERS.md).

## Avertissement

Projet indépendant, **non affilié à Fujifilm Corporation**. « Fujifilm », « Fuji X RAW Studio », « Provia », « Velvia », « Astia », « Acros », « Eterna », « Classic Chrome », « Classic Negative » et les noms de boîtiers sont des marques de Fujifilm Corporation ; Kodak, Tri-X, Portra, Ektar, Ektachrome, Kodachrome, Ilford, HP5 et FP4 sont des marques de leurs propriétaires. Les noms de films désignent le rendu visé, pas un produit.

Ce projet **ne redistribue ni le binaire Fuji X RAW Studio, ni aucun code Fujifilm**. Le tableur génère des fichiers XML au format lu par XRFC.

**L'outil `xt4_recettes` écrit dans votre boîtier.** Il est fourni tel quel, **sans garantie d'aucune sorte**, et je ne peux pas être tenu responsable d'un réglage perdu ou d'un boîtier qui se comporterait mal. Fujifilm prévient qu'un particulier qui contrôle son boîtier par son SDK peut perdre la garantie ; cet outil n'utilise pas le SDK de Fujifilm, mais il parle au boîtier par le même protocole. Faites une sauvegarde complète avec l'application officielle avant le premier essai, écrivez un emplacement à la fois, vérifiez-le dans le menu, et ne branchez qu'un X-T4.

**Pendant les mesures**, le boîtier développe des milliers de RAF à la suite. Pendant ma passe de 2026, il s'est figé trois fois, toujours pendant de longues séries à balance du profil forcée, et il est reparti après extinction et rallumage. Sans balance forcée, plus de 20 000 conversions d'affilée sont passées sans incident, et 300 conversions forcées ensuite n'ont rien bloqué. La cause la plus probable est une fuite du firmware quand la balance du profil est forcée ; elle n'est pas prouvée.
