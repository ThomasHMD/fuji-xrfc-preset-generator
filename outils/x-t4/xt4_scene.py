#!/usr/bin/env python3
# SPDX-License-Identifier: CC-BY-NC-4.0
# Copyright (c) 2026 Thomas Hammoudi
"""Scène XYZ (D65) estimée depuis un RAF du X-T4 : remplace la seule ColorMatrix D65 de xt4_mesure.lineaire.
Voir docs/methode.md.

Toutes les méthodes prennent le RVB caméra équilibré (balance de la vue, vert = 1) et rendent un XYZ adapté à D65
(Bradford), un neutre allant sur le blanc D65 :
  cm-d65        (a) ColorMatrix D65 d'Adobe (table adobe_coeff de LibRaw), à la dcraw : l'ancienne méthode ;
  fm-dng        (b) ForwardMatrix 1 (lumière A) et 2 (D65) d'Adobe Standard, interpolées selon la balance de la vue
                    comme le fait la norme DNG (température par Robertson, poids en 1/T), puis D50 → D65 ;
  fm-dng-hsm    (c) (b) + HueSatMap d'Adobe Standard (table 90 × 30, appliquée en ProPhoto linéaire) : pas une matrice ;
  fm-dng-hsm-lin    (b) + HueSatMap du profil « Linear-Fujifilm X-T4 » (tiers, dérivé d'Adobe Standard) : idem ;
  mire          (d) matrice 3 × 3 ajustée sur les mires VFA d'Imaging Resource (ColorChecker 24 + SG 140) du X-T3 et du
                    X-T30, même capteur X-Trans IV : Adobe donne aux trois boîtiers un profil identique au bit près.
Méthode retenue : 'mire' (METHODE). Contre la mire de l'autre boîtier, ΔE2000 médian 1,4 à 1,5 et p90 3,7 à 3,8 au lieu
de 2,5 et 6,6 à 6,8 pour cm-d65 (plages L* ≥ 20) ; détail et limites (LED, lumière chaude) : voir docs/methode.md.
lineaire(raf) a la même interface et les mêmes sorties que xt4_mesure.lineaire : un `from xt4_scene import lineaire`
suffit (ou `xt4_mesure.lineaire = xt4_scene.lineaire`). L'échelle d'exposition (etalonnage.json) reste valable (+0,001 IL).
Les blocs déjà préparés (CHANTIER/blocs/*.npz) se convertissent sans relire les RAF : convertir_blocs(d).

  xt4_scene.py mesurer <RAF> <sortie.json> <cc> <sg>   plages d'une mire VFA (cc, sg : x0,y0,x1,y1 des centres des
                                                       plages extrêmes, pixels de la demi-résolution) ; lancer un fichier
                                                       téléchargé avec python3 -I
  xt4_scene.py valider                                 ΔE2000 de chaque méthode contre les deux mires
  xt4_scene.py effet                                   écart entre l'ancienne et la nouvelle scène sur les 16 RAF
  xt4_scene.py --self-test

Données : recherche/donnees/xt4-mire-ir-xtrans4.json (plages mesurées). Profils Adobe lus en place (lecture seule).
"""
import json
import os
import pathlib
import site
import sys
import tempfile

if site.getusersitepackages() not in sys.path:      # python3 -I écarte le site utilisateur, où numpy est souvent installé
    sys.path.append(site.getusersitepackages())
import numpy as np

ICI = pathlib.Path(__file__).resolve().parent
# modules du D750 (d750_modele, d750_cibles, films_nb, dcp…) : dépôt https://github.com/ThomasHMD/retro-ingenierie-boitiers ;
# XT4_RIB = le dossier de son clone (par défaut, deux dossiers au-dessus de ce fichier)
RACINE = pathlib.Path(os.environ.get('XT4_RIB') or ICI.parent.parent)
sys.path.insert(0, str(RACINE / 'commun' / 'outils'))
sys.path.insert(0, str(RACINE / 'd750' / 'outils'))
if not (RACINE / 'd750' / 'outils' / 'd750_modele.py').is_file() and not os.environ.get('XT4_RIB_AVERTI'):
    os.environ['XT4_RIB_AVERTI'] = '1'
    print(f"xt4 : modules du D750 introuvables dans {RACINE / 'd750' / 'outils'} ; XT4_RIB doit pointer vers un clone de "
          'https://github.com/ThomasHMD/retro-ingenierie-boitiers (voir docs/methode.md).', file=sys.stderr)
CHANTIER = pathlib.Path(os.environ.get('XT4_CHANTIER') or pathlib.Path(tempfile.gettempdir()) / 'xt4-mesure')
DONNEES = ICI.parent / 'recherche' / 'donnees'
MIRES = DONNEES / 'xt4-mire-ir-xtrans4.json'
DCP_STANDARD = pathlib.Path('/Library/Application Support/Adobe/CameraRaw/CameraProfiles/Adobe Standard/Fujifilm X-T4 Adobe Standard.dcp')
DCP_LINEAR = pathlib.Path.home() / 'Library/Application Support/Adobe/CameraRaw/CameraProfiles/Linear-Fujifilm X-T4.dcp'

M709 = np.array([[0.4124564, 0.3575761, 0.1804375], [0.2126729, 0.7151522, 0.0721750], [0.0193339, 0.1191920, 0.9503041]])
D65 = M709.sum(1)                                     # blanc de d750_modele (xyz_lab), Y = 1
D50 = np.array([0.3457 / 0.3585, 1.0, (1 - 0.3457 - 0.3585) / 0.3585])   # blanc PCS de la norme DNG
BRADFORD = np.array([[0.8951, 0.2664, -0.1614], [-0.7502, 1.7135, 0.0367], [0.0389, -0.0685, 1.0296]])
PROPHOTO = np.array([[0.7977, 0.1352, 0.0313], [0.2880, 0.7119, 0.0001], [0.0, 0.0, 0.8249]])   # ProPhoto linéaire → XYZ D50
# ColorMatrix D65 du X-T4 dans adobe_coeff de LibRaw (= ColorMatrix2 d'Adobe Standard), XYZ → caméra
CM_LIBRAW = np.array([[13426, -6334, -1177], [-4244, 12136, 2371], [-580, 1303, 5980]]) / 10000

# (d) caméra équilibrée → XYZ D65, ajustée par ajuster_mire() sur les 2 × 164 plages (lignes de somme D65 : neutre gardé)
M_MIRE = np.array([[0.605492, 0.302941, 0.042037],
                   [0.190848, 1.038771, -0.229618],
                   [0.038968, -0.26423, 1.314092]])
METHODE = 'mire'


# ---------------------------------------------------------------------------------------------------------------
# 1. Norme DNG : température de la balance, interpolation des matrices, HueSatMap
# ---------------------------------------------------------------------------------------------------------------
# En-tête de dng_temperature.cpp (SDK DNG d'Adobe), d'où vient la table ci-dessous :
# Copyright 2006-2019 Adobe Systems Incorporated
# All Rights Reserved.
#
# NOTICE:  Adobe permits you to use, modify, and distribute this file in
# accordance with the terms of the Adobe license agreement accompanying it.
#
# Table de Robertson reprise de ce fichier ; voir LICENCES-TIERS.md.
_ROBERTSON = np.array([  # mired, u, v, pente (table du SDK DNG, dng_temperature.cpp)
    [0, 0.18006, 0.26352, -0.24341], [10, 0.18066, 0.26589, -0.25479], [20, 0.18133, 0.26846, -0.26876],
    [30, 0.18208, 0.27119, -0.28539], [40, 0.18293, 0.27407, -0.30470], [50, 0.18388, 0.27709, -0.32675],
    [60, 0.18494, 0.28021, -0.35156], [70, 0.18611, 0.28342, -0.37915], [80, 0.18740, 0.28668, -0.40955],
    [90, 0.18880, 0.28997, -0.44278], [100, 0.19032, 0.29326, -0.47888], [125, 0.19462, 0.30141, -0.58204],
    [150, 0.19962, 0.30921, -0.70471], [175, 0.20525, 0.31647, -0.84901], [200, 0.21142, 0.32312, -1.0182],
    [225, 0.21807, 0.32909, -1.2168], [250, 0.22511, 0.33439, -1.4512], [275, 0.23247, 0.33904, -1.7298],
    [300, 0.24010, 0.34308, -2.0637], [325, 0.24702, 0.34655, -2.4681], [350, 0.25591, 0.34951, -2.9641],
    [375, 0.26400, 0.35200, -3.5814], [400, 0.27218, 0.35407, -4.3633], [425, 0.28039, 0.35577, -5.3762],
    [450, 0.28863, 0.35714, -6.7262], [475, 0.29685, 0.35823, -8.5955], [500, 0.30505, 0.35907, -11.324],
    [525, 0.31320, 0.35968, -15.628], [550, 0.32129, 0.36011, -23.325], [575, 0.32931, 0.36038, -40.770],
    [600, 0.33724, 0.36051, -116.45]])
T_ILLUM = {17: 2850.0, 21: 6500.0, 23: 5000.0, 20: 5500.0}   # valeurs du SDK DNG (lumière A, D65, D50, D55)


def xy_cct(xy):
    """Température proximale (K) d'une chromaticité, méthode de Robertson comme dng_temperature::Set_xy_coord."""
    x, y = xy
    u, v = 2 * x / (1.5 - x + 6 * y), 3 * y / (1.5 - x + 6 * y)
    last_dt = 0.0
    for i in range(1, 31):
        r, uu0, vv0, t = _ROBERTSON[i]
        du, dv = 1 / np.hypot(1, t), t / np.hypot(1, t)
        dt = -(u - uu0) * dv + (v - vv0) * du
        if dt <= 0 or i == 30:
            dt = -min(dt, 0.0)
            f = 0.0 if i == 1 else dt / (last_dt + dt)       # poids de la ligne i − 1
            return 1e6 / (_ROBERTSON[i - 1, 0] * f + r * (1 - f))
        last_dt = dt


def bradford(src, dst):
    """Adaptation chromatique de Bradford (matrice XYZ → XYZ) du blanc src au blanc dst."""
    return np.linalg.inv(BRADFORD) @ np.diag((BRADFORD @ dst) / (BRADFORD @ src)) @ BRADFORD


def lire_profil(chemin):
    """Matrices et HueSatMap d'un profil DCP (lecture seule, dcp.py de d750/outils/)."""
    import dcp
    p = dcp.lire(str(chemin))
    out = {k: np.array(p[k], float).reshape(3, 3) for k in ('ColorMatrix1', 'ColorMatrix2', 'ForwardMatrix1', 'ForwardMatrix2')}
    out['T1'], out['T2'] = T_ILLUM[p['CalibrationIlluminant1'][0]], T_ILLUM[p['CalibrationIlluminant2'][0]]
    if 'ProfileHueSatMapDims' in p:
        nh, ns, nv = p['ProfileHueSatMapDims']
        out['hsm_dims'] = (nh, ns, nv)
        for k in (1, 2):
            out[f'hsm{k}'] = np.array(p[f'ProfileHueSatMapData{k}'], float).reshape(nv, nh, ns, 3)
    out['nom'] = p.get('ProfileName', pathlib.Path(chemin).stem)
    return out


def _normaliser_cm(m):
    """dng_color_spec : une ColorMatrix est ramenée à « blanc D50 → canal max = 1 »."""
    c = m @ D50
    return m / c.max() if c.max() > 0 and not 0.99 < c.max() < 1.01 else m


def poids_illuminant1(T, prof):
    """Poids de l'illuminant 1 (lumière A) à la température T, linéaire en 1/T, borné (norme DNG)."""
    t1, t2 = prof['T1'], prof['T2']
    if T <= t1:
        return 1.0
    if T >= t2:
        return 0.0
    return (1 / T - 1 / t2) / (1 / t1 - 1 / t2)


def blanc_dng(wb, prof):
    """Chromaticité et température du neutre de la vue (dng_color_spec::NeutralToXY), et poids de l'illuminant 1.
    wb : balance (multiplicateurs, vert = 1) ; le neutre caméra vaut 1 / wb."""
    neutre = 1 / np.asarray(wb, float)
    cm1, cm2 = _normaliser_cm(prof['ColorMatrix1']), _normaliser_cm(prof['ColorMatrix2'])
    xy = D50[:2] / D50.sum()
    for passe in range(30):
        g = poids_illuminant1(xy_cct(xy), prof)
        X = np.linalg.solve(g * cm1 + (1 - g) * cm2, neutre)
        nxy = X[:2] / X.sum()
        if abs(nxy - xy).sum() < 1e-7:
            xy = nxy
            break
        xy = nxy if passe < 29 else (xy + nxy) / 2
    T = xy_cct(xy)
    return xy, T, poids_illuminant1(T, prof)


def cam_xyz_fm(wb, prof):
    """(b) caméra équilibrée → XYZ D65 : ForwardMatrix interpolée (poids de blanc_dng), puis Bradford D50 → D65.
    Le neutre caméra est normalisé au vert comme l'équilibrage des blocs (vert = 1)."""
    _, _, g = blanc_dng(wb, prof)
    fm = g * prof['ForwardMatrix1'] + (1 - g) * prof['ForwardMatrix2']
    return bradford(D50, D65) @ fm


def cam_xyz_cm(cm=CM_LIBRAW):
    """(a) l'ancienne : XYZ → caméra (D65) composée avec sRGB, lignes ramenées à 1 (blanc sRGB → caméra (1, 1, 1))."""
    cam_rgb = cm @ M709
    cam_rgb = cam_rgb / cam_rgb.sum(1, keepdims=True)
    return M709 @ np.linalg.inv(cam_rgb)


def _hsv(rgb):
    v = rgb.max(1)
    gap = v - rgb.min(1)
    h = np.zeros(len(rgb))
    s = np.where(v > 0, gap / np.maximum(v, 1e-12), 0)
    r, g, b = rgb.T
    ok = gap > 0
    gg = np.maximum(gap, 1e-12)
    hr = (g - b) / gg
    hr = np.where(hr < 0, hr + 6, hr)
    h = np.where(ok & (r == v), hr, np.where(ok & (g == v), 2 + (b - r) / gg, np.where(ok, 4 + (r - g) / gg, 0)))
    return h, s, v


def _rgb(h, s, v):
    h = np.mod(h, 6)
    i = np.floor(h).astype(int) % 6
    f = h - np.floor(h)
    p, q, t = v * (1 - s), v * (1 - s * f), v * (1 - s * (1 - f))
    tab = [(v, t, p), (q, v, p), (p, v, t), (p, q, v), (t, p, v), (v, p, q)]
    out = np.zeros((len(h), 3))
    for k, (a, b, c) in enumerate(tab):
        m = i == k
        out[m] = np.c_[a, b, c][m]
    return np.where(s[:, None] > 0, out, v[:, None])


def appliquer_hsm(xyz50, table, dims):
    """HueSatMap 2,5D (sans dimension de valeur) en ProPhoto linéaire, comme RefBaselineHueSatMap du SDK DNG."""
    nh, ns, nv = dims
    assert nv == 1, 'table 3D non prise en charge'
    rgb = np.clip(xyz50 @ np.linalg.inv(PROPHOTO).T, 0, None)
    h, s, v = _hsv(rgb)
    hs, ss = h * nh / 6, s * (ns - 1)
    h0 = np.minimum(hs.astype(int), nh - 1)
    s0 = np.minimum(ss.astype(int), ns - 2)
    h1 = np.where(h0 >= nh - 1, 0, h0 + 1)
    fh, fs = hs - h0, ss - s0
    t = table[0]
    e = ((1 - fh)[:, None] * ((1 - fs)[:, None] * t[h0, s0] + fs[:, None] * t[h0, s0 + 1])
         + fh[:, None] * ((1 - fs)[:, None] * t[h1, s0] + fs[:, None] * t[h1, s0 + 1]))
    h = h + e[:, 0] * 6 / 360
    s = np.minimum(s * e[:, 1], 1)
    v = v * e[:, 2]                       # le SDK borne v à 1 ; ici la scène n'est pas bornée (table sans valeur)
    return _rgb(h, s, v) @ PROPHOTO.T


_PROFILS = {}


def profil(nom='standard'):
    if nom not in _PROFILS:
        _PROFILS[nom] = lire_profil(DCP_STANDARD if nom == 'standard' else DCP_LINEAR)
    return _PROFILS[nom]


def scene_xyz(x, wb, methode=METHODE):
    """x : RVB caméra équilibré (N × 3) ; wb : balance de la vue (vert = 1) → XYZ D65 adapté (N × 3)."""
    x = np.asarray(x, float)
    if methode in ('fm-dng-hsm', 'fm-dng-hsm-lin'):
        prof = profil('standard' if methode == 'fm-dng-hsm' else 'linear')
        _, _, g = blanc_dng(wb, profil('standard'))      # le profil Linear porte les mêmes matrices
        fm = g * prof['ForwardMatrix1'] + (1 - g) * prof['ForwardMatrix2']
        tab = g * prof['hsm1'] + (1 - g) * prof['hsm2']
        return appliquer_hsm(x @ fm.T, tab, prof['hsm_dims']) @ bradford(D50, D65).T
    return x @ cam_xyz(wb, methode).T


def cam_xyz(wb, methode=METHODE):
    """Matrice caméra équilibrée → XYZ D65 d'une méthode linéaire."""
    if methode == 'cm-d65':
        return cam_xyz_cm()
    if methode == 'fm-dng':
        return cam_xyz_fm(wb, profil('standard'))
    if methode == 'mire':
        return M_MIRE.copy()
    raise ValueError(f'{methode} : pas une matrice (méthode non linéaire ou inconnue)')


def rgb_cam(wb, methode=METHODE):
    """Matrice caméra équilibrée → sRGB linéaire, la sortie de xt4_mesure.lineaire."""
    return np.linalg.inv(M709) @ cam_xyz(wb, methode)


# ---------------------------------------------------------------------------------------------------------------
# 2. Remplaçant de xt4_mesure.lineaire, conversion des blocs déjà préparés
# ---------------------------------------------------------------------------------------------------------------
def lineaire(raf, methode=METHODE):
    """RAW en demi-résolution : RVB caméra, noir soustrait, fraction de la pleine échelle, SANS balance (pour repérer
    l'écrêtage) ; renvoie (image, balance de la prise de vue normalisée au vert, matrice caméra équilibrée → sRGB linéaire).
    Même interface que xt4_mesure.lineaire ; seule la matrice change (méthode METHODE, voir l'en-tête)."""
    import rawpy
    with rawpy.imread(raf) as r:
        a = r.postprocess(half_size=True, output_color=rawpy.ColorSpace.raw, gamma=(1, 1), no_auto_bright=True,
                          use_camera_wb=False, user_wb=[1, 1, 1, 1], output_bps=16, user_flip=0).astype(np.float32) / 65535
        wb = np.array(r.camera_whitebalance[:3], float)
    wb = wb / wb[1]
    return a, wb, rgb_cam(wb, methode)


def convertir_blocs(d, methode=METHODE):
    """Bloc préparé par xt4_mesure (dict d'un .npz : srgb, rgb_cam, wb) → copie dont srgb (et rgb_cam) suivent la méthode.
    Le RVB caméra équilibré est retrouvé exactement par l'inverse de l'ancienne matrice."""
    x = d['srgb'] @ np.linalg.inv(d['rgb_cam']).T
    out = dict(d)
    if methode in ('fm-dng-hsm', 'fm-dng-hsm-lin'):
        out['srgb'] = (scene_xyz(x, d['wb'], methode) @ np.linalg.inv(M709).T).astype(np.float32)
        out['rgb_cam'] = None
    else:
        out['rgb_cam'] = rgb_cam(d['wb'], methode)
        out['srgb'] = (x @ out['rgb_cam'].T).astype(np.float32)
    return out


# ---------------------------------------------------------------------------------------------------------------
# 3. Mires VFA d'Imaging Resource : mesure, correction de l'éclairage et du voile, références
# ---------------------------------------------------------------------------------------------------------------
def mesurer(raf, coins_cc, coins_sg):
    """Moyenne de chaque plage (CC 6 × 4 puis SG 14 × 10, ligne par ligne) dans le RAW demi-résolution de lineaire,
    sans balance. Grille affine recalée en minimisant l'écart-type relatif dans les fenêtres (30 % du pas)."""
    from scipy.optimize import minimize
    a, wb, _ = lineaire(raf, 'cm-d65')
    lum = a.mean(2)

    def centres(p, nx, ny):
        i, j = np.meshgrid(np.arange(nx), np.arange(ny))
        return np.c_[(p[0] + i * p[2] + j * p[4]).ravel(), (p[1] + i * p[3] + j * p[5]).ravel()]

    def cout(p, nx, ny, w):
        s = 0.0
        for x, y in np.round(centres(p, nx, ny)).astype(int):
            f = lum[y - w:y + w + 1, x - w:x + w + 1]
            s += f.std() / max(f.mean(), 1e-4)
        return s
    out = {'raf': pathlib.Path(raf).name, 'wb_prise_de_vue': np.round(wb, 5).tolist(), 'plages': []}
    for nom, (x0, y0, x1, y1), nx, ny in (('cc', coins_cc, 6, 4), ('sg', coins_sg, 14, 10)):
        p0 = np.array([x0, y0, (x1 - x0) / (nx - 1), 0, 0, (y1 - y0) / (ny - 1)])
        w = int(0.3 * min(p0[2], p0[5]))
        simplexe = np.r_[[p0], [p0 + np.eye(6)[k] * (2 if k < 2 else 0.05) for k in range(6)]]
        p = minimize(cout, p0, args=(nx, ny, w), method='Nelder-Mead',
                     options={'initial_simplex': simplexe, 'maxiter': 4000, 'xatol': 0.01, 'fatol': 1e-4}).x
        out[f'grille_{nom}'] = np.round(p, 3).tolist()
        for x, y in centres(p, nx, ny):
            f = a[int(round(y)) - w:int(round(y)) + w + 1, int(round(x)) - w:int(round(x)) + w + 1].reshape(-1, 3)
            out['plages'].append([round(float(x), 1), round(float(y), 1)] + f.mean(0).round(7).tolist())
    return out


def references(edition='Before'):
    """XYZ D65 (Bradford depuis D50) des 24 + 140 plages, valeurs X-Rite de colour-science (édition d'avant ou d'après
    novembre 2014), dans l'ordre de mesurer()."""
    import colour
    ref = []
    for c in ('ColorChecker24', 'ColorCheckerSG'):
        ref += list(colour.CCS_COLOURCHECKERS[f'{c} - {edition} November 2014'].data.values())
    X50 = np.array([[x / y * Y, Y, (1 - x - y) / y * Y] for x, y, Y in ref])
    w50 = colour.CCS_COLOURCHECKERS['ColorChecker24 - Before November 2014'].illuminant
    return X50 @ bradford(np.array([w50[0] / w50[1], 1, (1 - w50.sum()) / w50[1]]), D65).T


def _lab(X):
    import d750_modele as dm
    return dm.xyz_lab(X)


def _de(a, b):
    import d750_modele as dm
    return dm.de2000(a, b)


def mires(edition='Before'):
    """{mire: dict(x = RVB équilibré corrigé (164 × 3), wb = balance tirée des neutres, wb_vue, X = référence, lab, pos)}.
    Corrections (identiques pour toutes les méthodes) : sur la SG, gain et voile en plans (x, y) ajustés sur ses
    ~60 plages neutres (blancs, gris et noirs du pourtour, brillant) ; sur la CC (mate), gain et voile constants sur
    ses 6 neutres. La balance est celle des neutres corrigés (vert = 1)."""
    d = json.loads(MIRES.read_text(encoding='utf-8'))
    X = references(edition)
    lab = _lab(X)
    neutre = np.hypot(lab[:, 1], lab[:, 2]) < 3
    out = {}
    for nom, m in d['mires'].items():
        p = np.array(m['plages'])
        pos, raw = p[:, :2], p[:, 2:]
        cc = np.arange(len(raw)) < 24
        wb0 = raw[19:23].mean(0)
        wb0 = wb0[1] / wb0
        xb = raw * wb0
        g = xb.mean(1)
        x = np.empty_like(xb)
        for sel, plan in ((cc, False), (~cc, True)):
            k = sel & neutre
            u = (pos[:, 0] - pos[k, 0].mean()) / 1000
            v = (pos[:, 1] - pos[k, 1].mean()) / 1000
            A = np.c_[X[:, 1], X[:, 1] * u, X[:, 1] * v, np.ones(len(u)), u, v] if plan else np.c_[X[:, 1], np.ones(len(u))]
            c = np.linalg.lstsq(A[k], g[k], rcond=None)[0]
            gain = A[:, :len(c) // 2] @ c[:len(c) // 2] / X[:, 1]
            voile = A[:, len(c) // 2:] @ c[len(c) // 2:]
            x[sel] = ((xb - voile[:, None]) / gain[:, None])[sel]
        n = x[neutre].mean(0)                       # balance finale sur tous les neutres corrigés
        wb = wb0 * n[1] / n
        x = x * (n[1] / n)
        out[nom] = {'x': x, 'wb': wb, 'wb_vue': np.array(m['wb_prise_de_vue']), 'X': X, 'lab': lab, 'pos': pos,
                    'neutre': neutre}
    return out


def ajuster_mire(x, X, forme='3x3'):
    """Matrice x → XYZ D65 à lignes de somme D65 (un neutre reste neutre), moindres carrés robustes en CIELAB
    (soft_l1, comme d750_analyse.matrice_camera) ; forme 'poly' : racine-polynôme d'ordre 2 (3 × 6), pour comparaison."""
    from scipy.optimize import least_squares
    n = 3 if forme == '3x3' else 6
    T = _traits(x, n)
    lab = _lab(X)

    def M(q):
        A = q.reshape(3, n - 1)
        return np.c_[A, D65 - A.sum(1)]
    q0 = np.c_[M_MIRE[:, :2], np.zeros((3, n - 3))].ravel()
    r = least_squares(lambda q: (_lab(T @ M(q).T) - lab).ravel(), q0, loss='soft_l1', f_scale=2)
    return M(r.x)


def _traits(x, n):
    x = np.clip(np.asarray(x, float), 0, None)
    if n == 3:
        return x
    return np.c_[x[:, 0], x[:, 1], np.sqrt(x[:, 0] * x[:, 1]), np.sqrt(x[:, 1] * x[:, 2]), np.sqrt(x[:, 0] * x[:, 2]), x[:, 2]]


def appliquer_matrice(x, M):
    return _traits(x, M.shape[1]) @ M.T


# ---------------------------------------------------------------------------------------------------------------
# 4. Validation et effet sur les 16 RAF
# ---------------------------------------------------------------------------------------------------------------
METHODES = ('cm-d65', 'fm-dng', 'fm-dng-hsm', 'fm-dng-hsm-lin', 'mire')
FAMILLES = {  # sur le Lab de la scène (référence pour la mire, scène retenue pour les RAF)
    'saturées (C* > 40)': lambda L, C, h: C > 40,
    'magenta, pourpre': lambda L, C, h: (h > 300) & (h < 350) & (C > 25),
    'bleu, violet': lambda L, C, h: (h > 240) & (h <= 300) & (C > 25),
    'jaune, orangé': lambda L, C, h: (h > 55) & (h < 100) & (C > 40),
    'rouge': lambda L, C, h: ((h >= 350) | (h < 40)) & (C > 30),
    'vert': lambda L, C, h: (h > 100) & (h < 180) & (C > 12),
    'cyan, ciel': lambda L, C, h: (h >= 180) & (h <= 240) & (C > 8),
    'peau': lambda L, C, h: (h > 25) & (h < 70) & (C > 10) & (C < 40) & (L > 35) & (L < 85),
    'neutres (C* < 8)': lambda L, C, h: C < 8,
}


def stats(e, w=None):
    e = np.asarray(e, float)
    if not len(e):
        return {'n': 0}
    if w is None:
        return {'n': int(len(e)), 'mediane': round(float(np.median(e)), 2), 'p90': round(float(np.percentile(e, 90)), 2),
                'max': round(float(e.max()), 2)}
    o = np.argsort(e)
    c = np.cumsum(w[o])
    q = lambda p: float(np.interp(p * c[-1], c, e[o]))
    return {'n': int(len(e)), 'mediane': round(q(0.5), 2), 'p90': round(q(0.9), 2), 'max': round(float(e.max()), 2)}


def familles(lab, e, w=None):
    C = np.hypot(lab[:, 1], lab[:, 2])
    h = np.degrees(np.arctan2(lab[:, 2], lab[:, 1])) % 360
    return {k: stats(e[f(lab[:, 0], C, h)], None if w is None else w[f(lab[:, 0], C, h)]) for k, f in FAMILLES.items()}


def valider(edition='Before', verbeux=True):
    """ΔE2000 de chaque méthode contre les références, mire par mire ; validation croisée de la matrice ajustée (ajustée
    sur une mire, notée sur l'autre boîtier) ; plages L* ≥ 20 seulement dans les chiffres principaux (les noirs brillants
    de la SG gardent un reflet que la correction de voile n'efface pas tout à fait)."""
    ms = mires(edition)
    noms = list(ms)
    res = {'edition_references': edition, 'mires': {}}
    for nom, m in ms.items():
        r = {'wb_mire': np.round(m['wb'], 4).tolist(), 'wb_vue': np.round(m['wb_vue'], 4).tolist()}
        xy, T, g = blanc_dng(m['wb'], profil('standard'))
        r['blanc_dng'] = {'xy': np.round(xy, 4).tolist(), 'T': round(T), 'poids_lumiere_A': round(g, 3)}
        autre = [n for n in noms if n != nom][0]
        cands = {k: scene_xyz(m['x'], m['wb'], k) for k in METHODES if k != 'mire'}
        cands['mire (ajustée sur les deux)'] = appliquer_matrice(m['x'], ajuster_mire(np.r_[ms[noms[0]]['x'], ms[noms[1]]['x']], np.r_[m['X'], m['X']]))
        cands[f'mire (ajustée sur {autre})'] = appliquer_matrice(m['x'], ajuster_mire(ms[autre]['x'], m['X']))
        cands[f'racine-polynôme (ajustée sur {autre})'] = appliquer_matrice(m['x'], ajuster_mire(ms[autre]['x'], m['X'], 'poly'))
        cands['fm-dng, balance de la vue'] = scene_xyz(m['x'] * m['wb_vue'] / m['wb'], m['wb_vue'], 'fm-dng')
        cands['cm-d65, balance de la vue'] = scene_xyz(m['x'] * m['wb_vue'] / m['wb'], m['wb_vue'], 'cm-d65')
        clair = m['lab'][:, 0] >= 20
        r['methodes'] = {}
        for k, Xe in cands.items():
            Le = _lab(Xe)
            e = _de(Le, m['lab'])
            Ce, Cr = np.hypot(*Le[:, 1:].T), np.hypot(*m['lab'][:, 1:].T)
            dh = (np.degrees(np.arctan2(Le[:, 2], Le[:, 1]) - np.arctan2(m['lab'][:, 2], m['lab'][:, 1])) + 180) % 360 - 180
            sat = clair & (Cr > 40)
            r['methodes'][k] = {'L>=20': stats(e[clair]), 'toutes': stats(e), 'cc24': stats(e[:24]),
                                'familles': familles(m['lab'][clair], e[clair]),
                                'saturees_signe': {'dL': round(float(np.median((Le[:, 0] - m['lab'][:, 0])[sat])), 2),
                                                   'C_rapport': round(float(np.median(Ce[sat] / Cr[sat])), 3),
                                                   'dh_abs_deg': round(float(np.median(np.abs(dh[sat]))), 2)}}
        res['mires'][nom] = r
    # généralisation à d'autres pigments : ajustée sur les 24 plages de la CC (deux mires), notée sur les 140 de la SG
    x = np.r_[ms[noms[0]]['x'], ms[noms[1]]['x']]
    X = np.r_[ms[noms[0]]['X'], ms[noms[1]]['X']]
    lab, cc = _lab(X), np.tile(np.arange(164) < 24, 2)
    sg = ~cc & (lab[:, 0] >= 20)
    res['cc_vers_sg'] = {f: stats(_de(_lab(appliquer_matrice(x[sg], ajuster_mire(x[cc], X[cc], f))), lab[sg])) for f in ('3x3', 'poly')}
    for k in ('cm-d65', 'fm-dng-hsm'):
        res['cc_vers_sg'][k] = stats(np.concatenate([_de(_lab(scene_xyz(ms[n]['x'][24:], ms[n]['wb'], k)), ms[n]['lab'][24:])[ms[n]['lab'][24:, 0] >= 20] for n in noms]))
    if verbeux:
        for nom, r in res['mires'].items():
            print(f"\n== {nom} : balance mire {r['wb_mire']} (vue {r['wb_vue']}), blanc DNG {r['blanc_dng']}")
            fam = list(FAMILLES)[:-1]
            print(f"{'méthode':42s} {'L*≥20 méd/p90/max':>20s}  {'toutes':>11s} " + ' '.join(f'{f[:9]:>9s}' for f in fam) + '   sat: dL C× |dh|')
            for k, v in r['methodes'].items():
                s, t, z = v['L>=20'], v['toutes'], v['saturees_signe']
                print(f"{k:42s} {s['mediane']:6.2f} {s['p90']:6.2f} {s['max']:6.2f}  {t['mediane']:5.2f} {t['p90']:5.2f} "
                      + ' '.join(f"{v['familles'][f].get('mediane', 0):9.2f}" for f in fam) + f"   {z['dL']:+.1f} {z['C_rapport']:.2f} {z['dh_abs_deg']:.1f}")
            print('effectifs (L*≥20) :', {f: r['methodes']['cm-d65']['familles'][f]['n'] for f in FAMILLES})
        print('\nCC → SG (ajustée sur la CC des deux mires, notée sur la SG, L* ≥ 20) :', res['cc_vers_sg'])
    return res


def blocs_16():
    """Blocs préparés par xt4_mesure (lecture seule) : {raf: dict du .npz}."""
    return {f.stem: dict(np.load(f)) for f in sorted((CHANTIER / 'blocs').glob('*.npz'))}


def y18(blocs, methode):
    """Échelle d'exposition refaite comme xt4_mesure.etalonner (même tri des blocs peu colorés, même droite L* = a + b log2 Y
    contre le Provia neutre du boîtier, médiane des RAF), sur la scène d'une méthode."""
    import d750_modele as dm
    L118 = float(dm.code_lab(np.array([118 / 255] * 3))[0])
    v = []
    for d in blocs.values():
        s = convertir_blocs(d, methode)['srgb']
        Y = s @ M709[1]
        L = dm.code_lab(d['jpg_ref'] / 255)[:, 0]
        m = (s.min(1) > 0) & (s.max(1) / np.maximum(s.min(1), 1e-9) < 1.5) & (L > 30) & (L < 70)
        if m.sum() >= 20:
            b, a = np.polyfit(np.log2(Y[m]), L[m], 1)
            v.append((L118 - a) / b)
    return float(2 ** np.median(v))


def effet(methode=METHODE, ancienne='cm-d65'):
    """Écart ΔE2000 bloc par bloc entre la scène de l'ancienne méthode et celle de la nouvelle, sur les blocs des 16 RAF
    (CHANTIER/blocs, lus sans être modifiés) ; même échelle d'exposition pour les deux (etalonnage.json, gris = 0,18),
    l'échelle refaite avec la nouvelle scène étant donnée à part ; familles de couleur prises sur la nouvelle scène ;
    chaque RAF pèse autant. N&B : décalage (IL) de l'entrée des cibles N&B, mélange de canaux de chaque film
    (films_nb.poids sur le sRGB linéaire de la scène, comme xt4_mesure.cibles)."""
    import films_nb as fn
    fn.fiches_exactes()
    w_nb = {f: fn.poids(n, fn.sens_srgb())[0] for f, n in (('trix', 'trix_fiche'), ('hp5', 'hp5_fiche'), ('fp4', 'fp4'))}
    y = json.loads((CHANTIER / 'etalonnage.json').read_text())['y18']
    blocs = blocs_16()
    tous, labs, ws, par_raf, T, nb = [], [], [], {}, {}, {f: [] for f in w_nb}
    for n, d in blocs.items():
        x = d['srgb'] @ np.linalg.inv(d['rgb_cam']).T * (0.18 / y)
        Xa, Xn = scene_xyz(x, d['wb'], ancienne), scene_xyz(x, d['wb'], methode)
        La, Ln = _lab(Xa), _lab(Xn)
        e = _de(La, Ln)
        tous.append(e)
        labs.append(Ln)
        ws.append(np.full(len(e), 1 / len(e)))
        par_raf[n] = round(float(np.median(e)), 2)
        T[n] = round(blanc_dng(d['wb'], profil('standard'))[1])
        sa, sn = Xa @ np.linalg.inv(M709).T, Xn @ np.linalg.inv(M709).T
        for f, w in w_nb.items():
            nb[f].append(np.abs(np.log2(np.clip(sn @ w, 1e-5, None) / np.clip(sa @ w, 1e-5, None))))
    e, lab, w = np.concatenate(tous), np.concatenate(labs), np.concatenate(ws)
    ya, yn = y18(blocs, ancienne), y18(blocs, methode)
    return {'methode': methode, 'ancienne': ancienne, 'blocs': int(len(e)), 'ensemble': stats(e, w),
            'familles': familles(lab, e, w),
            'nb_entree_IL_abs': {f: {'ensemble': stats(np.concatenate(v), w),
                                     'familles': {k: s.get('mediane') for k, s in familles(lab, np.concatenate(v), w).items()}}
                                 for f, v in nb.items()},
            'y18': {'ancienne': round(ya, 5), 'nouvelle': round(yn, 5), 'decalage_IL': round(float(np.log2(yn / ya)), 3)},
            'mediane_par_raf': par_raf, 'temperature_dng_par_raf': T}


# ---------------------------------------------------------------------------------------------------------------
# 5. Contrôles
# ---------------------------------------------------------------------------------------------------------------
def self_test():
    # Robertson : D65 et lumière A retrouvées
    assert abs(xy_cct((0.31271, 0.32902)) - 6504) < 15, xy_cct((0.31271, 0.32902))
    assert abs(xy_cct((0.44757, 0.40745)) - 2856) < 10, xy_cct((0.44757, 0.40745))
    # Bradford : le blanc source va sur le blanc cible
    assert np.allclose(bradford(D50, D65) @ D50, D65)
    # HSV du SDK : aller-retour
    rng = np.random.default_rng(1)
    c = rng.uniform(0, 1, (500, 3))
    assert np.allclose(_rgb(*_hsv(c)), c, atol=1e-9)
    # (a) identique à xt4_mesure.lineaire (même formule), un neutre équilibré → blanc D65
    for k in ('cm-d65', 'mire'):
        assert np.allclose(cam_xyz(np.ones(3), k) @ np.ones(3), D65, atol=1e-5), k
    # conversion de blocs : l'ancienne méthode se retrouve à l'identique
    d = {'srgb': rng.uniform(0, 0.5, (50, 3)), 'wb': np.array([1.8, 1, 1.6]), 'rgb_cam': rgb_cam(None, 'cm-d65')}
    assert np.allclose(convertir_blocs(d, 'cm-d65')['srgb'], d['srgb'], atol=1e-6)
    if DCP_STANDARD.exists():
        p = profil('standard')
        assert np.allclose(_normaliser_cm(p['ColorMatrix2']), _normaliser_cm(CM_LIBRAW), atol=1e-4), 'ColorMatrix2 ≠ LibRaw'
        for wb in ([1.8, 1, 1.6], [1.2, 1, 2.6], [2.6, 1, 1.2]):
            M = cam_xyz(np.array(wb), 'fm-dng')
            assert np.allclose(M @ np.ones(3), D65, atol=1e-3), (wb, M @ np.ones(3))
        # table HSM neutre sur les gris (saturation nulle) : un neutre reste neutre
        g = np.array([[0.2, 0.2, 0.2]]) @ p['ForwardMatrix2'].T
        assert np.allclose(appliquer_hsm(g, p['hsm2'], p['hsm_dims']), g, atol=1e-4)
        # balance d'une vue au soleil (X-T4, 5 300 K environ) : poids de la lumière A faible
        _, T, gA = blanc_dng(np.array([1.9, 1, 1.55]), p)
        assert 4000 < T < 6500 and 0 < gA < 0.5, (T, gA)
    if MIRES.exists():
        ms = mires()
        x = np.r_[ms['XT3hVFAI00160']['x'], ms['XT30hVFAI00160']['x']]
        X = np.r_[ms['XT3hVFAI00160']['X'], ms['XT30hVFAI00160']['X']]
        M = ajuster_mire(x, X)
        assert np.abs(M - M_MIRE).max() < 2e-4, ('M_MIRE à recopier', np.round(M, 6).tolist())
        e = _de(_lab(appliquer_matrice(x, M_MIRE)), _lab(X))
        assert np.median(e) < 2.0, np.median(e)
    # sur un vrai RAF : cm-d65 redonne exactement la matrice et la balance que xt4_mesure a rangées dans ses blocs
    npz = CHANTIER / 'blocs' / '176-DSCF0476.npz'
    if npz.exists() and (CHANTIER / 'raf' / '176-DSCF0476.RAF').exists():
        d = dict(np.load(npz))
        _, wb, M = lineaire(str(CHANTIER / 'raf' / '176-DSCF0476.RAF'), 'cm-d65')
        assert np.allclose(wb, d['wb']) and np.allclose(M, d['rgb_cam'], atol=1e-6), 'lineaire ≠ xt4_mesure.lineaire'
    print('self-test OK')


if __name__ == '__main__':
    a = sys.argv[1:]
    if not a or a[0] in ('-h', '--help'):
        print(__doc__)
        sys.exit(2)
    if a[0] == '--self-test':
        self_test()
    elif a[0] == 'mesurer':
        cc, sg = ([float(v) for v in s.split(',')] for s in a[3:5])
        r = mesurer(a[1], cc, sg)
        pathlib.Path(a[2]).write_text(json.dumps(r, ensure_ascii=False))
        print(r['raf'], 'grilles', r['grille_cc'], r['grille_sg'])
    elif a[0] == 'valider':
        valider(a[1] if len(a) > 1 else 'Before')
    elif a[0] == 'effet':
        print(json.dumps(effet(*a[1:]), indent=1, ensure_ascii=False))
    else:
        sys.exit(f'commande inconnue : {a[0]}')
