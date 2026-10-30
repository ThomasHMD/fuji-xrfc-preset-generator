# Le tableur et X RAW Studio

## Pourquoi

Fujifilm X RAW Studio n'a aucune fonction d'**import en masse** : chaque profil se règle à la main dans son interface et s'enregistre un par un. Il sait copier un profil vers un réglage perso du boîtier (CUSTOM SETTING, depuis sa version 1.8.0 d'après les notes de version de Fujifilm), mais un seul à la fois, toujours depuis son interface. Ce projet permet de :

1. décrire les **161 recettes communautaires** (FujiXWeekly, blog d'Henri-Pierre Chavaz, Discord « Team Fuji », contributions perso) dans un tableur lisible,
2. les **générer en lot** comme fichiers `.FP1` (XML XRFC) avec une macro VBA,
3. les **déposer dans XRFC** pour développer les RAF avec un choix massif de rendus,
4. depuis 2026, sur un X-T4 et un Mac, les **écrire directement dans C1 à C7** en ligne de commande, et utiliser des recettes **mesurées** plutôt que réglées à l'œil.

Historique : projet démarré en janvier 2022, [documenté publiquement](documentation-v1.md), avec une communauté d'échange de `.FP1` par boîtier sur Discord.

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
  │ (2026, 2022, ou  │   relecture et contrôle   │ enregistré à         │
  │  le vôtre)       │ ◄──────────────────────── │ l'extinction         │
  └──────────────────┘                           └──────────────────────┘
```

## Installation

### 1. Ouvrir le tableur et générer les presets

1. Télécharger `DemoPresetV1.1.xlsm` depuis la [dernière release](https://github.com/ThomasHMD/fuji-xrfc-preset-generator/releases/latest).
2. Ouvrir dans **Excel** (Microsoft Excel - LibreOffice Calc **n'exécute pas** la macro VBA utilisée). La macro est écrite pour Windows (chemins en `\`, `Scripting.FileSystemObject`) : sur Excel pour Mac, elle ne tournera probablement pas (non essayé). Sur Mac, prenez le pack complet : les `.FP1` y sont déjà générés.
3. Activer les macros à l'ouverture.
4. `Alt+F8` → `GenererFP1` → `Exécuter`.
5. Un dossier `FP1/` est créé à côté du `.xlsm`. Il contient les 161 `.FP1`.

> Raccourci : les 161 `.FP1` déjà générés sont dans le pack complet.

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

X RAW Studio exige qu'un **boîtier Fuji soit connecté en USB** (même modèle que celui indiqué par `device="..."` dans les `.FP1` : voir [plus bas](#adapter-à-un-autre-boîtier)), en mode USB RAW CONV./BACKUP RESTORE. Une fois connecté, les presets apparaissent dans le menu *Développer avec paramètres*.

### 4. Sans X RAW Studio (macOS, X-T4)

Voir [Écrire une recette dans C1 à C7](ecrire-dans-c1-c7.md).

## Adapter à un autre boîtier

Tout est déjà décliné dans le [pack lite ou complet](https://github.com/ThomasHMD/fuji-xrfc-preset-generator/releases/latest), un dossier par boîtier : X-T2, X-T3, X-T5, X-T20, X-T30, X-H1, X-S10, X-E3, X-Pro2, X-Pro3, X100F, X100V, GFX 50R, GFX 50S et GFX 100. Je n'ai testé que le X-T4.

Les `.FP1` de [`presets/`](../presets/) sont générés pour **X-T4**. Pour un autre modèle, modifier trois attributs dans la macro (lignes `"        <PropertyGroup device="…"`  et `TetherRAWConditonCode`) :

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

Certaines recettes utilisent des **simulations qui n'existent pas sur les anciens X-Trans** (`ClassicNEGA`, `Eterna`, `BleachBypass`, `AcrosR/G/Ye`, `ColorChromeBlue`, `ChromeEffect`). Le preset sera ignoré ou affichera une erreur *« preset non applicable »*. Voir la section [Autres corrections de la doc de la v1](documentation-v1.md#autres-corrections).

Ce tableau vaut pour X RAW Studio. **L'écriture directe dans C1 à C7 (`xt4_recettes`) ne marche que sur le X-T4**, et les recettes n'ont été mesurées que sur lui.
