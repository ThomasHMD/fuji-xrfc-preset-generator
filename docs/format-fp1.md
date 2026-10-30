# Le format `.FP1`

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
- les recettes mesurées remplissent aussi `Clarity` ; aucune n'utilise le virage : `BlackImageTone` et `MonochromaticColor_RG` y restent à 0 ;
- deux fichiers de 2022, `RR Split-Tones B&W 1_2` et `2_2`, ont un `&` non échappé dans leur `label` : un lecteur XML strict refuse de les ouvrir (`xt4_recettes` les lit quand même).

## Différences entre V1 et V1.1

La V1.1 corrige la gestion de la **balance des blancs en température** :

```vb
' V1  →  <WhiteBalance>5300K</WhiteBalance>  <WBColorTemp>10000K</WBColorTemp>
' V1.1 → <WhiteBalance>Temperature</WhiteBalance>  <WBColorTemp>5300K</WBColorTemp>
```

Si la valeur de la colonne `WhiteBalance` se termine par `K`, V1.1 la bascule automatiquement dans `WBColorTemp` et met `Temperature` dans `WhiteBalance` (comportement conforme à XRFC). V1 écrit la valeur brute et force `10000K` en température.

> **Recommandation** : utiliser la V1.1.
