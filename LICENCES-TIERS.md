# Licences et sources tierces

Tout ce qui n'est pas listé ici est le travail de Thomas Hammoudi, sous [CC BY-NC 4.0](LICENSE) : les recettes, les tableurs, les textes, les figures et le code de `xt4/outils/`.

## Repris dans le code de `xt4/outils/`

| Source | Licence | Ce qui est repris | Où |
|---|---|---|---|
| [FilmKit](https://github.com/eggricesoy/filmkit) | MIT | la séquence de conversion d'un RAF par le boîtier, les index du profil 0xD185, la table de réduction du bruit | `xt4_recettes.swift`, `xt4_banc.swift`, `xt4_d185.py`, `xt4_mesure.py` |
| [fujifilm-ptp-recipes](https://github.com/ILFforever/fujifilm-ptp-recipes), Fuji PTP Recipes contributors | documentation CC BY 4.0, code MIT | codes et encodages des réglages perso C1-C7, règles du nom d'emplacement (d'après la documentation) | `xt4_recettes.swift` |
| [fujifilm-ptp-reference](https://github.com/zgrimz/fujifilm-ptp-reference), zgrimz | CC BY 4.0 | transport, propriétés, emplacements (d'après la documentation) | `xt4_recettes.swift` |
| SDK DNG d'Adobe | licence du SDK DNG (mention ci-dessous) | la table de Robertson (`dng_temperature.cpp`) | `xt4_scene.py` |
| [Imaging Resource](https://www.imaging-resource.com/) | images © The Imaging Resource | la matrice de la scène est ajustée sur leurs mires du X-T3 et du X-T30 ; seuls les 9 coefficients sont ici, aucune image | `xt4_scene.py` |

Le relevé des propriétés du X-T4 de [libgphoto2](https://github.com/gphoto/libgphoto2) (LGPL-2.1) a servi de référence ; aucune ligne de son code n'est reprise.

### Notice de FilmKit

    MIT License

    Copyright (c) 2026 eggricesoy

    Permission is hereby granted, free of charge, to any person obtaining a copy
    of this software and associated documentation files (the "Software"), to deal
    in the Software without restriction, including without limitation the rights
    to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
    copies of the Software, and to permit persons to whom the Software is
    furnished to do so, subject to the following conditions:

    The above copyright notice and this permission notice shall be included in all
    copies or substantial portions of the Software.

    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
    IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
    FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
    AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
    LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
    OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
    SOFTWARE.

### Notice du SDK DNG d'Adobe

La table de Robertson de `xt4_scene.py` est reprise de `dng_temperature.cpp`, du SDK DNG d'Adobe, dont l'en-tête dit :

    Copyright 2006-2019 Adobe Systems Incorporated
    All Rights Reserved.

    NOTICE:  Adobe permits you to use, modify, and distribute this file in
    accordance with the terms of the Adobe license agreement accompanying it.

Le contrat de licence du SDK DNG permet l'usage, la modification et la redistribution, à condition de garder cette mention.

## Hors du dépôt : à récupérer soi-même

| Source | Sert à | Licence, conditions |
|---|---|---|
| Modules du D750 de [retro-ingenierie-boitiers](https://github.com/ThomasHMD/retro-ingenierie-boitiers) | cibles, modèle couleur, fiches des films (chaîne de mesure) | CC BY-NC-SA 4.0 |
| [spektrafilm](https://github.com/andreavolpato/spektrafilm) (Andrea Volpato) | cibles Provia 100F, Ektar 100, Velvia 100, Ektachrome E100, Kodachrome 64 | code GPL-3.0 ; profils et tables CC BY-SA 4.0 ; film modeling powered by spektrafilm ; ni le code ni les tables ne sont ici |
| LUT F-Log2 de Fujifilm | cible Classic Chrome | [page officielle](https://www.fujifilm-x.com/global/support/download/lut/) ; non redistribuée |
| RAF des mires VFA du X-T3 et du X-T30 (Imaging Resource) | refaire la matrice de la scène | usage privé et non commercial seulement ; non redistribués |
| Un preset acheté que j'aimais beaucoup | cibles Tri-X 400, Portra 400, Pro 400H | produit commercial ; aucun de ses fichiers, aucune de ses tables, aucun ajustement fait dessus n'est ici |
| Fiches Kodak (Tri-X F-4017, Portra E-4050) et Ilford (HP5 Plus, FP4 Plus) | cibles noir et blanc, grain | chiffres relevés ; PDF non redistribués |
| colour-science (BSD-3-Clause), rawpy (MIT) avec LibRaw (LGPL-2.1 ou CDDL-1.0), OpenCV (Apache-2.0), NumPy et SciPy (BSD-3-Clause), Pillow (MIT-CMU), ExifTool (Artistic ou GPL) | chaîne de mesure | leurs licences |

## Marques

Fujifilm, X RAW Studio, X-T4, Provia, Velvia, Astia, Acros, Eterna, Classic Chrome, Classic Negative, Kodak, Tri-X, Portra, Ektar, Ektachrome, Kodachrome, Ilford, HP5 et FP4 sont des marques de leurs propriétaires. Ce projet n'est lié à aucun d'eux ; les noms des films désignent le rendu visé, pas un produit.
