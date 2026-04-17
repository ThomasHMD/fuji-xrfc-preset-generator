# fuji-xrfc-preset-generator

Générateur en masse de profils **`.FP1`** pour **Fujifilm X Raw Studio (XRFC)** à partir d'un fichier Excel. 161 presets communautaires prêts à l'emploi, compilés depuis FujiXWeekly et un Discord francophone d'entraide.

---

## Télécharger

### ➜ [**DemoPresetV1.1.xlsm** (dernière release)](https://github.com/ThomasHMD/fuji-xrfc-preset-generator/releases/latest/download/DemoPresetV1.1.xlsm)

### ➜ [**presets-fp1-x-t4.zip** — les 161 `.FP1` déjà générés pour X-T4](https://github.com/ThomasHMD/fuji-xrfc-preset-generator/releases/latest/download/presets-fp1-x-t4.zip)

Pour un **autre boîtier** (X-T3, X-T2, X-H1, X100V, X-S10, X-Pro3, X-T5, GFX…) : cf. [§ Adapter à un autre boîtier](#adapter-à-un-autre-boîtier).

Toutes les versions et leur changelog : [Releases](https://github.com/ThomasHMD/fuji-xrfc-preset-generator/releases).

---

## Vidéo de présentation

📺 **[160+ presets directement dans votre Fujifilm !](https://www.youtube.com/watch?v=j8YM1vs0g2Y)** — présentation du projet, démonstration X-T4, procédure d'import (YouTube, 20 min).

## Pourquoi

Fujifilm X Raw Studio n'a aucune fonction d'**import en masse** : chaque preset doit être configuré à la main dans l'interface, puis sauvegardé un par un. Ce projet permet de :

1. décrire les **161 recettes communautaires** (FujiXWeekly, Blog Henri-Pierre Chavaz, Discord « Team Fuji », contributions perso) dans un tableur lisible,
2. les **générer en lot** comme fichiers `.FP1` (XML XRFC) avec une macro VBA,
3. les **déposer dans XRFC** pour développer les RAF avec un choix massif de rendus.

Historique : projet démarré en janvier 2022, [documenté publiquement sur Notion](https://thomashammoudi.notion.site/Documentation-preset-Fujifilm-a68e0d6ce170416987ad458475cca9ec), avec une communauté d'échange de `.FP1` par boîtier sur Discord.

## Arborescence

```
fuji-xrfc-preset-generator/
├── V1/
│   ├── DemoPreset.xlsm           # Générateur v1 — macro VBA GenererFP1
│   ├── DemoPreset.xml            # Exemple annoté du format de sortie
│   └── FP1/                      # 161 .FP1 générés (X-T4)
├── V1.1/
│   ├── DemoPresetV1.1.xlsm       # Générateur v1.1 (fix Temperature WB)
│   └── FP1/                      # 161 .FP1 générés (X-T4)
└── Les presets FP1 du discord/
    ├── Règles de nommage.txt     # Convention communautaire
    ├── Henri-Pierre Chavaz - FUJI X RAW STUDIO PRESETS (04-02-2022)/
    │   └── {GFX 100,GFX 50R,GFX 50S,X Pro 2,X Pro 3,X-E3,X-H1,X-T2,
    │        X-T20,X-T3,X-T30,X-T4,X100F,X100V}/…
    └── X-T4, X-T2, X-H1, X100V, X-S10/{Base,Discord}
                                   # Base = pack de référence,
                                   # Discord = contributions persos
                                   # (Thomas_HMD, Stolentinstants,
                                   #  Sylvain_BZH, DarkFox, Dietmar Kaske…)
```

## Comment ça marche

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

## Installation (utilisateur final)

### 1. Ouvrir le tableur et générer les presets

1. Télécharger `DemoPresetV1.1.xlsm` depuis la [dernière release](https://github.com/ThomasHMD/fuji-xrfc-preset-generator/releases/latest).
2. Ouvrir dans **Excel** (Microsoft Excel — LibreOffice Calc **n'exécute pas** la macro VBA utilisée).
3. Activer les macros à l'ouverture.
4. `Alt+F8` → `GenererFP1` → `Exécuter`.
5. Un dossier `FP1/` est créé à côté du `.xlsm`. Il contient les 161 `.FP1`.

> Raccourci : les 161 `.FP1` pour X-T4 sont aussi disponibles pré-générés dans la release (`presets-fp1-x-t4.zip`).

### 2. Importer dans Fuji X Raw Studio

**macOS** : coller les `.FP1` dans

```
~/Library/Application Support/com.fujifilm.denji/X RAW STUDIO/
```

**Windows** :

```
C:\Users\<votre-nom>\AppData\Local\com.fujifilm.denji\X_RAW_STUDIO\
```

### 3. Brancher un boîtier Fuji et développer

X Raw Studio exige qu'un **boîtier Fuji soit connecté en USB** (même modèle que celui indiqué par `device="..."` dans les `.FP1` — voir § Adapter). Une fois connecté, les presets apparaissent dans le menu *Développer avec paramètres*.

## Adapter à un autre boîtier

Les `.FP1` fournis sont générés pour **X-T4**. Pour un autre modèle, modifier trois attributs dans la macro (lignes `"        <PropertyGroup device="…"`  et `TetherRAWConditonCode`) :

| Boîtier | `device=` | `TetherRAWConditonCode` |
|---|---|---|
| X-T2 | `X-T2` | `X-T2_0100` |
| X-T3 | `X-T3` | `X-T3_0100` |
| X-T4 | `X-T4` | `X-T4_0100` |
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

Certaines recettes utilisent des **simulations qui n'existent pas sur les anciens X-Trans** (`ClassicNEGA`, `Eterna`, `BleachBypass`, `AcrosR/G/Ye`, `ColorChromeBlue`, `ChromeEffect`). Le preset sera ignoré ou affichera une erreur *« preset non applicable »*. Voir la section [Différences par appareil sur la doc Notion](https://thomashammoudi.notion.site/Documentation-preset-Fujifilm-a68e0d6ce170416987ad458475cca9ec).

## Format `.FP1` — résumé

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

### Mapping colonnes Excel → tags XML

| Colonne | Tag | Valeurs possibles |
|---|---|---|
| `Label` | `label="…"` + nom de fichier | Texte libre (`/`→`_`, `*`→`_`) |
| `FilmSimulation` | `<FilmSimulation>` | `Provia`, `Velvia`, `Astia`, `Classic` (Classic Chrome), `ClassicNEGA`, `NEGA` (Pro Neg Std), `NEGAhi` (Pro Neg Hi), `Eterna`, `BleachBypass`, `Acros`, `AcrosR/G/Y/Ye`, `BW`, `BR/G/Ye`, `Sepia` |
| `Grain` | `<GrainEffect>` + `<GrainEffectSize>` | `OFF` · `WEAK` · `STRONG` · `STRONG L` (→ STRONG/LARGE) |
| `CCFx/CCFxB` | `<ChromeEffect>` + `<ColorChromeBlue>` | `OFF` · `"A/B"` splitté sur `/`, ex. `WEAK/STRONG` |
| `WhiteBalance` | `<WhiteBalance>` + `<WBColorTemp>` | Preset (`Auto`, `Daylight`, `Shade`, `FLight1`, `FLight2`, `UWater`, `Auto_White`) **ou** température (`5300K`, `6700K`…). V1.1 : `*K` → `Temperature` + `WBColorTemp` |
| `WBShiftR` | `<WBShiftR>` | `-9..+9` |
| `WBShiftB` | `<WBShiftB>` | `-8..+9` |
| `DynamicRange` | `<DynamicRange>` | `100`, `200`, `400`, `AUTO`, `WEAK`, `STRONG` |
| `HighlightTone` | `<HighlightTone>` | `-2..+4` |
| `ShadowTone` | `<ShadowTone>` | `-2..+4` |
| `Color` | `<Color>` | `-4..+4` |
| `Sharpness` | `<Sharpness>` | `-4..+4` |
| `NoisReduction` | `<NoisReduction>` | `-4..+4` |
| `ExposureBias` | `<ExposureBias>` | Encodage Fuji : `0`, `P0P33` (+1/3 EV), `P0P67` (+2/3), `P1P00` (+1), `M0M33` (−1/3), `M1P00` (−1). Lettre 1 = signe des EV entiers (P/M), chiffre = EV, lettre 3 = signe des tiers, chiffres = 33/67 |

Champs **figés en dur** dans la macro (pour évolution ultérieure) : `SerialNumber`, `Clarity`, `BlackImageTone`, `MonochromaticColor_RG`, `SmoothSkinEffect`, `ColorSpace`, `LensModulationOpt`, `HDR`, `DigitalTeleConv`, `WideDRange`.

## Différences entre V1 et V1.1

La V1.1 corrige la gestion de la **balance des blancs en température** :

```vb
' V1  →  <WhiteBalance>5300K</WhiteBalance>  <WBColorTemp>10000K</WBColorTemp>
' V1.1 → <WhiteBalance>Temperature</WhiteBalance>  <WBColorTemp>5300K</WBColorTemp>
```

Si la valeur de la colonne `WhiteBalance` se termine par `K`, V1.1 la bascule automatiquement dans `WBColorTemp` et met `Temperature` dans `WhiteBalance` (comportement conforme à XRFC). V1 écrit la valeur brute et force `10000K` en température.

> **Recommandation** : utiliser la V1.1.

## Pistes d'évolution

* **Port Python (ou Go)** — multiplateforme, scriptable, pas de dépendance Excel. Un membre du Discord a déjà publié [`FujiSimuRecipesGen`](https://thomashammoudi.notion.site/Documentation-preset-Fujifilm-a68e0d6ce170416987ad458475cca9ec#FujiSimuRecipesGen) en Go (MIT).
* **Multi-boîtier natif** — ajouter des colonnes `Device`, `Firmware`, `SerialNumber` pour générer tous les packs en une passe.
* **Exposer les champs figés** (Clarity, ColorSpace, BlackImageTone…) pour couvrir les presets B&W virés + les presets AdobeRGB.
* **Validateur `.FP1`** (JSON Schema / Pydantic) pour vérifier un preset avant import et dé-générer vers CSV.
* **UI web** (Streamlit / SvelteKit) pour saisir un preset via formulaire avec preview.
* **Support X-T5 et boîtiers récents** — voir la [section X-T5 de la doc Notion](https://thomashammoudi.notion.site/Documentation-preset-Fujifilm-a68e0d6ce170416987ad458475cca9ec) pour un début d'intégration communautaire.

Contributions bienvenues — ouvrir une issue ou une PR.

## Contribuer

Les presets sont nommés par **préfixe auteur** (convention FujiXWeekly / Team Fuji) :

| Préfixe | Auteur |
|---|---|
| `BLP` | Blaise Pauly |
| `BT` | Benjamin Turner |
| `DC` | Daniel Craig |
| `EM` | Eric Mercurio |
| `GB` | *(inconnu, GB)* |
| `HF` | *(inconnu, HF)* |
| `JC` | Jerome Courtial |
| `JP` | *(inconnu, JP)* |
| `KM` | Kevin Mullins |
| `LC` | *(inconnu, LC)* |
| `MT` | Michael Turner |
| `NZD` | *(NZD)* |
| `PE` | *(PE)* |
| `PS` | *(PS)* |
| `RR` | Ritchie Roesch ([FujiXWeekly](https://fujixweekly.com/)) |
| `VM` | *(VM)* |
| `WM` | *(WM)* |

Pour ajouter **vos propres presets**, utiliser `Prénom_Nom - Nom du preset.FP1` (cf. `Les presets FP1 du discord/Règles de nommage.txt`) et déposer dans le dossier de votre boîtier.

## Ressources externes

* 🎥 **Vidéo YouTube** — [160+ presets directement dans votre Fujifilm !](https://www.youtube.com/watch?v=j8YM1vs0g2Y) (Thomas Hammoudi, janvier 2022)
* 📘 **Documentation Notion** (la plus à jour) — [Documentation preset Fujifilm](https://thomashammoudi.notion.site/Documentation-preset-Fujifilm-a68e0d6ce170416987ad458475cca9ec)
* 📚 **FujiXWeekly** — [fujixweekly.com](https://fujixweekly.com/) — source de la plupart des presets `RR …`
* 📚 **Henri-Pierre Chavaz** — [hpchavaz-photography.blogspot.com/p/fujifims.html](https://hpchavaz-photography.blogspot.com/p/fujifims.html) — compilation par boîtier
* 📄 Article blog Thomas Hammoudi — [thomashammoudi.com/presets-fujifilm/](https://thomashammoudi.com/presets-fujifilm/)

## Licence

Ce projet est distribué sous **Creative Commons Attribution-NonCommercial 4.0 International (CC BY-NC 4.0)** — cf [`LICENSE`](./LICENSE).

**En clair** : vous pouvez utiliser, partager, modifier et redistribuer les presets et le générateur **librement pour un usage non commercial**, à condition de **créditer les auteurs** (attribution par préfixe, cf. § Contribuer). Tout usage commercial (revente du pack, intégration dans un produit payant, etc.) est **interdit** sans accord explicite.

Les **recettes de presets** (valeurs de paramètres) sont des réglages publiés par leurs auteurs respectifs (voir § Contribuer). Elles ont été compilées depuis des sources publiques (FujiXWeekly, blogs, Discord francophone Team Fuji). Si vous êtes l'auteur d'un preset et souhaitez un retrait ou une correction d'attribution, ouvrir une issue.

## Disclaimer

Projet indépendant, **non affilié à Fujifilm Corporation**. « Fujifilm », « Fuji X Raw Studio », « Provia », « Velvia », « Astia », « Acros », « Eterna », « Classic Chrome », « Classic Negative » et les noms de boîtiers sont des marques de Fujifilm Corporation.

Ce projet **ne redistribue ni le binaire Fuji X Raw Studio, ni aucun code Fujifilm**. Il se contente de générer des fichiers XML au format documenté par Fujifilm et lu par XRFC. Usage à vos propres risques.
