#!/usr/bin/env python3
# SPDX-License-Identifier: CC-BY-NC-4.0
# Copyright (c) 2026 Thomas Hammoudi
"""Cibles de rendu des recettes JPEG du X-T4 (29/10/2026) : les mêmes que celles du D750 et du D40 (on repart des mêmes
cibles qu'avant), des variantes de goût du Classic Chrome et de nouveaux films simulés par spektrafilm.
Voir docs/methode.md.

Chaque cible est une fonction XYZ de la scène (D65, gris de 18 % = 0,18) → CIELAB D65 de l'image rendue (affichage
sRGB). Échelle d'exposition : celle de xt4_mesure.scene (RAW × 0,18 / y18, y18 = valeur RAW que le Provia neutre du
boîtier rend à 118/255). Rien n'est recopié : les cibles viennent de d750_cibles, d750_analyse et d750_spektrafilm.

- trix    : d750_cibles.cible_nb, mélange et courbe du preset Tri-X (courbe des recettes V1 du D40) : cible de la Tri-X v2 du D750
            (C-7) et du Tri-X du D40 ;
- hp5     : d750_cibles.cible_nb('hp5_fiche', d750_analyse.courbe_hp5_scans) : mélange de la fiche Ilford, tonalité des
            scans HP5 de l'auteur (le « TRI-X » du D750 ramené centile par centile sur ces scans) : cible de la HP5+ du D750.
            Gris à L* 68 : `correction_hp5` calcule la surexposition à la prise de vue qui y amène une courbe normale ;
- hp5_consigne : la cible hp5 telle que doit la rendre, sur un RAF exposé normalement (le banc), une recette HP5 donnée
            avec la consigne « exposer +2/3 IL » (HP5_CONSIGNE_IL) : hp5(XYZ × 2^-2/3), gris vers L* 50 ;
- fp4     : d750_cibles.cible_nb('fp4_fiche', d750_cibles.courbe_film('fp4')) : fiche Ilford, tirage grade 2 (D750) ;
- portra  : d750_cibles.melange_film(paires(portra-preset-regle.json), portra-esprit.json) : « esprit Portra », l'export
            du preset Portra tel que l'auteur le règle, tiré à 65 % vers ses scans Portra 400 (C-5 du D750) ;
- classic_chrome : d750_cibles.fuji('CLASSIC-CHROME') : LUT F-Log2 officielle de Fujifilm (C-2 du D750) ;
- kodachrome : d750_spektrafilm.cible(kodak_kodachrome_64.npz, chroma=1,2) : « Kodachrome vif » du D750 (C-1), ici dans
            le rendu retenu pour spektrafilm (le D750 visait l'absolu : `fonction('kodachrome', rendu='absolu')`) ;
- cc_115, cc_130, cc_130_contraste : Classic Chrome plus coloré (chroma × 1,15, × 1,3, × 1,3 et courbe en S douce sur L*) :
            CHOIX DE GOÛT de l'auteur (29/10/2026), rien de mesuré ;
- ektachrome, velvia, provia : spektrafilm, film inversible regardé directement (scan du film, comme le Kodachrome) ;
- ektar, pro400h : spektrafilm, négatif TIRÉ sur le papier conseillé par son profil (Ektar : Kodak Portra Endura ;
            Pro 400H : Fujifilm Crystal Archive II), filtres neutres de la base de spektrafilm (gris de 18 % neutre).
            spektrafilm n'inverse pas un négatif (son « scan du film » rend le négatif orangé) : le tirage est son seul
            chemin positif, et le plus proche d'un tirage ou d'un scan de labo (voir docs/methode.md) ;
- fp400h  : Pro 400H du preset acheté (profil Look du preset, RETENUE pour la Pro 400H, 29/10/2026 : l'auteur la préfère à
            spektrafilm, comme pour la Portra) : la table RVB de ce profil Look (lue dans son .xmp, hors du dépôt, rien
            recopié) posée sur la base d'Adobe ajustée aux paires NEF + export du D750 (matrice K et courbe de
            portra-preset.json, d750-analyse-seances.md §3.6) : la chaîne exacte de la cible PORTRA du D750, avec un autre
            profil. Le préréglage du preset qui l'appelle n'ajoute aucun autre réglage. Voir `profil_sur_base` ;
- pro400h, pro400h_p1, pro400h_p2 : variantes spektrafilm de la 400H ;
- pro400h_p1, pro400h_p2 : la 400H surexposée de 1 et 2 IL à la prise de vue, tirée normalement (exposition du tirage
            compensée, d750_spektrafilm --surex), le « 400H pastel » des photographes ; témoins : la Portra 400 de
            spektrafilm traitée de même sur le même papier (portra_spk_ca, _p1, _p2).

Rendu des cibles spektrafilm (RENDU, 29/10/2026), trois au choix :
- 'absolu' : lumière rapportée à l'illuminant de visée (D50), comme le Kodachrome du D750 : le support sans image n'est
  pas blanc (L* 83 à 88) ;
- 'relatif' : le blanc du support (film ou papier sans image) sort à L* 100, par adaptation chromatique de Bradford à ce
  blanc (l'œil devant une table lumineuse ou un tirage, un scanner calé sur la densité minimale) ; le noir reste celui
  du support (pas de compensation du point noir). Le gris de 18 % monte alors à L* 57 à 60 (+0,3 à +0,5 IL) ;
- 'relatif_gris' (RETENU) : le relatif, la scène décalée en exposition pour que le gris de 18 % sorte à 118/255 (L* 49,6),
  comme toutes les autres cibles et le calage du X-T4 ; le décalage est calculé par table (`decalage_gris`).

Tables spektrafilm (hors du dépôt) : dossier D750_SPEKTRAFILM, obligatoire pour ces cibles ; fabriquées par
d750_spektrafilm.py (venv du chantier, Python 3.13). Film modeling powered by spektrafilm (A. Volpato ; code GPLv3,
profils CC BY-SA 4.0).

  xt4_cibles.py controle     gris, rampe de gris, ColorChecker (BabelColor) de chaque cible, en relatif et en absolu
  xt4_cibles.py comparer     anciennes cibles contre nouvelles, absolu contre relatif, 400H surexposée contre Portra, et
                             correction d'exposition de la HP5, sur les blocs des 16 RAF ; recettes déjà rendues (cache,
                             sans le boîtier) notées contre les nouvelles cibles
  xt4_cibles.py planche      recherche/figures/xt4-cibles-2026-10-29.jpg (rendus de la cible seule, 3 RAF)
  xt4_cibles.py --self-test

Interface pour xt4_mesure : `cibles(y18)` rend la même chose que xt4_mesure.cibles ({film: {raf: Lab}}, {raf: Lab de la
scène}), mêmes clés trix, hp5, fp4, portra, plus les nouvelles ; `fonction(cle)` ; `image(raf, cle, y18)`.
"""
import json
import os
import pathlib
import sys

import numpy as np

ICI = pathlib.Path(__file__).resolve().parent
# modules du D750 (d750_modele, d750_cibles, films_nb, dcp…) : dépôt https://github.com/ThomasHMD/retro-ingenierie-boitiers ;
# XT4_RIB = le dossier de son clone (par défaut, deux dossiers au-dessus de ce fichier)
RACINE = pathlib.Path(os.environ.get('XT4_RIB') or ICI.parent.parent)
if not (RACINE / 'd750' / 'outils' / 'd750_modele.py').is_file() and not os.environ.get('XT4_RIB_AVERTI'):
    os.environ['XT4_RIB_AVERTI'] = '1'
    print(f"xt4 : modules du D750 introuvables dans {RACINE / 'd750' / 'outils'} ; XT4_RIB doit pointer vers un clone de "
          'https://github.com/ThomasHMD/retro-ingenierie-boitiers (voir docs/methode.md).', file=sys.stderr)
for _p in (ICI, RACINE / 'd750' / 'outils', RACINE / 'commun' / 'outils'):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
SPK = pathlib.Path(os.environ.get('D750_SPEKTRAFILM') or '<D750_SPEKTRAFILM non défini>')   # sans lui, cibles spektrafilm désactivées
SEANCES = RACINE / 'd750' / 'recherche' / 'donnees-films' / 'd750-seances'
DONNEES = ICI.parent / 'recherche' / 'donnees'
FIGURES = ICI.parent / 'recherche' / 'figures'
DATE = '2026-10-29'
RENDUS = ('absolu', 'relatif', 'relatif_gris')
RENDU = 'relatif_gris'   # rendu retenu pour les cibles spektrafilm : blanc du support → L* 100, gris de 18 % à 118/255
L_GRIS = 49.64           # L* de 118/255

# clé → nom affiché, noir et blanc ou non, source en une ligne (planche)
FILMS = {
    'trix': ('Tri-X 400', True, 'preset Tri-X (Tri-X v2 du D750, D40)'),
    'hp5': ('HP5 Plus', True, "fiche Ilford, tonalité des scans HP5 de l'auteur"),
    'hp5_consigne': ('HP5 Plus, exposée +2/3 IL', True, 'la même, vue par un RAF exposé normalement'),
    'fp4': ('FP4 Plus', True, 'fiche Ilford, tirage grade 2'),
    'portra': ('Portra 400', False, 'esprit Portra : export du preset réglé + scans'),
    'classic_chrome': ('Classic Chrome', False, 'LUT officielle Fujifilm'),
    'kodachrome': ('Kodachrome 64', False, 'spektrafilm × 1,2 (D750 : absolu)'),
    'cc_115': ('Classic Chrome × 1,15', False, 'goût : chroma × 1,15'),
    'cc_130': ('Classic Chrome × 1,3', False, 'goût : chroma × 1,3'),
    'cc_130_contraste': ('CC × 1,3 + contraste', False, 'goût : × 1,3, pente +15 % au gris'),
    'ektachrome': ('Ektachrome E100', False, 'spektrafilm, diapositive'),
    'velvia': ('Velvia 100', False, 'spektrafilm, diapositive'),
    'provia': ('Provia 100F', False, 'spektrafilm, diapositive'),
    'ektar': ('Ektar 100', False, 'spektrafilm, tirage Portra Endura'),
    'fp400h': ('Pro 400H du preset', False, 'profil Look du preset acheté'),
    'pro400h': ('Pro 400H', False, 'spektrafilm, tirage Crystal Archive II'),
    'pro400h_p1': ('Pro 400H +1 IL', False, 'surexposée 1 IL, tirage compensé'),
    'pro400h_p2': ('Pro 400H +2 IL', False, 'surexposée 2 IL, tirage compensé'),
}
FILMS_NB = tuple(k for k, v in FILMS.items() if v[1])
TABLES = {'kodachrome': 'kodak_kodachrome_64.npz', 'ektachrome': 'kodak_ektachrome_100.npz', 'velvia': 'fujifilm_velvia_100.npz',
          'provia': 'fujifilm_provia_100f.npz', 'ektar': 'kodak_ektar_100_tirage_kodak_portra_endura.npz',
          'pro400h': 'fujifilm_pro_400h_tirage_fujifilm_crystal_archive_typeii.npz',
          'pro400h_p1': 'fujifilm_pro_400h_tirage_fujifilm_crystal_archive_typeii_surex+1.npz',
          'pro400h_p2': 'fujifilm_pro_400h_tirage_fujifilm_crystal_archive_typeii_surex+2.npz'}
# témoins de contrôle, pas des cibles : Portra 400 de spektrafilm tirée sur le papier de l'Ektar et sur celui de la 400H
# (le papier pèse autant que le film sur la saturation), et surexposée comme la 400H
TEMOINS = {'portra_spk': ('Portra 400 témoin', 'spektrafilm, tirage Portra Endura', 'kodak_portra_400_tirage_kodak_portra_endura.npz'),
           'portra_spk_ca': ('Portra 400 témoin', 'spektrafilm, tirage Crystal Archive II',
                             'kodak_portra_400_tirage_fujifilm_crystal_archive_typeii.npz'),
           'portra_spk_ca_p1': ('Portra 400 témoin +1 IL', 'surexposée 1 IL, Crystal Archive II',
                                'kodak_portra_400_tirage_fujifilm_crystal_archive_typeii_surex+1.npz'),
           'portra_spk_ca_p2': ('Portra 400 témoin +2 IL', 'surexposée 2 IL, Crystal Archive II',
                                'kodak_portra_400_tirage_fujifilm_crystal_archive_typeii_surex+2.npz')}
SPK_CLES = set(TABLES) | set(TEMOINS)
GOUT = {'cc_115': (1.15, 0.0), 'cc_130': (1.30, 0.0), 'cc_130_contraste': (1.30, 0.15)}   # (chroma, contraste)
TOLERANCE_RAMPE = 0.01   # L* : les plateaux du Dmax des tables spektrafilm ondulent de 0,001 (interpolation)
# profils Look du preset acheté (produit commercial, absent du dépôt). Variables d'environnement ; sans elles, la cible Pro 400H
# du preset et le témoin Portra sont désactivés :
#   XT4_PROFILS               dossier qui contient les profils .xmp du preset
#   XT4_PROFIL_PRO400H        chemin, dans ce dossier, du profil Look Pro 400H
#   XT4_PROFIL_PORTRA_PRESET  chemin, dans ce dossier, du profil Look Portra (le témoin ; son dossier sert aussi de D750_LOOKS)
PROFILS = pathlib.Path(os.environ.get('XT4_PROFILS') or '<XT4_PROFILS non défini>')
PROFIL_PORTRA_PRESET = os.environ.get('XT4_PROFIL_PORTRA_PRESET') or '<XT4_PROFIL_PORTRA_PRESET non défini>'
PROFILS_CLES = {'fp400h': os.environ.get('XT4_PROFIL_PRO400H') or '<XT4_PROFIL_PRO400H non défini>',
                'portra_preset': PROFIL_PORTRA_PRESET}
# témoin, pas une cible : le preset Portra sur la même base, soit exactement la cible PORTRA du D750
TEMOINS_PROFILS = {'portra_preset': ('Portra du preset, témoin', 'profil du preset, même base : PORTRA du D750')}
HP5_CONSIGNE_IL = 2 / 3   # « Réglage à faire en plus » de la HP5 : exposer +2/3 IL à la prise de vue (correction_hp5)
KODACHROME_CHROMA = 1.2   # « Kodachrome vif » retenu par l'auteur au D750 (choix de goût, d750-analyse-seances.md §3.5 bis)


def _dm():
    import d750_modele as dm
    return dm


def nom(cle):
    return FILMS[cle][:3:2] if cle in FILMS else TEMOINS[cle][:2] if cle in TEMOINS else TEMOINS_PROFILS[cle]


# ---------------------------------------------------------------------------------------------------------------
# 1. Les cibles
# ---------------------------------------------------------------------------------------------------------------
def courbe_trix_preset():
    """Courbe Tri-X des recettes V1 du D40 (preset Tri-X, vérifiée sur les exports de l'auteur) : Y scène → code."""
    import d750_cibles as dc
    return dc.courbe_trix_preset()


def courbe_hp5():
    """Tonalité HP5 « à la manière de l'auteur » du D750 : Y scène → code (d750_analyse.courbe_hp5_scans, modèle de la livraison)."""
    import d750_analyse as da
    m = json.loads((SEANCES / 'modele.json').read_text(encoding='utf-8'))
    _, k, _ = da.matrice_camera()
    return da.courbe_hp5_scans(m, k)


def gout(f, chroma=1.0, contraste=0.0):
    """Variante de goût d'une cible f : a*, b* × chroma ; courbe en S douce sur L* (0, 50 et 100 fixes, pente au gris
    1 + contraste, aux extrémités 1 − 2 contraste)."""
    def g(xyz):
        L = f(xyz)
        x = np.clip(L[..., 0] / 100, 0, 1)
        return np.stack([100 * (x + 4 * contraste * (x - 0.5) * x * (1 - x)), chroma * L[..., 1], chroma * L[..., 2]], -1)
    return g


def table(cle):
    t = SPK / (TABLES[cle] if cle in TABLES else TEMOINS[cle][2])
    if not t.exists():
        raise FileNotFoundError(f'{t} : table spektrafilm absente (d750_spektrafilm.py, variable D750_SPEKTRAFILM)')
    return t


def support(cle):
    """Blanc et noir du support (Lab absolus), gardés dans la table."""
    d = np.load(table(cle))
    return d['blanc'], d['noir']


_CACHE = {}


def profil_sur_base(xmp, base='d750'):
    """Profil Look du preset acheté (table RVB 3D lue dans son .xmp par d750_cibles.table_look, rien recopié) posé sur la
    base que Lightroom met dessous (développement d'Adobe Standard et courbe de Camera Raw).
    base 'd750' (retenue) : la base ajustée sur 20 paires NEF + export du D750 (matrice K et courbe de portra-preset.json,
      d750-analyse-seances.md §3.6), soit la chaîne exacte de d750_cibles.paires pour la cible PORTRA. Elle vaut pour le
      X-T4 : la LookTable d'Adobe Standard est identique octet pour octet sur le X-T4 et le D750, aucun des deux .dcp n'a
      de ProfileToneCurve (Camera Raw met sa courbe par défaut, la même) ; seul l'étalonnage colorimétrique diffère ;
    base 'courbe' : d750_cibles.look_preset sur la seule courbe des neutres de cette base (Y → code), sans sa matrice :
      contrôle de ce que pèse la partie couleur de la base."""
    import d750_cibles as dc
    dm = _dm()
    m = json.loads(dc.PORTRA.read_text(encoding='utf-8'))
    K, c = np.array(m['K']), np.array(m['courbe'])
    if base == 'd750':
        table = dc.table_look(xmp)
        return lambda xyz: dc._lab_affichage(dc.appliquer_look(table, dm.courbe(c, np.asarray(xyz, float) @ K.T)))
    Y = np.r_[0, 0.18 * 2.0 ** np.linspace(-12, 4, 513)]
    T = dm.oetf(np.clip(dm.courbe(c, (Y[:, None] * dm.BLANC) @ K.T)[:, 1], 0, 1) ** 2.2)   # canal vert, code Adobe RGB → sRGB
    return dc.look_preset(xmp, lambda v: np.interp(v, Y, T))


def decalage_gris(f):
    """Décalage d'exposition (IL) qui amène le gris de 18 % de la cible f à L* 49,6 (118/255)."""
    from scipy.optimize import brentq
    blanc = _dm().M709.sum(1)
    return brentq(lambda e: f(0.18 * 2.0 ** e * blanc[None])[0, 0] - L_GRIS, -3, 3)


def fonction(cle, rendu=None):
    """Cible `cle` : fonction XYZ (D65, gris = 0,18) → Lab D65. rendu : celui des cibles spektrafilm (None = RENDU)."""
    rendu = rendu or RENDU
    assert rendu in RENDUS, rendu
    rel = rendu != 'absolu'
    k = (cle, rendu if cle in SPK_CLES else None)
    if k in _CACHE:
        return _CACHE[k]
    import d750_cibles as dc
    import d750_spektrafilm as sp
    if cle == 'trix':
        f = dc.cible_nb(dc.MELANGES['preset_trix'], courbe_trix_preset())
    elif cle == 'hp5':
        f = dc.cible_nb('hp5_fiche', courbe_hp5())
    elif cle == 'hp5_consigne':
        g = fonction('hp5')
        f = lambda xyz, g=g: g(np.asarray(xyz, float) * 2.0 ** -HP5_CONSIGNE_IL)
    elif cle == 'fp4':
        f = dc.cible_nb('fp4_fiche', dc.courbe_film('fp4'))
    elif cle == 'portra':
        f = dc.melange_film(dc.paires(dc.PORTRA_REGLE), json.loads(dc.PORTRA_ESPRIT.read_text(encoding='utf-8')))
    elif cle == 'classic_chrome':
        f = dc.fuji('CLASSIC-CHROME')
    elif cle in PROFILS_CLES:
        f = profil_sur_base(PROFILS / PROFILS_CLES[cle])
    elif cle in GOUT:
        f = gout(fonction('classic_chrome'), *GOUT[cle])
    elif cle == 'kodachrome':
        f = sp.cible(table(cle), chroma=KODACHROME_CHROMA, relatif_=rel)
    elif cle in SPK_CLES:
        f = sp.cible(table(cle), relatif_=rel)
    else:
        raise KeyError(cle)
    if cle in SPK_CLES and rendu == 'relatif_gris':
        e, g = decalage_gris(f), f
        f = lambda xyz, g=g, e=e: g(np.asarray(xyz, float) * 2.0 ** e)
        f.decalage_IL = e
    _CACHE[k] = f
    return f


def disponibles():
    """Clés dont la cible peut être construite ici (tables spektrafilm présentes)."""
    return [k for k in FILMS if (k not in TABLES or (SPK / TABLES[k]).exists())
            and (k not in PROFILS_CLES or (PROFILS / PROFILS_CLES[k]).exists())]


def cibles(y18, films=None, rendu=None):
    """Lab cible de chaque bloc des RAF du chantier de xt4_mesure, pour chaque film : ({film: {raf: Lab}}, {raf: Lab de
    la scène}), comme xt4_mesure.cibles (mêmes clés trix, hp5, fp4, portra, plus les autres)."""
    import xt4_mesure as xm
    dm = _dm()
    fs = {c: fonction(c, rendu) for c in (films or disponibles())}
    out, sc = {c: {} for c in fs}, {}
    for n, d in xm.charger_blocs().items():
        _, X = xm.scene(d, y18)
        sc[n] = dm.xyz_lab(X)
        for c, f in fs.items():
            out[c][n] = f(X)
    return out, sc


# ---------------------------------------------------------------------------------------------------------------
# 2. Images entières (planches)
# ---------------------------------------------------------------------------------------------------------------
def scene_image(n, y18, taille=None):
    """XYZ (D65, gris = 0,18) de l'image entière du RAF n, par xt4_mesure.image_cible elle-même (géométrie du JPEG du
    boîtier, lissage, échelle d'exposition) : sa cible couleur (d750_cibles.paires) est remplacée, le temps de l'appel, par
    une fonction qui garde le XYZ qu'elle reçoit."""
    import xt4_mesure as xm
    import d750_cibles as dc
    taille = taille or xm.TUILE
    pris = {}

    def garder(xyz):
        pris['xyz'] = np.array(xyz, float)
        return np.tile([50.0, 0, 0], (len(pris['xyz']), 1))
    vieux = dc.paires
    dc.paires = lambda *a, **k: garder
    try:
        xm.image_cible(n, 'portra', y18, taille)
    finally:
        dc.paires = vieux
    if 'xyz' not in pris:
        raise RuntimeError("xt4_mesure.image_cible n'appelle plus d750_cibles.paires : adapter scene_image")
    return pris['xyz'].reshape(taille[1], taille[0], 3)


def rendre(xyz, cle, rendu=None):
    """XYZ (…, 3) → codes 8 bits sRGB de la cible."""
    dm = _dm()
    code = dm.lab_code(fonction(cle, rendu)(xyz.reshape(-1, 3)))
    return (np.clip(code, 0, 1) * 255 + 0.5).astype(np.uint8).reshape(xyz.shape)


def image(n, cle, y18, taille=None, rendu=None):
    return rendre(scene_image(n, y18, taille), cle, rendu)


# ---------------------------------------------------------------------------------------------------------------
# 3. Contrôles : gris, rampe, ColorChecker
# ---------------------------------------------------------------------------------------------------------------
def colorchecker():
    """24 plages ColorChecker (moyenne BabelColor, spectres de colour-science) sous D65, observateur 2°, réflectance = Y
    (le gris neutral 5 à Y ≈ 0,19 : l'échelle des cibles)."""
    import colour
    cc = colour.SDS_COLOURCHECKERS['BabelColor Average']
    cmfs = colour.MSDS_CMFS['CIE 1931 2 Degree Standard Observer']
    ill = colour.SDS_ILLUMINANTS['D65']
    noms = list(cc)
    return noms, np.array([colour.sd_to_XYZ(cc[k], cmfs=cmfs, illuminant=ill) / 100 for k in noms])


def _teinte(lab):
    return np.degrees(np.arctan2(lab[..., 2], lab[..., 1])) % 360


def _dh(a, b):
    return (b - a + 180) % 360 - 180


def controle_une(cle, noms, X, rendu=None):
    dm = _dm()
    f = fonction(cle, rendu)
    blanc = dm.M709.sum(1)
    il = np.arange(-8, 4.001, 1 / 8)
    rampe = f(0.18 * 2.0 ** il[:, None] * blanc)
    gris = f(0.18 * blanc[None])[0]
    lab = f(X)
    sc = dm.xyz_lab(X)
    chrom = np.arange(18)
    Cs, Ct = np.hypot(sc[chrom, 1], sc[chrom, 2]), np.hypot(lab[chrom, 1], lab[chrom, 2])
    dh = _dh(_teinte(sc[chrom]), _teinte(lab[chrom]))
    code = dm.lab_code(lab)
    pl = {noms[i]: {'L': round(float(lab[i, 0]), 1), 'a': round(float(lab[i, 1]), 1), 'b': round(float(lab[i, 2]), 1),
                    'C_sur_scene': round(float(Ct[i] / Cs[i]), 2) if i < 18 else None,
                    'dh': round(float(dh[i]), 1) if i < 18 and Ct[i] > 1 else None}   # pas de teinte sur un gris
          for i in range(len(noms))}
    milieu = (rampe[:, 0] > 10) & (rampe[:, 0] < 90)
    out = {
        'gris_18': {'L': round(float(gris[0]), 2), 'a': round(float(gris[1]), 2), 'b': round(float(gris[2]), 2)},
        'rampe_monotone': bool(np.all(np.diff(rampe[:, 0]) >= -TOLERANCE_RAMPE)),
        'rampe_descente_max': round(float(max(0.0, -np.diff(rampe[:, 0]).min())), 4),
        'rampe_L_par_IL': {f'{e:+g}': round(float(np.interp(e, il, rampe[:, 0])), 1) for e in (-6, -4, -3, -2, -1, 0, 1, 2, 3, 4)},
        'neutres_a_b_max_L10_90': [round(float(np.abs(rampe[milieu, 1]).max()), 2), round(float(np.abs(rampe[milieu, 2]).max()), 2)],
        'neutres_b_moyen_L10_90': round(float(rampe[milieu, 2].mean()), 2),
        'ombres_a_b_L8_40': [round(float(v), 2) for v in rampe[(rampe[:, 0] > 8) & (rampe[:, 0] < 40), 1:].mean(0)],
        'L_max': round(float(rampe[:, 0].max()), 1), 'L_min': round(float(rampe[:, 0].min()), 1),
        'chroma_sur_scene_mediane': round(float(np.median(Ct / Cs)), 3),
        'dh_moyen_abs': round(float(np.mean(np.abs(dh))), 1) if np.all(Ct > 1) else None,
        'hors_srgb': int(((code < -1e-3) | (code > 1 + 1e-3)).any(1)[chrom].sum()),
        'plages': pl,
    }
    if cle in SPK_CLES:
        b, n = support(cle)
        out['support'] = {'blanc_absolu': [round(float(v), 1) for v in b], 'noir_absolu': [round(float(v), 1) for v in n]}
        if hasattr(f, 'decalage_IL'):
            out['decalage_gris_IL'] = round(float(f.decalage_IL), 2)
    return out


def controle():
    noms, X = colorchecker()
    out = {'date': DATE, 'colorchecker': 'BabelColor Average, D65, 2°', 'tables': str(SPK),
           'rendu_spektrafilm': RENDU, 'cibles': {}}
    cles = disponibles() + [t for t in TEMOINS if (SPK / TEMOINS[t][2]).exists()] \
        + [t for t in TEMOINS_PROFILS if (PROFILS / PROFILS_CLES[t]).exists()]
    for c in cles:
        r = controle_une(c, noms, X)
        if c in SPK_CLES:
            r['autres_rendus'] = {}
            for ar in RENDUS:
                if ar != RENDU:
                    a = controle_une(c, noms, X, rendu=ar)
                    r['autres_rendus'][ar] = {k: a[k] for k in ('gris_18', 'rampe_L_par_IL', 'L_max', 'L_min', 'chroma_sur_scene_mediane',
                                                               'neutres_b_moyen_L10_90', 'ombres_a_b_L8_40')}
        out['cibles'][c] = r
        g = r['gris_18']
        s = ''.join(f" | {ar} : gris L {v['gris_18']['L']:4.1f} b {v['gris_18']['b']:+4.1f}, L max {v['L_max']:5.1f}"
                    for ar, v in r.get('autres_rendus', {}).items()) + (f" | décalage {r['decalage_gris_IL']:+.2f} IL" if 'decalage_gris_IL' in r else '')
        print(f"{c:17s} gris L {g['L']:5.1f} a {g['a']:+5.1f} b {g['b']:+5.1f} | rampe {'ok' if r['rampe_monotone'] else 'NON'} "
              f"L {r['L_min']:4.1f}..{r['L_max']:5.1f} | neutres max |a| {r['neutres_a_b_max_L10_90'][0]:4.1f} |b| "
              f"{r['neutres_a_b_max_L10_90'][1]:4.1f} b moy {r['neutres_b_moyen_L10_90']:+4.1f} | C/scène {r['chroma_sur_scene_mediane']:.2f}"
              f" | hors sRGB {r['hors_srgb']}{s}")
    out['descriptions'] = verifier_descriptions(out['cibles'], noms, X)
    for k, v in out['descriptions'].items():
        print(f"{k:12s} {v['plausible'] if v['plausible'] == 'partiel' else 'oui' if v['plausible'] else 'NON'} : {v['constat']}")
    DONNEES.mkdir(parents=True, exist_ok=True)
    (DONNEES / f'xt4-cibles-controle-{DATE}.json').write_text(json.dumps(out, indent=1, ensure_ascii=False))
    return out


def verifier_descriptions(c, noms, X):
    """Face aux descriptions connues : Velvia saturée, Ektachrome froide et neutre, Ektar saturée, 400H pastel et tirant
    vers le cyan-vert (aussi surexposée de 1 et 2 IL). Comparaisons relatives entre films simulés de la même façon
    (diapositives entre elles, négatifs entre eux sur le même papier), pas des seuils absolus."""
    dm = _dm()
    out = {}
    if not all(k in c for k in ('velvia', 'provia', 'ektachrome', 'ektar', 'pro400h')):
        return out
    s = {k: c[k]['chroma_sur_scene_mediane'] for k in c}
    out['velvia'] = {'plausible': s['velvia'] > max(s['provia'], s['ektachrome']),
                     'constat': f"chroma / scène {s['velvia']:.2f} contre Provia {s['provia']:.2f}, Ektachrome {s['ektachrome']:.2f}"}
    be, bp = c['ektachrome']['neutres_b_moyen_L10_90'], c['provia']['neutres_b_moyen_L10_90']
    bk = c['kodachrome']['neutres_b_moyen_L10_90'] / KODACHROME_CHROMA if 'kodachrome' in c else float('nan')
    ge = c['ektachrome']['gris_18']
    neutre = abs(ge['a']) < 2 and abs(ge['b']) < 2
    out['ektachrome'] = {'plausible': (neutre and be < bk) and (True if be < bp else 'partiel'),
                         'constat': f"b* moyen des neutres {be:+.1f} (Provia {bp:+.1f}, Kodachrome sans le × 1,2 {bk:+.1f}) ; "
                                    f"gris a* {ge['a']:+.1f} b* {ge['b']:+.1f} ; chroma / scène {s['ektachrome']:.2f}"}
    pe, pc = s.get('portra_spk'), s.get('portra_spk_ca')   # Portra 400 sur Portra Endura (papier de l'Ektar), sur Crystal Archive (400H)
    out['ektar'] = {'plausible': pe is not None and s['ektar'] > pe,
                    'constat': f"chroma / scène {s['ektar']:.2f} contre Portra 400 sur le même papier {pe:.2f}"}
    for k, t in (('pro400h', 'portra_spk_ca'), ('pro400h_p1', 'portra_spk_ca_p1'), ('pro400h_p2', 'portra_spk_ca_p2')):
        if k not in c or t not in c:
            continue
        o4, op = c[k]['ombres_a_b_L8_40'], c[t]['ombres_a_b_L8_40']
        e = dm.de2000(fonction(k)(X), fonction(t)(X))
        out[k] = {'plausible': s[k] < s[t] and o4[0] < op[0] - 1,
                  'constat': f"chroma / scène {s[k]:.2f} contre Portra 400 traitée de même {s[t]:.2f} ; ombres (L* 8 à 40) a* "
                             f"{o4[0]:+.1f} b* {o4[1]:+.1f} contre {op[0]:+.1f} {op[1]:+.1f} (a* < 0 : vert) ; ΔE2000 à cette Portra "
                             f"sur la mire {np.median(e):.1f} (max {e.max():.1f})"}
    if 'fp400h' in c and 'portra_preset' in c:   # profils du preset posés sur la même base : 400H contre le preset Portra
        f4, fp = c['fp400h'], c['portra_preset']
        o4, op = f4['ombres_a_b_L8_40'], fp['ombres_a_b_L8_40']
        r4, rp = f4['rampe_L_par_IL'], fp['rampe_L_par_IL']
        pastel = s['fp400h'] < s['portra_preset'] and r4['-2'] > rp['-2']
        out['fp400h'] = {'plausible': pastel and o4[0] < op[0] - 1,
                         'constat': f"chroma / scène {s['fp400h']:.2f} contre le preset Portra sur la même base {s['portra_preset']:.2f} ; L* à −2 IL "
                                    f"{r4['-2']:.1f} contre {rp['-2']:.1f} (ombres relevées) ; gris L* {f4['gris_18']['L']:.1f} contre "
                                    f"{fp['gris_18']['L']:.1f} ; ombres (L* 8 à 40) a* {o4[0]:+.1f} b* {o4[1]:+.1f} contre {op[0]:+.1f} {op[1]:+.1f}"}
    return out


# ---------------------------------------------------------------------------------------------------------------
# 4. Sur les blocs des 16 RAF : anciennes cibles contre nouvelles, absolu contre relatif, 400H surexposée, HP5 ;
#    recettes déjà rendues notées à nouveau (sans le boîtier)
# ---------------------------------------------------------------------------------------------------------------
def _cache():
    """Rendus du premier passage (cache du chantier), sans ouvrir le boîtier : seules les recettes déjà rendues servent."""
    import xt4_mesure as xm
    R = xm.Rendus.__new__(xm.Rendus)
    R.blocs, R.cache, R.banc = xm.charger_blocs(), xm.CHANTIER / 'cache', None
    return R


def _livrees():
    import xt4_mesure as xm
    out = {}
    for f, n in (('trix', 'XT4 Tri-X 400 mesure'), ('hp5', 'XT4 HP5 Plus mesure'), ('fp4', 'XT4 FP4 Plus mesure'), ('portra', 'XT4 Portra 400 mesure')):
        p = xm.RECETTES / f'{n}.FP1'
        if p.exists():
            r = xm.lire_fp1(p)
            out[f] = dict({k: v for k, v in r.items() if k not in ('nom', 'source', 'kelvin')}, wb=0, grain=1)
    return out


def _ecart(A, B, nb=False):
    import xt4_mesure as xm
    dm = _dm()
    return xm.resume({n: (np.abs(A[n][:, 0] - B[n][:, 0]) if nb else dm.de2000(A[n], B[n])) for n in A})


def correction_hp5(y18):
    """Surexposition à la prise de vue (IL) qui amène le gris de 18 % au L* de la cible HP5 (gris des scans de l'auteur), avec une
    courbe normale : (1) la courbe HP5 de la fiche Ilford et du tirage grade 2 (gris à 118/255) ; (2) les rendus du X-T4
    déjà faits (cache) : Acros neutre et la HP5 livrée, sur les blocs peu colorés des 16 RAF (L* médian par tranche de
    1/6 IL de la scène). Arrondi au tiers d'IL. Résidu : écart de forme qui reste entre la courbe décalée et la cible."""
    import xt4_mesure as xm
    from scipy.optimize import brentq
    dm = _dm()
    blanc = dm.M709.sum(1)
    Lg = float(fonction('hp5')(0.18 * blanc[None])[0, 0])
    out = {'L_gris_cible': round(Lg, 2), 'courbes': {}}

    def L_fiche(v):
        return dm.code_lab(np.repeat(xm.courbe_nb('hp5_fiche', np.asarray(v, float))[..., None], 3, -1))[..., 0]
    d = brentq(lambda e: L_fiche(np.array([0.18 * 2 ** e]))[0] - Lg, -2, 4)
    il = np.arange(-3, 2.51, 0.25)
    res = np.abs(fonction('hp5')(0.18 * 2.0 ** il[:, None] * blanc)[:, 0] - L_fiche(0.18 * 2.0 ** (il + d)))
    out['courbes']['fiche Ilford + tirage grade 2 (courbe normale)'] = {'IL': round(float(d), 2), 'residu_forme_median_L': round(float(np.median(res)), 1)}
    R = _cache()
    recs = {'Acros neutre (X-T4)': dict(xm.NEUTRE, sim=12)}
    lv = _livrees()
    if 'hp5' in lv:
        recs['HP5 livrée le 29/10 (X-T4)'] = lv['hp5']
    x, L = {k: [] for k in recs}, {k: [] for k in recs}
    for n, b in R.blocs.items():
        _, X = xm.scene(b, y18)
        lab = dm.xyz_lab(X)
        m = np.hypot(lab[:, 1], lab[:, 2]) < 6
        for k, r in recs.items():
            if R.chemin(n, r).exists():
                x[k].append(np.log2(np.maximum(X[m, 1], 1e-6) / 0.18))
                L[k].append(dm.code_lab(R.moyennes(n, r)[m] / 255)[:, 0])
    for k in recs:
        if not x[k]:
            continue
        xx, LL = np.concatenate(x[k]), np.concatenate(L[k])
        bords = np.arange(-3, 3.01, 1 / 6)
        cx, cL = [], []
        for a, b in zip(bords[:-1], bords[1:]):
            s = (xx >= a) & (xx < b)
            if s.sum() >= 15:
                cx.append((a + b) / 2)
                cL.append(np.median(LL[s]))
        cL = np.maximum.accumulate(np.array(cL))
        out['courbes'][k] = {'IL': round(float(np.interp(Lg, cL, cx)), 2), 'blocs': int(len(xx)), 'L_gris_sans_correction': round(float(np.interp(0, cx, cL)), 1)}
    v = [c['IL'] for c in out['courbes'].values()]
    out['retenue_IL'] = round(round(float(np.median(v)) * 3) / 3, 2)
    out['retenue_texte'] = {0: '0', 1: '+1/3', 2: '+2/3', 3: '+1', 4: '+1 1/3', 5: '+1 2/3', 6: '+2'}.get(int(round(out['retenue_IL'] * 3)), f"{out['retenue_IL']:+.2f}")
    return out


def _sur_blocs(y18, f):
    """Une fonction cible appliquée aux blocs des RAF du chantier : ({raf: Lab}, {raf: XYZ})."""
    import xt4_mesure as xm
    out, sc = {}, {}
    for n, d in xm.charger_blocs().items():
        _, X = xm.scene(d, y18)
        out[n], sc[n] = f(X), X
    return out, sc


def comparer():
    import xt4_mesure as xm
    dm = _dm()
    et = json.loads((xm.CHANTIER / 'etalonnage.json').read_text())
    y18 = et['y18']
    vieilles, _ = xm.cibles(y18)
    neuves, sc = cibles(y18)
    out = {'date': DATE, 'y18': y18, 'anciennes_contre_nouvelles': {}, 'rendu_retenu': RENDU, 'autres_rendus_contre_retenu': {}, 'pro400h_surex': {},
           'correction_hp5': None, 'recettes_rendues': {}}
    for f in ('trix', 'hp5', 'fp4', 'portra'):
        dL = np.concatenate([neuves[f][n][:, 0] - vieilles[f][n][:, 0] for n in neuves[f]])
        out['anciennes_contre_nouvelles'][f] = {**_ecart(vieilles[f], neuves[f], f in FILMS_NB),
                                                'dL_signe_median': round(float(np.median(dL)), 1), 'unite': '|ΔL*|' if f in FILMS_NB else 'ΔE2000'}
        print('ancienne/nouvelle', f, out['anciennes_contre_nouvelles'][f])
    # autres rendus contre le rendu retenu (cibles spektrafilm), dont l'absolu du Kodachrome du D750
    chroma = lambda T: float(np.median(np.concatenate([np.hypot(T[n][:, 1], T[n][:, 2]) for n in T])))
    for ar in RENDUS:
        if ar == RENDU:
            continue
        autres, _ = cibles(y18, [k for k in TABLES if k in neuves], rendu=ar)
        for k, A in autres.items():
            dL = np.concatenate([neuves[k][n][:, 0] - A[n][:, 0] for n in A])
            out['autres_rendus_contre_retenu'].setdefault(k, {})[ar] = {
                **_ecart(A, neuves[k]), 'dL_retenu_moins_autre_median': round(float(np.median(dL)), 1),
                'chroma_mediane_autre': round(chroma(A), 1), 'chroma_mediane_retenu': round(chroma(neuves[k]), 1)}
            print(ar, '/', RENDU, k, out['autres_rendus_contre_retenu'][k][ar])
    # 400H surexposée contre la Portra 400 traitée de même (même papier), et contre la 400H sans surexposition
    tem, _ = cibles(y18, [t for t in TEMOINS if (SPK / TEMOINS[t][2]).exists()])
    for k, t in (('pro400h', 'portra_spk_ca'), ('pro400h_p1', 'portra_spk_ca_p1'), ('pro400h_p2', 'portra_spk_ca_p2')):
        if k in neuves and t in tem:
            out['pro400h_surex'][k] = {'contre_portra_meme_traitement': _ecart(neuves[k], tem[t]),
                                       'contre_portra_sans_surex': _ecart(neuves[k], tem['portra_spk_ca']),
                                       'contre_400h_sans_surex': _ecart(neuves[k], neuves['pro400h']),
                                       'chroma_mediane': round(chroma(neuves[k]), 1), 'chroma_mediane_portra': round(chroma(tem[t]), 1)}
            print('400H', k, out['pro400h_surex'][k])
    # Pro 400H du preset (profil du preset) : contrôle de la base sur le preset Portra contre la cible PORTRA du D750, écarts aux autres cibles
    if 'fp400h' in neuves:
        import d750_cibles as dc
        os.environ.setdefault('D750_LOOKS', str((PROFILS / PROFIL_PORTRA_PRESET).parent))
        portra_d750, _ = _sur_blocs(y18, dc.paires(dc.PORTRA))
        portra_profil = PROFILS / PROFIL_PORTRA_PRESET
        q = {'controle_portra_preset_contre_portra_d750': {
                 'base_d750': _ecart(_sur_blocs(y18, profil_sur_base(portra_profil, 'd750'))[0], portra_d750),
                 'courbe_neutre_seule': _ecart(_sur_blocs(y18, profil_sur_base(portra_profil, 'courbe'))[0], portra_d750),
                 'profiletonecurve_du_dcp': 'absente : ni Fujifilm X-T4 ni Nikon D750 Adobe Standard.dcp n\'en ont'},
             'base_retenue': 'base_d750'}
        fc, _ = _sur_blocs(y18, profil_sur_base(PROFILS / PROFILS_CLES['fp400h'], 'courbe'))
        q['fp400h_base_courbe_contre_base_d750'] = _ecart(fc, neuves['fp400h'])
        for k in ('pro400h', 'pro400h_p1', 'pro400h_p2', 'portra'):
            if k in neuves:
                q[f'contre_{k}'] = _ecart(neuves['fp400h'], neuves[k])
        q['contre_portra_preset_meme_base'] = _ecart(neuves['fp400h'], portra_d750)
        q['chroma_mediane'] = {'fp400h': round(chroma(neuves['fp400h']), 1), 'portra_preset': round(chroma(portra_d750), 1),
                               'portra': round(chroma(neuves['portra']), 1)}
        out['fp400h'] = q
        print('Pro 400H du preset', q)
    out['correction_hp5'] = correction_hp5(y18)
    print('HP5', out['correction_hp5'])
    # recettes déjà rendues par le boîtier (cache du premier passage), notées contre les nouvelles cibles ; rien n'est rendu
    R = _cache()
    best = json.loads((xm.CHANTIER / 'meilleures.json').read_text())
    nb, portra = xm.presets_existants()
    livrees = _livrees()
    noms = list(R.blocs)
    for f in ('trix', 'hp5', 'hp5_consigne', 'fp4', 'portra'):
        fb = 'hp5' if f == 'hp5_consigne' else f
        cands = {'trouvée au premier passage': best[fb]['recette']}
        if fb in livrees:
            cands['livrée (.FP1, grain coupé)'] = livrees[fb]
        for r in (portra if f == 'portra' else nb):
            cands[r['nom']] = xm.pour_mesure(r)
        lig = []
        for k, r in cands.items():
            if not all(R.chemin(n, r).exists() for n in noms):
                continue
            e = {}
            for n in noms:
                L = dm.code_lab(R.moyennes(n, r) / 255)
                T = neuves[f][n]
                e[n] = np.abs(L[:, 0] - T[:, 0]) if f in FILMS_NB else dm.de2000(L, T)
            lig.append({'recette': k, 'reglages': xm.recette_txt(r), **xm.resume(e)})
        lig.sort(key=lambda x: x['score'])
        out['recettes_rendues'][f] = lig
        for x in lig[:3]:
            print(f"  {f} {x['score']:.2f} {x['mediane']:.2f} ({x['p90']:.1f}) {x['recette']} : {x['reglages']}")
    DONNEES.mkdir(parents=True, exist_ok=True)
    (DONNEES / f'xt4-cibles-comparaison-{DATE}.json').write_text(json.dumps(out, indent=1, ensure_ascii=False))
    return out


# ---------------------------------------------------------------------------------------------------------------
# 5. Planche : chaque cible seule, sur 3 RAF communs, nom de la colonne dans l'image
# ---------------------------------------------------------------------------------------------------------------
PLANCHE_RAF = ['167-DSCF0467', '176-DSCF0476', '159-DSCF9414']   # peau et rouge ; couleurs mêlées ; verts et ciel
# une colonne = une clé, ou (clé, rendu) pour montrer un autre rendu spektrafilm que RENDU
BANDES = [('Cibles reprises du D750 et du D40 (Kodachrome dans le rendu retenu, puis tel que le D750 le visait)',
           ['trix', 'hp5', 'fp4', 'portra', 'classic_chrome', 'kodachrome', ('kodachrome', 'absolu')]),
          ('Classic Chrome plus coloré (choix de goût, rien de mesuré) et diapositives (spektrafilm)',
           ['cc_115', 'cc_130', 'cc_130_contraste', 'ektachrome', 'velvia', 'provia']),
          ('Négatifs : Pro 400H du preset (profil du preset, retenue) ; spektrafilm : Ektar, Pro 400H surexposée, Portra 400 témoin traitée de même',
           ['fp400h', 'ektar', 'pro400h', 'pro400h_p1', 'pro400h_p2', 'portra_spk_ca', 'portra_spk_ca_p2'])]


def planche(taille=(440, 293), sortie=None):
    from PIL import Image, ImageDraw
    import xt4_mesure as xm
    et = json.loads((xm.CHANTIER / 'etalonnage.json').read_text())
    scenes = {n: scene_image(n, et['y18'], taille) for n in PLANCHE_RAF}
    W, H = taille
    m, haut_titre, haut_bande, haut_col = 12, 70, 44, 58
    ncol = max(len(b[1]) for b in BANDES)
    hb = haut_bande + haut_col + len(PLANCHE_RAF) * (H + m)
    img = Image.new('RGB', (ncol * (W + m) + m, haut_titre + len(BANDES) * hb + 40), 'white')
    dr = ImageDraw.Draw(img)
    p0, p1, p2, p3 = xm._police(30), xm._police(22), xm._police(17), xm._police(15)
    dr.text((m, 12), 'X-T4 : cibles de rendu des recettes, rendues par la cible seule (pas par le boîtier)', fill='black', font=p0)
    dr.text((m, 46), f'3 RAF du banc, même exposition (gris de 18 % rendu 118/255 par le Provia neutre du boîtier) ; spektrafilm en '
            f'rendu relatif, gris recalé (blanc du film ou du papier = blanc, gris de 18 % à 118/255) · {DATE}', fill=(80, 80, 80), font=p3)
    y0 = haut_titre
    for titre, cles in BANDES:
        dr.text((m, y0 + 10), titre, fill=(30, 30, 30), font=p1)
        for k, c in enumerate(cles):
            x = m + k * (W + m)
            c, rendu = c if isinstance(c, tuple) else (c, None)
            t1, t2 = nom(c)
            if rendu == 'absolu':
                t1, t2 = t1 + ' absolu', 'cible du D750 : support non blanc'
            dr.text((x, y0 + haut_bande), t1.upper(), fill='black', font=p1)
            dr.text((x, y0 + haut_bande + 28), t2, fill=(70, 70, 70), font=p3)
            for i, n in enumerate(PLANCHE_RAF):
                y = y0 + haut_bande + haut_col + i * (H + m)
                img.paste(Image.fromarray(rendre(scenes[n], c, rendu)), (x, y))
                if k == 0:
                    t = n[:3]
                    tw = dr.textlength(t, font=p2)
                    dr.rectangle((x + 6, y + H - 30, x + 14 + tw, y + H - 6), fill='white')
                    dr.text((x + 10, y + H - 28), t, fill='black', font=p2)
        y0 += hb
    dr.text((m, y0 + 8), 'Kodachrome, Ektachrome, Velvia, Provia, Ektar, Pro 400H, Portra 400 témoin : film modeling powered by '
            'spektrafilm (A. Volpato ; code GPLv3, profils CC BY-SA 4.0). Négatifs : tirage simulé sur le papier conseillé par le '
            'profil ; surexposition compensée au tirage. Pro 400H du preset : table du profil du preset acheté sur la base d\'Adobe ajustée au D750.',
            fill=(70, 70, 70), font=p3)
    sortie = pathlib.Path(sortie or FIGURES / f'xt4-cibles-{DATE}.jpg')
    sortie.parent.mkdir(parents=True, exist_ok=True)
    img.save(sortie, quality=88)
    print(sortie, img.size)
    return sortie


# ---------------------------------------------------------------------------------------------------------------
# 6. Contrôles automatiques
# ---------------------------------------------------------------------------------------------------------------
def self_test():
    import d750_spektrafilm as sp
    dm = _dm()
    blanc = dm.M709.sum(1)
    gris = 0.18 * blanc[None]
    attendu = {'trix': 49.5, 'fp4': 49.3, 'classic_chrome': 49.4, 'portra': 57.2, 'hp5': 68.3}
    assert abs(fonction('hp5_consigne')(gris * 2.0 ** HP5_CONSIGNE_IL)[0, 0] - 68.3) < 0.05   # la consigne ramène le gris
    # valeurs relevées le 29/10/2026 sur les cibles du D750 : rien n'a bougé en amont ; Kodachrome du D750 = absolu
    assert abs(fonction('kodachrome', rendu='absolu')(gris)[0, 0] - 49.3) < 0.3
    il = np.arange(-8, 4.001, 0.25)
    for c in disponibles() + [t for t in TEMOINS if (SPK / TEMOINS[t][2]).exists()]:
        L = fonction(c)(gris)[0]
        assert np.all(np.isfinite(L)), c
        if c in FILMS_NB:
            assert abs(L[1]) < 1e-6 and abs(L[2]) < 1e-6, (c, L)
        if c in attendu:
            assert abs(L[0] - attendu[c]) < 0.3, (c, L[0], attendu[c])
        r = fonction(c)(0.18 * 2.0 ** il[:, None] * blanc)
        assert np.all(np.diff(r[:, 0]) >= -TOLERANCE_RAMPE), (c, 'rampe de gris non monotone')
        if c in SPK_CLES:
            b, _ = support(c)
            assert np.allclose(sp.relatif(b[None], b)[0], [100, 0, 0], atol=1e-6), (c, 'blanc du support')
            rr = fonction(c, 'relatif')(0.18 * 2.0 ** il[-1:, None] * blanc)
            assert rr[0, 0] > 99, (c, 'blanc relatif non atteint à +4 IL', rr[0, 0])
            if RENDU == 'relatif_gris':
                assert abs(L[0] - L_GRIS) < 0.05, (c, 'gris non recalé', L[0])
            if c != 'kodachrome':
                assert abs(L[1]) < 3 and abs(L[2]) < 3, (c, 'gris trop teinté', L)
            sx = float(np.load(table(c))['surex'])
            assert sx == (1.0 if c.endswith('_p1') else 2.0 if c.endswith('_p2') else 0.0), (c, sx)
    # Pro 400H du preset : la chaîne de profil_sur_base redonne exactement la cible PORTRA du D750 avec le profil du preset Portra ;
    # le fondement de la base retenue (Adobe Standard du X-T4 et du D750 : même LookTable, pas de courbe) est relu
    if all((PROFILS / p).exists() for p in PROFILS_CLES.values()):
        import d750_cibles as dc
        os.environ.setdefault('D750_LOOKS', str((PROFILS / PROFIL_PORTRA_PRESET).parent))
        xx = np.random.default_rng(1).uniform(0, 1.2, (500, 3)) @ dm.M709.T
        assert np.abs(profil_sur_base(PROFILS / PROFIL_PORTRA_PRESET)(xx) - dc.paires(dc.PORTRA)(xx)).max() < 1e-9, 'base D750 ≠ PORTRA'
        assert abs(fonction('fp400h')(gris)[0, 0] - 59.5) < 0.3, fonction('fp400h')(gris)
    d = pathlib.Path('/Library/Application Support/Adobe/CameraRaw/CameraProfiles/Adobe Standard')
    if (d / 'Fujifilm X-T4 Adobe Standard.dcp').exists() and (d / 'Nikon D750 Adobe Standard.dcp').exists():
        import dcp
        a, b = (dcp.lire(d / f'{m} Adobe Standard.dcp') for m in ('Fujifilm X-T4', 'Nikon D750'))
        assert a['ProfileLookTableData'] == b['ProfileLookTableData'], 'LookTable différentes'
        assert 'ProfileToneCurve' not in a and 'ProfileToneCurve' not in b, 'un .dcp a une courbe'
    # variantes de goût : chroma exacte sur une couleur, gris et extrémités de L* inchangés
    x = np.array([[0.25, 0.18, 0.06]])
    cc = fonction('classic_chrome')(x)[0]
    for c, (k, t) in GOUT.items():
        v = fonction(c)(x)[0]
        assert np.allclose(v[1:], k * cc[1:]), c
        if t == 0:
            assert abs(v[0] - cc[0]) < 1e-9, c
    g = gout(lambda xyz: np.array([[0.0, 0, 0], [50, 0, 0], [100, 0, 0], [25, 0, 0]]), 1.0, 0.15)(None)
    assert np.allclose(g[:3, 0], [0, 50, 100]) and g[3, 0] < 25, g
    # interface de xt4_mesure.cibles, sur un RAF, si le chantier est là
    try:
        import xt4_mesure as xm
        et = json.loads((xm.CHANTIER / 'etalonnage.json').read_text())
        n, d = next(iter(xm.charger_blocs().items()))
    except (FileNotFoundError, StopIteration):
        print('chantier X-T4 absent : interface non vérifiée')
    else:
        _, X = xm.scene(d, et['y18'])
        for c in ('trix', 'hp5', 'fp4', 'portra'):
            assert fonction(c)(X).shape == (len(X), 3), c
    print(f'self-test OK ({len(disponibles())} cibles, rendu spektrafilm {RENDU} : {", ".join(disponibles())})')


if __name__ == '__main__':
    a = sys.argv[1:]
    if not a or a[0] in ('-h', '--help'):
        print(__doc__)
        sys.exit(2)
    if a[0] == '--self-test':
        self_test()
    else:
        globals()[a[0]]()
