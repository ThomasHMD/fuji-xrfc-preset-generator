# La méthode de mesure

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

## Ce que le boîtier ne sait pas faire

La mesure dit aussi où le X-T4 plafonne, quelle que soit la recette :

- **Pas de vraie courbe de tons.** Le réglage des hautes lumières n'agit qu'au-dessus de L\* 60 environ, celui des ombres qu'en dessous de L\* 45, de −2 à +4 par demi-cran. Rien ne touche les tons moyens.
- **Pas de mélangeur de canaux en noir et blanc.** Les films noir et blanc voient beaucoup de bleu ; le boîtier fait son gris par un mélange fixe que ses filtres ne déplacent que vers le rouge ou le vert. Résultat : les jaunes ne se placent pas où l'on veut. En HP5 et en FP4, ils sortent trop clairs (+13 et +17 L\* en médiane, sur les photos jamais vues) ; en Tri-X, trop sombres (−9 L\*), comme avec la meilleure de mes recettes de 2022.
- **Un grain plus fin que celui de la Tri-X.** Le grain fort et gros du boîtier reste environ 2,5 fois plus faible, à l'échelle d'un tirage.
- **La correction d'exposition n'est pas gardée** par les réglages perso : d'où la colonne « Réglage à faire en plus ».
- **La plage dynamique se choisit à la prise de vue.** Un RAF se développe à sa DR de prise de vue ou en dessous ; au-dessus, l'image vire au vert. Les recettes mesurées restent en DR100 : aucune DR plus haute n'a gagné assez (règle fixée d'avance : 0,3 de gain moyen, sur 2 scènes sur 3).
- **La balance en Kelvin n'aide pas le noir et blanc** : elle agit comme une exposition, pas comme un filtre. Dans le duel (Tri-X, HP5, FP4, de 3 200 à 6 500 K), aucune température ne bat la balance Auto avec décalages R / B : toutes les recettes mesurées restent en Auto.

## Rejouer la mesure

La chaîne est dans [`outils/x-t4/`](../outils/x-t4/) :

| Outil | Rôle |
|---|---|
| `xt4_banc.swift` | le banc : envoie un RAF au boîtier, puis des profils de conversion, et récupère chaque JPEG |
| `xt4_d185.py` | lit et modifie le profil de conversion `0xD185` |
| `xt4_scene.py` | la couleur de la scène estimée depuis le RAW |
| `xt4_cibles.py` | les cibles de film |
| `xt4_mesure.py` | la première passe : préparation des photos, blocs, échelle d'exposition, mesure, grain |
| `xt4_recherche_v2.py` | la recherche de la passe finale, le bilan, l'écriture des `.FP1` mesurés |
| `xt4_transfert.py` | le pré-tri : chaque proposition est d'abord rendue sur 3 photos, son rendu sur les autres est prédit, et seules les 2 meilleures sont rendues partout (environ 7 fois moins de conversions ; les décisions et les chiffres publiés viennent toujours de rendus réels) |
| `xt4_validation.py` | contrôle du banc, plage dynamique, verdict sur les photos jamais vues |
| `xt4_leviers.py` | l'effet de chaque réglage caché du profil de conversion |
| `xt4_effets.py` | l'effet de chaque réglage du menu, mesuré sur les rendus déjà faits (chiffres de la [doc](traitement-couleur-x-t4.md)) |
| `xt4_illustrations.py` | les figures de la doc : le boîtier rend des photos sans personne, un réglage à la fois |

Pour la rejouer, il faut :

- un X-T4 et vos propres RAF du X-T4 (le boîtier ne développe que les RAF de son modèle) ;
- Python 3 et les paquets de [`outils/x-t4/requirements.txt`](../outils/x-t4/requirements.txt), plus [ExifTool](https://exiftool.org/) ;
- les modules du D750 publiés dans mon dépôt [retro-ingenierie-boitiers](https://github.com/ThomasHMD/retro-ingenierie-boitiers) (`d750/outils/`) : clonez ce dépôt, puis donnez son dossier aux outils par la variable `XT4_RIB` (par exemple `export XT4_RIB=~/retro-ingenierie-boitiers`) ; ces modules restent sous la licence de leur dépôt, **CC BY-NC-SA 4.0** ; le code de `outils/x-t4/` les importe sans en copier une ligne ;
- pour la cible Classic Chrome, la LUT F-Log2 de Fujifilm, à télécharger [chez Fujifilm](https://www.fujifilm-x.com/global/support/download/lut/) ;
- pour Provia, Ektar, Velvia, Ektachrome et Kodachrome, les tables fabriquées avec spektrafilm, à faire chez vous, dans le dossier donné par `D750_SPEKTRAFILM` ;
- un dossier de travail pour les rendus du boîtier et le cache, donné par `XT4_CHANTIER` (par défaut, `xt4-mesure` dans le dossier temporaire du système) ;
- pour la matrice de la scène, rien : ses coefficients sont dans `xt4_scene.py` (les RAF d'Imaging Resource ne servent qu'à la refaire) ;
- les cibles Tri-X, Portra et Pro 400H ne sont pas reproductibles avec ce dépôt : elles viennent d'un preset acheté, dont aucun fichier ni aucune table n'est publié ici.
