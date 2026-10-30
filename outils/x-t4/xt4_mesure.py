#!/usr/bin/env python3
# SPDX-License-Identifier: CC-BY-NC-4.0
# Copyright (c) 2026 Thomas Hammoudi
"""Recettes JPEG du X-T4 mesurées contre des cibles de film (Tri-X 400, HP5 Plus, FP4 Plus, Portra 400), le boîtier
développant lui-même les RAF par USB (xt4_banc.swift). Voir docs/methode.md.

Chaîne de mesure, pour chaque RAF :
1. RAW linéaire (rawpy / LibRaw, demi-résolution 3123 × 2085, noir soustrait, balance des blancs de la prise de vue) ;
   colorimétrie : matrice Adobe du X-T4 (ColorMatrix D65 de la table adobe_coeff de LibRaw : 13426 -6334 -1177 /
   -4244 12136 2371 / -580 1303 5980, × 1/10 000), comme un développement neutre ;
2. géométrie : le JPEG du boîtier (taille S, 3120 × 2080 : celle de la conversion par USB, distorsion de l'objectif corrigée) est recalé sur le RAW par
   points SIFT (OpenCV) + similitude + distorsion radiale (k1, k2, k3), modèle de d750_blocs.py ;
3. blocs de 16 × 16 px du JPEG, uniformes dans le RAW (écart-type relatif < 6 %), non écrêtés ; jusqu'à 1 000 par RAF ;
4. échelle d'exposition : le gris de 18 % est la valeur RAW que le boîtier rend à 118/255 en Provia neutre (convention
   SOS de l'ISO 12232, comme le calage des recettes V1 du D40) ; une seule valeur pour tous les RAF (tous en DR100) ;
5. cibles (fonctions de la scène XYZ D65, gris = 0,18) : N&B = mélange de canaux et courbe film + tirage grade 2 de
   films_nb.py (fiches Kodak et Ilford, d750/outils/ du dépôt retro-ingenierie-boitiers) ; Portra = le profil Portra du preset
   acheté tel que l'auteur le règle, mesuré au D750
   (d750/recherche/donnees-films/d750-seances/portra-preset-regle.json, via d750_cibles.paires) ;
6. écart : ΔE2000 (couleur) ou |ΔL*| (N&B) bloc par bloc entre le JPEG du boîtier et la cible ; médiane et p90,
   chaque RAF pesant autant.

  xt4_mesure.py preparer                 RAW linéaires, géométrie, blocs (un rendu de référence par RAF sur le boîtier)
  xt4_mesure.py etalonner                échelle d'exposition (gris de 18 %) d'après le Provia neutre
  xt4_mesure.py existantes               mesure des .FP1 de 2022 (presets/recettes-2022)
  xt4_mesure.py chercher <film> [...]    recherche grossière puis fine (le boîtier rend chaque candidat)
  xt4_mesure.py grain                    bruit ajouté par chaque réglage de grain (choix du grain, à part)
  xt4_mesure.py --self-test              contrôles sans boîtier

Variables : XT4_BANC (binaire compilé de xt4_banc.swift, hors du dépôt), XT4_CHANTIER (dossier lourd, hors du dépôt ; par défaut
<dossier temporaire>/xt4-mesure), XT4_RIB (clone du dépôt retro-ingenierie-boitiers : modules du D750, dans d750/outils/).
Les appels au boîtier se font un à la fois (un seul xt4_banc ouvert).
"""
import hashlib
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import time

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
BANC = os.environ.get('XT4_BANC', '')
PRESETS = ICI.parent.parent / 'presets' / 'recettes-2022'          # racine du dépôt fuji-xrfc-preset-generator
RECETTES = ICI.parent.parent / 'presets' / 'recettes-2026'
FIGURES = ICI.parent / 'recherche' / 'figures'
DONNEES = ICI.parent / 'recherche' / 'donnees'

# ---------------------------------------------------------------------------------------------------------------
# 1. Profil de conversion 0xD185 : 28 entiers 32 bits signés à la fin (index FilmKit src/profile/d185.ts)
# ---------------------------------------------------------------------------------------------------------------
IDX = {'expo': 4, 'dr': 6, 'drp': 7, 'sim': 8, 'grain': 9, 'cc': 10, 'wb_cond': 11, 'wb': 12, 'wb_r': 13, 'wb_b': 14,
       'kelvin': 15, 'h': 16, 's': 17, 'couleur': 18, 'nettete': 19, 'bruit': 20, 'ccb': 25, 'clarte': 27}
# toning monochrome : index trouvés par essai sur le boîtier le 29/10/2026 (23 = chaud/froid, +30 rougit et l'EXIF lit
# « BW Adjustment +3 » ; 26 = magenta/vert, +30 verdit, EXIF « BW Magenta Green +3 »), × 10 comme les tons
IDX_MONO = {'mono_wc': 23, 'mono_mg': 26}
BRUIT = {-4: 0x8000, -3: 0x7000, -2: 0x4000, -1: 0x3000, 0: 0x2000, 1: 0x1000, 2: 0x0000, 3: 0x6000, 4: 0x5000}
SIMS = {1: 'Provia', 2: 'Velvia', 3: 'Astia', 4: 'Pro Neg. Hi', 5: 'Pro Neg. Std', 6: 'Monochrome', 7: 'Monochrome + Ye',
        8: 'Monochrome + R', 9: 'Monochrome + G', 10: 'Sepia', 11: 'Classic Chrome', 12: 'Acros', 13: 'Acros + Ye',
        14: 'Acros + R', 15: 'Acros + G', 16: 'Eterna', 17: 'Classic Neg.', 18: 'Eterna Bleach Bypass'}
SIMS_MONO = {6, 7, 8, 9, 12, 13, 14, 15}
FP1_SIM = {1: 'Provia', 2: 'Velvia', 3: 'Astia', 4: 'NEGAhi', 5: 'NEGAStd', 6: 'BW', 7: 'BYe', 8: 'BR', 9: 'BG', 10: 'Sepia',
           11: 'Classic', 12: 'Acros', 13: 'AcrosYe', 14: 'AcrosR', 15: 'AcrosG', 16: 'Eterna', 17: 'ClassicNEGA', 18: 'BleachBypass'}
SIM_FP1 = {v: k for k, v in FP1_SIM.items()} | {'NEGA': 5, 'AcrosY': 13}
WB = {'Auto': 0x0002, 'Auto_White': 0x8020, 'Auto_Ambience': 0x8021, 'Daylight': 0x0004, 'Incand': 0x0006, 'Shade': 0x8006, 'UWater': 0x0008,
      'FLight1': 0x8001, 'FLight2': 0x8002, 'FLight3': 0x8003, 'Temperature': 0x8007}
WB_NOM = {v: k for k, v in WB.items()}
GRAIN = {1: ('OFF', 'SMALL'), 2: ('WEAK', 'SMALL'), 3: ('STRONG', 'SMALL'), 4: ('WEAK', 'LARGE'), 5: ('STRONG', 'LARGE')}
NIVEAU = {1: 'OFF', 2: 'WEAK', 3: 'STRONG'}

# recette « neutre » de référence : Provia, tout à 0, DR100, balance de la prise de vue (0 = celle de l'EXIF)
NEUTRE = {'sim': 1, 'dr': 100, 'drp': 0, 'grain': 1, 'cc': 1, 'ccb': 1, 'wb': 0, 'wb_r': 0, 'wb_b': 0, 'h': 0, 's': 0,
          'couleur': 0, 'nettete': 0, 'bruit': 0, 'clarte': 0}


def d185_params(d):
    import struct
    n = struct.unpack_from('<H', d, 0)[0]
    off = len(d) - 4 * n
    return off, list(struct.unpack_from(f'<{n}i', d, off))


def vers_d185(rec):
    """Recette (unités de l'écran du boîtier : tons et couleur en crans, 0,5 permis pour h et s) → {index: valeur}."""
    p = {}
    for k in ('sim', 'dr', 'drp', 'grain', 'cc', 'ccb', 'wb', 'wb_r', 'wb_b', 'kelvin'):
        if k in rec and rec[k] is not None:
            p[IDX[k]] = int(rec[k])
    for k in ('h', 's', 'couleur', 'nettete', 'clarte'):
        if k in rec and rec[k] is not None:
            p[IDX[k]] = int(round(rec[k] * 10))
    if rec.get('bruit') is not None:
        p[IDX['bruit']] = BRUIT[int(rec['bruit'])]
    for k in ('mono_wc', 'mono_mg'):
        if rec.get(k) is not None and IDX_MONO[k] is not None:
            p[IDX_MONO[k]] = int(round(rec[k] * 10))
    if rec.get('wb'):
        # index 11 : balance de la prise de vue (mesuré sur le boîtier) : à 1, le boîtier la garde
        # et ignore wb / kelvin ; à 0, il les applique (mesuré sur le boîtier le 29/10/2026)
        p[IDX['wb_cond']] = 0
    if rec.get('brut'):
        p.update({int(i): int(v) for i, v in rec['brut'].items()})
    return p


def profil(base, rec):
    import struct
    d = bytearray(base)
    off, _ = d185_params(d)
    for i, v in vers_d185(rec).items():
        struct.pack_into('<i', d, off + 4 * i, v)
    return bytes(d)


def cle(rec):
    """Identifiant stable d'une recette (sans le grain s'il est coupé : la mesure se fait grain coupé)."""
    r = {k: v for k, v in sorted(rec.items()) if v is not None and k not in ('nom', 'source')}
    return hashlib.sha1(json.dumps(r, sort_keys=True, default=float).encode()).hexdigest()[:16]


# ---------------------------------------------------------------------------------------------------------------
# 2. .FP1 (format X RAW Studio, comme les presets de presets/recettes-2022) : lecture et écriture
# ---------------------------------------------------------------------------------------------------------------
def lire_fp1(chemin):
    import re
    t = pathlib.Path(chemin).read_text(encoding='utf-8', errors='replace')
    c = dict(re.findall(r'<(\w+)>([^<]*)</\1>', t))
    lab = re.search(r'label="([^"]*)"', t)
    rec = {'nom': lab.group(1) if lab else pathlib.Path(chemin).stem, 'source': pathlib.Path(chemin).name}
    rec['sim'] = SIM_FP1[c['FilmSimulation']]
    dr = c.get('DynamicRange', '100')
    rec['dr'] = int(dr) if dr.isdigit() else 100           # AUTO : rendu en DR100 (tous les RAF sont en DR100)
    rec['drp'] = {'WEAK': 1, 'STRONG': 2}.get(dr, 0)
    g, t_ = c.get('GrainEffect', 'OFF'), c.get('GrainEffectSize', 'SMALL')
    rec['grain'] = {('OFF', 'SMALL'): 1, ('OFF', 'LARGE'): 1}.get((g, t_)) or {v: k for k, v in GRAIN.items()}[(g, t_)]
    rec['cc'] = {v: k for k, v in NIVEAU.items()}[c.get('ChromeEffect', 'OFF')]
    rec['ccb'] = {v: k for k, v in NIVEAU.items()}[c.get('ColorChromeBlue', 'OFF')]
    w = c.get('WhiteBalance', 'Auto')
    if w.endswith('K'):
        rec['wb'], rec['kelvin'] = WB['Temperature'], int(w[:-1])
    else:
        rec['wb'] = WB[w]
        if w == 'Temperature':
            rec['kelvin'] = int(c['WBColorTemp'].rstrip('K'))
    rec['wb_r'], rec['wb_b'] = int(c.get('WBShiftR', 0)), int(c.get('WBShiftB', 0))
    rec['h'], rec['s'] = float(c.get('HighlightTone', 0)), float(c.get('ShadowTone', 0))
    rec['couleur'] = 0 if rec['sim'] in SIMS_MONO else float(c.get('Color', 0))
    rec['nettete'], rec['bruit'], rec['clarte'] = float(c.get('Sharpness', 0)), int(c.get('NoisReduction', 0)), float(c.get('Clarity', 0))
    if rec['sim'] in SIMS_MONO:
        rec['mono_wc'], rec['mono_mg'] = float(c.get('BlackImageTone', 0)), float(c.get('MonochromaticColor_RG', 0))
    return rec


def ecrire_fp1(rec, chemin, label):
    """Écrit une recette au format des .FP1 de 2022 (mêmes champs, device="X-T4")."""
    def n(v):
        return str(int(v)) if float(v).is_integer() else f'{v:.1f}'
    mono = rec['sim'] in SIMS_MONO
    g, t = GRAIN[rec.get('grain', 1)]
    wb = WB_NOM[rec['wb']] if rec['wb'] else 'Auto'
    import re
    modele = (PRESETS / 'NZD Tri-X.FP1').read_text(encoding='utf-8')   # même numéro de série que les profils de 2022
    serie = re.search(r'<SerialNumber>([^<]*)<', modele).group(1)
    champs = [
        ('SerialNumber', serie), ('TetherRAWConditonCode', 'X-T4_0100'), ('Editable', 'TRUE'), ('SourceFileName', None),
        ('Fileerror', 'NONE'), ('RotationAngle', '0'), ('StructVer', '65536'), ('IOPCode', 'FF159505'),
        ('ShootingCondition', 'OFF'), ('FileType', 'JPG'), ('ImageSize', 'L3x2'), ('ImageQuality', 'Fine'),
        ('ExposureBias', '0'), ('DynamicRange', str(rec.get('dr', 100))), ('WideDRange', '0'),
        ('FilmSimulation', FP1_SIM[rec['sim']]), ('BlackImageTone', n(rec.get('mono_wc', 0) if mono else 0)),
        ('MonochromaticColor_RG', n(rec.get('mono_mg', 0) if mono else 0)), ('GrainEffect', g), ('GrainEffectSize', t),
        ('ChromeEffect', NIVEAU[rec.get('cc', 1)]), ('ColorChromeBlue', NIVEAU[rec.get('ccb', 1)]), ('SmoothSkinEffect', 'OFF'),
        ('WBShootCond', 'OFF'), ('WhiteBalance', wb), ('WBShiftR', str(int(rec.get('wb_r', 0)))),
        ('WBShiftB', str(int(rec.get('wb_b', 0)))), ('WBColorTemp', f"{rec['kelvin']}K" if wb == 'Temperature' else '10000K'),
        ('HighlightTone', n(rec.get('h', 0))), ('ShadowTone', n(rec.get('s', 0))), ('Color', n(0 if mono else rec.get('couleur', 0))),
        ('Sharpness', n(rec.get('nettete', 0))), ('NoisReduction', str(int(rec.get('bruit', 0)))), ('Clarity', n(rec.get('clarte', 0))),
        ('LensModulationOpt', 'ON'), ('ColorSpace', 'sRGB'), ('HDR', None), ('DigitalTeleConv', 'OFF')]
    lignes = ['<?xml version="1.0" encoding="utf-8"?>', '<ConversionProfile application="XRFC" version="1.12.0.0">',
              f'    <PropertyGroup device="X-T4" version="X-T4_0100" label="{label}">']
    for k, v in champs:
        lignes.append(f'        <{k}/>' if v is None or v == '' else f'        <{k}>{v}</{k}>')
    lignes += ['    </PropertyGroup>', '</ConversionProfile>', '']
    pathlib.Path(chemin).write_bytes('\r\n'.join(lignes).encode('utf-8'))   # fins de ligne CRLF, comme ses .FP1


# ---------------------------------------------------------------------------------------------------------------
# 3. Banc : pilotage de xt4_banc (un seul à la fois)
# ---------------------------------------------------------------------------------------------------------------
class Banc:
    def __init__(self, exe=None):
        exe = exe or BANC
        if not exe or not os.path.exists(exe):
            raise SystemExit('XT4_BANC : binaire de xt4_banc.swift introuvable')
        self.p = subprocess.Popen([exe], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, bufsize=1)
        r = self.p.stdout.readline().strip()
        if not r.startswith('OK'):
            self.p.kill()
            raise SystemExit(f'banc : {r or "muet"} (boîtier débranché, éteint, batterie ?)')
        self.charge = None

    def _cmd(self, *champs):
        self.p.stdin.write('\t'.join(map(str, champs)) + '\n')
        self.p.stdin.flush()
        r = self.p.stdout.readline().strip()
        if not r.startswith('OK'):
            raise RuntimeError(f'banc : {r or "muet (boîtier perdu ?)"}')
        return r

    def charger(self, raf, base):
        if self.charge != raf:
            self._cmd('charger', raf, base)
            self.charge = raf

    def rendre(self, prof, jpg):
        return self._cmd('rendre', prof, jpg)

    def fermer(self):
        try:
            self._cmd('fin')
        except Exception:  # noqa: BLE001
            pass
        self.p.wait(timeout=10)


# ---------------------------------------------------------------------------------------------------------------
# 4. Préparation : RAW linéaire, géométrie, blocs
# ---------------------------------------------------------------------------------------------------------------
B = 16                       # côté d'un bloc, en pixels du JPEG S (3120 × 2080)
PAR_RAF = 1000               # blocs gardés par RAF
M709 = np.array([[0.4124564, 0.3575761, 0.1804375], [0.2126729, 0.7151522, 0.0721750], [0.0193339, 0.1191920, 0.9503041]])


def rafs():
    return sorted(str(p) for p in (CHANTIER / 'raf').glob('*.RAF'))


def nom_raf(raf):
    return pathlib.Path(raf).stem


RAF_TSV = DONNEES / 'xt4-mesure-raf.tsv'      # nom, chemin d'origine, sha256, taille : de quoi refaire la copie des RAF


def _sha256(p):
    h = hashlib.sha256()
    with open(p, 'rb') as fh:
        for b in iter(lambda: fh.read(1 << 22), b''):
            h.update(b)
    return h.hexdigest()


def inventaire_rafs(index_tsv):
    """Écrit RAF_TSV d'après les RAF du chantier ; index_tsv : « numéro<TAB>chemin d'origine » (l'index du tri des RAF).
    Vérifie que chaque original est identique à sa copie (sha256)."""
    orig = dict(l.split('\t', 1) for l in pathlib.Path(index_tsv).read_text().splitlines() if '\t' in l)
    lignes = ['nom\torigine\tsha256\ttaille']
    for raf in rafs():
        n = nom_raf(raf)
        o = orig[n.split('-')[0]].strip()
        assert pathlib.Path(o).stem == n.split('-', 1)[1], (n, o)
        h = _sha256(raf)
        assert h == _sha256(o), f'{n} : l\'original a changé depuis la copie'
        lignes.append(f'{n}\t{o}\t{h}\t{pathlib.Path(raf).stat().st_size}')
    RAF_TSV.write_text('\n'.join(lignes) + '\n')
    print(RAF_TSV, len(lignes) - 1, 'RAF')


def copier_rafs():
    """Refait la copie des RAF dans CHANTIER/raf d'après RAF_TSV (les originaux sont seulement lus), sha256 vérifié."""
    import shutil
    (CHANTIER / 'raf').mkdir(parents=True, exist_ok=True)
    for l in RAF_TSV.read_text().splitlines()[1:]:
        n, o, h, t = l.split('\t')[:4]          # colonnes suivantes : moitié, ISO, balance, blocs (xt4_recherche_v2)
        dest = CHANTIER / 'raf' / f'{n}.RAF'
        if dest.exists() and dest.stat().st_size == int(t):
            continue
        part = dest.with_suffix('.partiel')
        shutil.copyfile(o, part)
        if _sha256(part) != h:
            raise RuntimeError(f'{n} : {o} ne correspond plus au sha256 inventorié (copie laissée en {part.name})')
        part.rename(dest)
        print('copié', n)


def lineaire(raf):
    """RAW en demi-résolution : RVB caméra, noir soustrait, fraction de la pleine échelle, SANS balance (pour repérer
    l'écrêtage) ; renvoie (image, balance de la prise de vue normalisée au vert, matrice caméra équilibrée → sRGB linéaire)."""
    import rawpy
    with rawpy.imread(raf) as r:
        a = r.postprocess(half_size=True, output_color=rawpy.ColorSpace.raw, gamma=(1, 1), no_auto_bright=True,
                          use_camera_wb=False, user_wb=[1, 1, 1, 1], output_bps=16, user_flip=0).astype(np.float32) / 65535
        wb = np.array(r.camera_whitebalance[:3], float)
        cm = np.array(r.rgb_xyz_matrix)[:3]           # XYZ (D65) → caméra : ColorMatrix Adobe du X-T4 (table de LibRaw)
    wb = wb / wb[1]
    cam_rgb = cm @ M709                                # sRGB linéaire → caméra
    cam_rgb = cam_rgb / cam_rgb.sum(1, keepdims=True)  # un blanc sRGB → (1, 1, 1) caméra équilibrée (comme dcraw)
    return a, wb, np.linalg.inv(cam_rgb)


def jpeg(chemin):
    from PIL import Image
    return np.asarray(Image.open(chemin).convert('RGB'))


def geometrie(lin, jp):
    """JPEG S (x, y) → RAW demi-résolution (x, y) : similitude + distorsion radiale (k1, k2, k3) autour du centre du JPEG,
    ajustée sur des points SIFT appariés (OpenCV), tri RANSAC. Même modèle que d750_blocs.geometrie."""
    import cv2
    from scipy.optimize import least_squares
    g_l = np.clip(lin.mean(2) / max(np.percentile(lin.mean(2), 99.5), 1e-6), 0, 1) ** (1 / 2.2)
    g_j = jp.mean(2) / 255
    sift = cv2.SIFT_create(nfeatures=6000)
    det = []
    for im in (g_l, g_j):
        u8 = (np.clip(cv2.resize(im.astype(np.float32), None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA), 0, 1) * 255).astype(np.uint8)
        kp, des = sift.detectAndCompute(u8, None)
        det.append((np.array([k.pt for k in kp]) * 2, des))
    mt = cv2.BFMatcher(cv2.NORM_L2).knnMatch(det[1][1], det[0][1], k=2)
    bons = [m for m, n in (x for x in mt if len(x) == 2) if m.distance < 0.75 * n.distance]
    pj = np.array([det[1][0][m.queryIdx] for m in bons])
    pl = np.array([det[0][0][m.trainIdx] for m in bons])
    A, inl = cv2.estimateAffinePartial2D(pj, pl, method=cv2.RANSAC, ransacReprojThreshold=3, maxIters=5000)
    inl = inl.ravel().astype(bool)
    pj, pl = pj[inl], pl[inl]
    cj = np.array([jp.shape[1], jp.shape[0]]) / 2
    nrm = np.hypot(*cj)

    def proj(p, q):
        u = (q - cj) / nrm
        r2 = (u ** 2).sum(1, keepdims=True)
        u = u * (1 + p[4] * r2 + p[5] * r2 ** 2 + p[6] * r2 ** 3)
        c, s = np.cos(p[3]), np.sin(p[3])
        return np.c_[c * u[:, 0] - s * u[:, 1], s * u[:, 0] + c * u[:, 1]] * p[2] * nrm + p[:2]
    s0 = np.hypot(A[0, 0], A[1, 0])
    p0 = np.r_[A @ np.r_[cj, 1], s0, np.arctan2(A[1, 0], A[0, 0]), 0, 0, 0]
    res = least_squares(lambda p: (proj(p, pj) - pl).ravel(), p0, loss='soft_l1', f_scale=1)
    err = np.hypot(*(proj(res.x, pj) - pl).T)
    return res.x, proj, {'points': int(len(pj)), 'residu_median_px': round(float(np.median(err)), 3),
                         'residu_p95_px': round(float(np.percentile(err, 95)), 3)}


def moyennes_blocs(jp, idx=None):
    """Moyenne (et écart-type) des blocs B × B d'un JPEG S ; idx : indices à plat des blocs voulus."""
    H, W = jp.shape[0] // B * B, jp.shape[1] // B * B
    a = jp[:H, :W].astype(np.float32).reshape(H // B, B, W // B, B, 3).transpose(0, 2, 1, 3, 4).reshape(-1, B * B, 3)
    if idx is not None:
        a = a[idx]
    return a.mean(1), a.std(1)


def preparer(banc_exe=None, graine=0):
    """Pour chaque RAF : profil d'origine (lu sur le boîtier), rendu de référence Provia neutre (gardé), RAW linéaire,
    géométrie, blocs uniformes. Écrit CHANTIER/blocs/<raf>.npz."""
    from scipy.ndimage import map_coordinates
    if RAF_TSV.exists():
        copier_rafs()
    (CHANTIER / 'blocs').mkdir(exist_ok=True)
    (CHANTIER / 'base').mkdir(exist_ok=True)
    (CHANTIER / 'reference').mkdir(exist_ok=True)
    banc = None
    for raf in rafs():
        n = nom_raf(raf)
        base, ref = CHANTIER / 'base' / f'{n}.bin', CHANTIER / 'reference' / f'{n}-provia-neutre.jpg'
        if not ref.exists():
            banc = banc or Banc(banc_exe)
            banc.charger(raf, str(base))
            pf = CHANTIER / 'base' / f'{n}-neutre.bin'
            pf.write_bytes(profil(base.read_bytes(), NEUTRE))
            banc.rendre(str(pf), str(ref))
        if (CHANTIER / 'blocs' / f'{n}.npz').exists():
            continue
        lin, wb, rgb_cam = lineaire(raf)
        jp = jpeg(ref)
        p, proj, qual = geometrie(lin * wb, jp)
        H, W = jp.shape[0] // B * B, jp.shape[1] // B * B
        ny, nx = H // B, W // B
        sous = 4
        o = (np.arange(sous) + 0.5) * B / sous
        gy, gx = np.meshgrid(np.arange(ny) * B, np.arange(nx) * B, indexing='ij')
        forme = (ny, nx, sous, sous)
        py = np.broadcast_to(gy[..., None, None] + o[:, None], forme).reshape(-1)
        px = np.broadcast_to(gx[..., None, None] + o[None, :], forme).reshape(-1)
        q = proj(p, np.c_[px, py])
        dedans = ((q[:, 0] > 2) & (q[:, 0] < lin.shape[1] - 3) & (q[:, 1] > 2) & (q[:, 1] < lin.shape[0] - 3)).reshape(ny * nx, -1).all(1)
        rv = np.stack([map_coordinates(lin[..., c], [q[:, 1], q[:, 0]], order=1, mode='nearest') for c in range(3)], -1)
        rb = rv.reshape(ny * nx, sous * sous, 3)
        brut_max = rb.max(1).max(1)
        rb = rb * wb
        m, s = rb.mean(1), rb.std(1)
        jm, js = moyennes_blocs(jp)
        ok = dedans & (brut_max < 0.92) & (m.min(1) > 2e-4)
        ok &= (s / np.maximum(m, 1e-6)).max(1) < 0.06
        ok &= js.max(1) < np.maximum(4.0, 0.05 * jm.mean(1))
        rng = np.random.default_rng(graine)
        idx = np.flatnonzero(ok)
        idx = np.sort(rng.choice(idx, min(PAR_RAF, len(idx)), replace=False))
        srgb = m[idx] @ rgb_cam.T                       # sRGB linéaire (D65), échelle RAW (fraction de la pleine échelle)
        np.savez_compressed(CHANTIER / 'blocs' / f'{n}.npz', idx=idx, srgb=srgb.astype(np.float32), jpg_ref=jm[idx].astype(np.float32),
                            wb=wb, rgb_cam=rgb_cam, geometrie=p, qualite=json.dumps(qual), uniformes=int(ok.sum()), grille=np.array([ny, nx]))
        print(f'{n} : {qual}, {int(ok.sum())} blocs uniformes, {len(idx)} gardés', flush=True)
    if banc:
        banc.fermer()


def charger_blocs():
    out = {}
    for f in sorted((CHANTIER / 'blocs').glob('*.npz')):      # d'après les blocs : les mesures se rejouent sans les RAF
        d = dict(np.load(f))
        d['raf'] = str(CHANTIER / 'raf' / f'{f.stem}.RAF')
        out[f.stem] = d
    return out


# ---------------------------------------------------------------------------------------------------------------
# 5. Échelle d'exposition et cibles
# ---------------------------------------------------------------------------------------------------------------
def _dm():
    import d750_modele as dm
    return dm


def etalonner():
    """Valeur RAW (Y en sRGB linéaire, fraction de la pleine échelle) que le Provia neutre du boîtier rend à 118/255 :
    droite L* = a + b log2 Y sur les blocs peu colorés (rapport des canaux < 1,5) entre L* 30 et 70, RAF par RAF ;
    la médiane des RAF donne l'échelle commune (gris de 18 %). Écrit CHANTIER/etalonnage.json."""
    dm = _dm()
    L118 = float(dm.code_lab(np.array([118 / 255] * 3))[0])
    par = {}
    for n, d in charger_blocs().items():
        s = d['srgb']
        Y = s @ M709[1]
        L = dm.code_lab(d['jpg_ref'] / 255)[:, 0]
        m = (s.min(1) > 0) & (s.max(1) / np.maximum(s.min(1), 1e-9) < 1.5) & (L > 30) & (L < 70)
        if m.sum() >= 20:
            b, a = np.polyfit(np.log2(Y[m]), L[m], 1)
            par[n] = {'blocs': int(m.sum()), 'pente': round(float(b), 2), 'log2_y18': round(float((L118 - a) / b), 3)}
    v = np.array([p['log2_y18'] for p in par.values()])
    out = {'L118': L118, 'log2_y18': float(np.median(v)), 'y18': float(2 ** np.median(v)),
           'ecart_type_entre_raf_il': round(float(v.std()), 3), 'par_raf': par}
    (CHANTIER / 'etalonnage.json').write_text(json.dumps(out, indent=1, ensure_ascii=False))
    print(json.dumps({k: out[k] for k in ('log2_y18', 'y18', 'ecart_type_entre_raf_il')}), len(par), 'RAF')
    return out


def scene(d, y18):
    """sRGB linéaire et XYZ D65 de la scène, gris de 18 % = 0,18."""
    s = d['srgb'] * (0.18 / y18)
    return s, s @ M709.T


FILMS_NB = {'trix': 'trix_fiche', 'hp5': 'hp5_fiche', 'fp4': 'fp4'}
NOMS_FILMS = {'trix': 'Tri-X 400', 'hp5': 'HP5 Plus', 'fp4': 'FP4 Plus', 'portra': 'Portra 400'}


def courbe_nb(film, v, densite=False):
    """Courbe film + tirage grade 2 de films_nb.courbe, sur une entrée linéaire quelconque v (gris 18 % → v = 0,18 rendu à
    118/255), prolongée au-delà de 1 (films_nb tabule 0..1) : même négatif, même papier, même exposition du tirage."""
    import films_nb as fn
    from scipy.optimize import brentq
    if not hasattr(courbe_nb, 'pret'):
        fn.fiches_exactes()
        courbe_nb.pret = True
    pap = fn.PAPIER
    cc = np.array(fn.CC[film])
    voile = cc[:, 1].min()
    logH_gris = np.interp(voile + 0.1, cc[:, 1], cc[:, 0]) + 1.0
    pente = 0.0 if film == 'fp4' else (cc[-1, 1] - cc[-4, 1]) / (cc[-1, 0] - cc[-4, 0])

    def D(v):
        logH = logH_gris + np.log10(np.maximum(v, 1e-6) / 0.18)
        return np.where(logH > cc[-1, 0], cc[-1, 1] + pente * (logH - cc[-1, 0]), np.interp(logH, cc[:, 0], cc[:, 1]))

    def tirage(decal, v):
        Rp = 10 ** -fn.logistique_papier(decal - D(v), pap)
        lin = np.clip((Rp - 10 ** -pap['dmax']) / (10 ** -pap['dmin'] - 10 ** -pap['dmax']), 0, 1)
        return _dm().oetf(lin)
    decal = brentq(lambda dd: tirage(dd, np.array([0.18]))[0] * 255 - 118, -3, 6)
    if densite:
        return tirage(decal, np.asarray(v, float)), D(np.asarray(v, float))
    return tirage(decal, np.asarray(v, float))


def poids_nb(film):
    import films_nb as fn
    if not hasattr(courbe_nb, 'pret'):
        fn.fiches_exactes()
        courbe_nb.pret = True
    return fn.poids(FILMS_NB[film], fn.sens_srgb())[0]


def cibles(y18):
    """Lab cible de chaque bloc, pour chaque film : {film: {raf: Lab}} ; et Lab de la scène (catégories de couleur)."""
    dm = _dm()
    import d750_cibles as dc
    portra = dc.paires(RACINE / 'd750' / 'recherche' / 'donnees-films' / 'd750-seances' / 'portra-preset-regle.json')
    w = {f: poids_nb(f) for f in FILMS_NB}
    out = {f: {} for f in list(FILMS_NB) + ['portra']}
    sc = {}
    for n, d in charger_blocs().items():
        s, X = scene(d, y18)
        sc[n] = dm.xyz_lab(X)
        for f in FILMS_NB:
            g = courbe_nb(FILMS_NB[f], np.clip(s @ w[f], 0, None))
            out[f][n] = dm.code_lab(np.repeat(g[:, None], 3, 1))
        out['portra'][n] = portra(X)
    return out, sc


# ---------------------------------------------------------------------------------------------------------------
# 6. Rendus (avec cache) et écarts
# ---------------------------------------------------------------------------------------------------------------
class Rendus:
    """Rend des recettes sur des RAF (le boîtier) et garde la moyenne de chaque bloc mesuré (cache sur disque)."""

    def __init__(self, banc_exe=None):
        self.banc_exe = banc_exe
        self.banc = None
        self.blocs = charger_blocs()
        self.cache = CHANTIER / 'cache'
        self.cache.mkdir(exist_ok=True)
        self.n_rendus = 0
        self.t_banc = 0.0

    def chemin(self, n, rec):
        return self.cache / n / f'{cle(rec)}.npy'

    def lot(self, recettes, noms=None, garder=None):
        """Rend ce qui manque ; garder : dossier où conserver les JPEG (sinon un seul fichier temporaire réécrit)."""
        noms = noms or list(self.blocs)
        for n in noms:
            manque = [r for r in recettes if not self.chemin(n, r).exists() or (garder and not (pathlib.Path(garder) / f'{n}-{cle(r)}.jpg').exists())]
            if not manque:
                continue
            if self.banc is None:
                self.banc = Banc(self.banc_exe)
            (self.cache / n).mkdir(exist_ok=True)
            base = CHANTIER / 'base' / f'{n}.bin'
            t0 = time.time()
            self.banc.charger(self.blocs[n]['raf'], str(base))
            b = base.read_bytes()
            for r in manque:
                pf = CHANTIER / 'tmp-profil.bin'
                pf.write_bytes(profil(b, r))
                jp = (pathlib.Path(garder) / f'{n}-{cle(r)}.jpg') if garder else CHANTIER / 'tmp-rendu.jpg'
                if jp.exists() and not garder:
                    jp.unlink()
                if not jp.exists():
                    self.banc.rendre(str(pf), str(jp))
                    self.n_rendus += 1
                m, _ = moyennes_blocs(jpeg(jp), self.blocs[n]['idx'])
                np.save(self.chemin(n, r), m.astype(np.float32))
            self.t_banc += time.time() - t0

    def moyennes(self, n, rec):
        return np.load(self.chemin(n, rec))

    def fermer(self):
        if self.banc:
            self.banc.fermer()
            self.banc = None


def quantile_pondere(e, w, q):
    o = np.argsort(e)
    c = np.cumsum(w[o])
    return float(np.interp(q * c[-1], c, e[o]))


def ecarts(rendus, film, rec, cib, noms=None):
    """Écart bloc par bloc, RAF par RAF : |ΔL*| pour le N&B, ΔE2000 pour la couleur."""
    dm = _dm()
    out = {}
    for n in (noms or list(rendus.blocs)):
        L = dm.code_lab(rendus.moyennes(n, rec) / 255)
        T = cib[film][n]
        out[n] = np.abs(L[:, 0] - T[:, 0]) if film in FILMS_NB else dm.de2000(L, T)
    return out


def resume(e):
    """Médiane et p90 sur l'ensemble, chaque RAF pesant autant ; score = médiane + 0,25 p90 (convention du D750)."""
    v = np.concatenate(list(e.values()))
    w = np.concatenate([np.full(len(x), 1 / len(x)) for x in e.values()])
    med, p90 = quantile_pondere(v, w, 0.5), quantile_pondere(v, w, 0.9)
    return {'mediane': round(med, 2), 'p90': round(p90, 2), 'score': round(med + 0.25 * p90, 3)}


# ---------------------------------------------------------------------------------------------------------------
# 7. Recherche : grille grossière, puis descente coordonnée par coordonnée, puis raffinements à deux paramètres
# ---------------------------------------------------------------------------------------------------------------
# descente : tons par cran entier et décalages de balance par 3 crans ; les raffinements 5 × 5 descendent ensuite au
# demi-cran (tons) et au cran (balance) autour de l'optimum
TONS = list(range(-2, 5))
DECALAGES = [-9, -6, -3, 0, 3, 6, 9]
DOMAINES_NB = {'h': TONS, 's': TONS, 'wb_r': DECALAGES, 'wb_b': DECALAGES, 'sim': [12, 13, 14, 15, 6, 7, 8, 9]}
DOMAINES_COULEUR = {'h': TONS, 's': TONS, 'couleur': list(range(-4, 5)), 'wb_r': DECALAGES, 'wb_b': DECALAGES,
                    'cc': [1, 2, 3], 'ccb': [1, 2, 3], 'sim': [17, 5, 4, 3, 1, 11, 16, 2]}
RECHERCHE = ['006-DSCF9213', '041-DSCF6283', '098-DSCF9209', '131-DSCF9386', '157-DSCF9412', '163-DSCF9423',
             '167-DSCF0467', '176-DSCF0476']          # 8 RAF pour chercher ; les 8 autres sont tenus à part


def journal(msg):
    print(msg, flush=True)
    with open(CHANTIER / 'recherche.log', 'a', encoding='utf-8') as f:
        f.write(time.strftime('%H:%M:%S ') + msg + '\n')


def evaluer(R, films, cands, cib, noms):
    """Rend tous les candidats (un seul passage par RAF) et note chacun pour chaque film."""
    uniques = list({cle(c): c for cs in cands.values() for c in cs}.values())
    R.lot(uniques, noms)
    return {f: [(resume(ecarts(R, f, c, cib, noms))['score'], c) for c in cands[f]] for f in films}


def descente(R, cib, departs, domaines, noms, tours=3, lisible=''):
    """departs : {film: recette} ; une coordonnée à la fois pour tous les films (renders partagés)."""
    best = {f: (resume(ecarts(R, f, r, cib, noms))['score'], r) for f, r in departs.items()} if all(
        all(R.chemin(n, r).exists() for n in noms) for r in departs.values()) else None
    if best is None:
        best = {f: v[0] for f, v in evaluer(R, list(departs), {f: [r] for f, r in departs.items()}, cib, noms).items()}
    for t in range(tours):
        bouge = False
        for p, vals in domaines.items():
            cands = {f: [dict(best[f][1], **{p: v}) for v in vals] for f in departs}
            res = evaluer(R, list(departs), cands, cib, noms)
            for f in departs:
                s, c = min(res[f], key=lambda x: x[0])
                if s < best[f][0] - 1e-3:
                    best[f] = (s, c)
                    bouge = True
                journal(f'{lisible} tour {t + 1} {p:7s} {f:6s} {best[f][0]:.3f} {recette_txt(best[f][1])}  [{R.n_rendus} rendus, {R.t_banc / 60:.1f} min]')
        if not bouge:
            break
    return best


def raffiner(R, cib, best, paires, noms, pas=None, lisible='', rayon=2):
    """Grilles 5 × 5 autour de l'optimum sur des couples de paramètres liés (tons ; décalages de balance)."""
    pas = pas or {'h': 0.5, 's': 0.5, 'wb_r': 1, 'wb_b': 1, 'couleur': 1}
    bornes = {'h': (-2, 4), 's': (-2, 4), 'wb_r': (-9, 9), 'wb_b': (-9, 9), 'couleur': (-4, 4)}
    for a, b in paires:
        cands = {}
        for f, (s, r) in best.items():
            va = [r[a] + k * pas[a] for k in range(-rayon, rayon + 1) if bornes[a][0] <= r[a] + k * pas[a] <= bornes[a][1]]
            vb = [r[b] + k * pas[b] for k in range(-rayon, rayon + 1) if bornes[b][0] <= r[b] + k * pas[b] <= bornes[b][1]]
            cands[f] = [dict(r, **{a: x, b: y}) for x in va for y in vb]
        res = evaluer(R, list(best), cands, cib, noms)
        for f in best:
            s, c = min(res[f], key=lambda x: x[0])
            if s < best[f][0] - 1e-3:
                best[f] = (s, c)
            journal(f'{lisible} raffinement {a}×{b} {f:6s} {best[f][0]:.3f} {recette_txt(best[f][1])}')
    return best


def recette_txt(r):
    t = [SIMS[r['sim']]]
    if r.get('dr', 100) != 100:
        t.append(f"DR{r['dr']}")
    t.append(f"H {r.get('h', 0):+g} S {r.get('s', 0):+g}")
    if r['sim'] not in SIMS_MONO:
        t.append(f"couleur {r.get('couleur', 0):+g}")
    t.append(f"BB R{r.get('wb_r', 0):+d} B{r.get('wb_b', 0):+d}")
    if r.get('cc', 1) != 1 or r.get('ccb', 1) != 1:
        t.append(f"CC {NIVEAU[r.get('cc', 1)].lower()} / FX bleu {NIVEAU[r.get('ccb', 1)].lower()}")
    if r.get('clarte', 0):
        t.append(f"clarté {r['clarte']:+g}")
    if r.get('mono_wc') or r.get('mono_mg'):
        t.append(f"mono WC {r.get('mono_wc', 0):+g} MG {r.get('mono_mg', 0):+g}")
    return ', '.join(t)


def presets_existants():
    """.FP1 de 2022 pertinents : tous les N&B (simulations monochromes), et les Portra."""
    import re
    nb, portra = [], []
    for p in sorted(PRESETS.glob('*.FP1')):
        r = lire_fp1(p)
        if r['sim'] in SIMS_MONO:
            nb.append(r)
        elif re.search(r'portra(?!it)|porta\b', p.stem.lower()):
            portra.append(r)
    return nb, portra


def pour_mesure(r):
    """Une recette telle qu'on la mesure : grain coupé, DR100 (DR200/400 ne s'appliquent pas proprement à la conversion
    d'un RAF pris en DR100 : dominante verte, mesuré), balance de la prise de vue (le mode de balance du profil n'est pas
    appliqué par la conversion : seuls les décalages R/B le sont, mesuré)."""
    m = {k: v for k, v in r.items() if k not in ('nom', 'source', 'kelvin')}
    m.update(grain=1, dr=100, drp=0, wb=0)
    return m


def existantes(banc_exe=None):
    et = json.loads((CHANTIER / 'etalonnage.json').read_text())
    cib, _ = cibles(et['y18'])
    R = Rendus(banc_exe)
    nb, portra = presets_existants()
    R.lot([pour_mesure(r) for r in nb + portra])
    R.fermer()
    out = {}
    for f in ('trix', 'hp5', 'fp4', 'portra'):
        liste = portra if f == 'portra' else nb
        out[f] = sorted(({'nom': r['nom'], 'source': r['source'], 'recette': recette_txt(r), **resume(ecarts(R, f, pour_mesure(r), cib))}
                         for r in liste), key=lambda x: x['score'])
        for x in out[f][:6]:
            journal(f"existante {f} {x['score']:.3f} {x['mediane']} / {x['p90']} {x['nom']} : {x['recette']}")
    (CHANTIER / 'existantes.json').write_text(json.dumps(out, indent=1, ensure_ascii=False))
    return out


def chercher(banc_exe=None, quoi='nb'):
    et = json.loads((CHANTIER / 'etalonnage.json').read_text())
    cib, _ = cibles(et['y18'])
    R = Rendus(banc_exe)
    noms = RECHERCHE
    base = dict(NEUTRE, bruit=0, nettete=0)
    if quoi == 'nb':
        films, doms = ['trix', 'hp5', 'fp4'], DOMAINES_NB
        grille = [dict(base, sim=s, h=h, s=sh) for s in doms['sim'] for h in (-2, 0, 2, 4) for sh in (-2, 0, 2, 4)]
    else:
        films, doms = ['portra'], DOMAINES_COULEUR
        grille = [dict(base, sim=s, couleur=c, h=h, s=sh) for s in doms['sim'] for c in (-4, 0, 4)
                  for h, sh in ((-1, -1), (1, 1), (1, -1))]
    journal(f'--- recherche {quoi} : grille grossière, {len(grille)} recettes × {len(noms)} RAF')
    res = evaluer(R, films, {f: grille for f in films}, cib, noms)
    departs = {}
    for f in films:
        top = sorted(res[f], key=lambda x: x[0])[:3]
        for s, c in top:
            journal(f'grille {f} {s:.3f} {recette_txt(c)}')
        departs[f] = top[0][1]
    best = descente(R, cib, departs, doms, noms, tours=2, lisible=quoi)
    paires = [('h', 's'), ('wb_r', 'wb_b')] + ([('couleur', 'h')] if quoi != 'nb' else [])
    best = raffiner(R, cib, best, paires, noms, lisible=quoi)
    best = descente(R, cib, {f: r for f, (s, r) in best.items()}, {'clarte': [-2, -1, 0, 1, 2]}, noms, tours=1, lisible=quoi + ' clarté')
    R.fermer()
    out = {f: {'score_recherche': s, 'recette': r, 'texte': recette_txt(r)} for f, (s, r) in best.items()}
    old = json.loads((CHANTIER / 'meilleures.json').read_text()) if (CHANTIER / 'meilleures.json').exists() else {}
    old.update(out)
    (CHANTIER / 'meilleures.json').write_text(json.dumps(old, indent=1, ensure_ascii=False))
    journal(f'--- fin {quoi} : {R.n_rendus} rendus, {R.t_banc / 60:.1f} min de boîtier')
    return out


def polir(banc_exe=None):
    """Dernier passage coordonnée par coordonnée, au pas fin (tons ±0,5, couleur et balance ±1, simulation et Color Chrome
    en entier), après les raffinements : rattrape une interaction laissée par le changement de balance."""
    et = json.loads((CHANTIER / 'etalonnage.json').read_text())
    cib, _ = cibles(et['y18'])
    best = json.loads((CHANTIER / 'meilleures.json').read_text())
    R = Rendus(banc_exe)
    bornes = {'h': (-2, 4), 's': (-2, 4), 'wb_r': (-9, 9), 'wb_b': (-9, 9), 'couleur': (-4, 4)}
    for f, b in best.items():
        r = b['recette']
        pas = {'h': 0.5, 's': 0.5, 'wb_r': 1, 'wb_b': 1} | ({} if f in FILMS_NB else {'couleur': 1})
        doms = {k: [v for v in (r.get(k, 0) - d, r.get(k, 0), r.get(k, 0) + d) if bornes[k][0] <= v <= bornes[k][1]] for k, d in pas.items()}
        doms['sim'] = DOMAINES_NB['sim'] if f in FILMS_NB else DOMAINES_COULEUR['sim']
        if f not in FILMS_NB:
            doms['cc'], doms['ccb'] = [1, 2, 3], [1, 2, 3]
        res = descente(R, cib, {f: r}, doms, RECHERCHE, tours=2, lisible='polir')
        s_, r_ = res[f]
        if s_ < b['score_recherche'] - 1e-3:
            best[f] = {'score_recherche': s_, 'recette': r_, 'texte': recette_txt(r_)}
    R.fermer()
    (CHANTIER / 'meilleures.json').write_text(json.dumps(best, indent=1, ensure_ascii=False))


def etendre(banc_exe=None):
    """Clarté au-delà de ±2 quand la recherche a buté au bord (+2 ou -2) : essai de ±3 à ±5 sur les 8 RAF de recherche ;
    puis règle de sobriété (voir plus bas)."""
    et = json.loads((CHANTIER / 'etalonnage.json').read_text())
    cib, _ = cibles(et['y18'])
    best = json.loads((CHANTIER / 'meilleures.json').read_text())
    R = Rendus(banc_exe)
    for f, b in best.items():
        c = b['recette'].get('clarte', 0)
        if abs(c) < 2:
            continue
        cands = [dict(b['recette'], clarte=v if c > 0 else -v) for v in (3, 4, 5)]
        R.lot(cands, RECHERCHE)
        for r in cands:
            sc = resume(ecarts(R, f, r, cib, RECHERCHE))['score']
            journal(f"extension clarté {f} {r['clarte']:+g} : {sc:.3f} (actuel {b['score_recherche']:.3f})")
            if sc < best[f]['score_recherche'] - 1e-3:
                best[f] = {'score_recherche': sc, 'recette': r, 'texte': recette_txt(r)}
    # sobriété : la clarté ralentit chaque déclenchement du X-T4 (traitement d'environ 1 s ; ici 1,6 s par rendu contre
    # 0,3 s) ; on ne la garde que si elle gagne au moins 0,05 sur le score
    for f, b in best.items():
        if b['recette'].get('clarte', 0):
            r0 = dict(b['recette'], clarte=0)
            R.lot([r0], RECHERCHE)
            s0 = resume(ecarts(R, f, r0, cib, RECHERCHE))['score']
            garde = s0 - b['score_recherche'] >= 0.05
            journal(f"clarté {f} {b['recette']['clarte']:+g} : {b['score_recherche']:.3f} contre {s0:.3f} sans : {'gardée' if garde else 'retirée'}")
            if not garde:
                best[f] = {'score_recherche': s0, 'recette': r0, 'texte': recette_txt(r0)}
    R.fermer()
    (CHANTIER / 'meilleures.json').write_text(json.dumps(best, indent=1, ensure_ascii=False))


def croise_detail(R, vus, cib, A, Bn):
    """Contrôle croisé sur les candidats rendus : la recette choisie sur A (score), notée sur B (médiane, p90), et l'inverse."""
    out = {}
    for f, cs in vus.items():
        cs = [c for c in cs.values() if all(R.chemin(n, c).exists() for n in A + Bn)]
        par = {cle(c): c for c in cs}
        ra = {k: resume(ecarts(R, f, c, cib, A)) for k, c in par.items()}
        rb = {k: resume(ecarts(R, f, c, cib, Bn)) for k, c in par.items()}
        ka, kb = min(ra, key=lambda k: ra[k]['score']), min(rb, key=lambda k: rb[k]['score'])
        out[f] = {'candidats': len(cs),
                  'choisi_sur_A': {'recette': recette_txt(par[ka]), 'sur_A': ra[ka], 'sur_B': rb[ka]},
                  'choisi_sur_B': {'recette': recette_txt(par[kb]), 'sur_B': rb[kb], 'sur_A': ra[kb]},
                  # anciens champs (scores seuls), gardés pour comparer aux journaux
                  'choisi_sur_A_note_sur_B': rb[ka]['score'], 'choisi_sur_B_note_sur_A': ra[kb]['score'],
                  'meilleur_sur_B': min(v['score'] for v in rb.values()), 'meilleur_sur_A': min(v['score'] for v in ra.values())}
    return out


def final16(banc_exe=None, best8=None, bil=None, rejeu=False):
    """Deuxième temps, après le constat du bilan (la recherche sur 8 RAF a sur-appris : sur les 8 tenus à part, des recettes
    existantes font mieux en N&B) : descente sur les 16 RAF, partant de la meilleure sur 16 entre la recette trouvée et les
    recettes existantes, puis raffinements 3 × 3 au pas fin. Contrôle croisé a posteriori sur tous les candidats rendus :
    choisi sur les 8 RAF de recherche, noté sur les 8 autres, et l'inverse. rejeu : rien d'écrit, renvoie (best, croise, vus)."""
    et = json.loads((CHANTIER / 'etalonnage.json').read_text())
    cib, _ = cibles(et['y18'])
    best8 = best8 or json.loads((CHANTIER / 'meilleures.json').read_text())
    bil = bil or json.loads((DONNEES / 'xt4-recettes-bilan-2026-10-29.json').read_text())
    nb, portra = presets_existants()
    par_nom = {r['nom']: r for r in nb + portra}
    R = Rendus(banc_exe)
    tous = list(R.blocs)
    A, Bn = RECHERCHE, [n for n in tous if n not in RECHERCHE]
    departs = {}
    for f in ('trix', 'hp5', 'fp4', 'portra'):
        lig = bil[f]['recettes']
        k = min((k for k in lig if not k.endswith('neutre')), key=lambda k: lig[k]['tous']['score'])
        r = best8[f]['recette'] if k == 'nouvelle' else dict(pour_mesure(par_nom[k]), nettete=0, bruit=0, mono_wc=0, mono_mg=0) if f in FILMS_NB else dict(pour_mesure(par_nom[k]), nettete=0, bruit=0)
        if f in FILMS_NB:
            r.pop('couleur', None)
            r['couleur'] = 0
        r = dict(r, clarte=0)          # la clarté (1,6 s par rendu) n'est essayée qu'à la fin
        departs[f] = r
        journal(f'final16 {f} : départ {k} ({lig[k]["tous"]["score"]:.3f}, clarté remise à 0) {recette_txt(r)}')
    vus = {f: {} for f in departs}
    vieux = evaluer

    def evaluer_note(R_, films, cands, cib_, noms):
        res = vieux(R_, films, cands, cib_, noms)
        for f in films:
            for c in cands[f]:
                vus[f][cle(c)] = c
        return res
    globals()['evaluer'] = evaluer_note
    try:
        nbf = {f: r for f, r in departs.items() if f in FILMS_NB}
        best = descente(R, cib, nbf, DOMAINES_NB, tous, tours=2, lisible='final16')
        best |= descente(R, cib, {'portra': departs['portra']}, DOMAINES_COULEUR, tous, tours=2, lisible='final16')
        best = raffiner(R, cib, best, [('h', 's'), ('wb_r', 'wb_b')], tous, lisible='final16', rayon=1)
        best = descente(R, cib, {f: r for f, (s_, r) in best.items()}, {'clarte': [0, 2, 4]}, tous, tours=1, lisible='final16 clarté')
    finally:
        globals()['evaluer'] = vieux
    # sobriété de la clarté (même règle que etendre)
    for f, (s_, r) in list(best.items()):
        if r.get('clarte', 0):
            r0 = dict(r, clarte=0)
            R.lot([r0], tous)
            s0 = resume(ecarts(R, f, r0, cib, tous))['score']
            if s0 - s_ < 0.05:
                best[f] = (s0, r0)
            journal(f"final16 clarté {f} {r['clarte']:+g} : {s_:.3f} contre {s0:.3f} sans")
    R.fermer()
    croise = croise_detail(R, vus, cib, A, Bn)
    if rejeu:
        return best, croise, vus
    for f in croise:
        journal(f'final16 croisé {f} {croise[f]}')
    (CHANTIER / 'croise-candidats.json').write_text(json.dumps({f: list(cs.values()) for f, cs in vus.items()}, ensure_ascii=False))
    out = {f: {'score_16': s_, 'recette': r, 'texte': recette_txt(r)} for f, (s_, r) in best.items()}
    (CHANTIER / 'meilleures-8raf.json').write_text(json.dumps(best8, indent=1, ensure_ascii=False))
    (CHANTIER / 'meilleures.json').write_text(json.dumps({f: {'score_recherche': v['score_16'], 'recette': v['recette'], 'texte': v['texte']}
                                                          for f, v in out.items()}, indent=1, ensure_ascii=False))
    (CHANTIER / 'croise.json').write_text(json.dumps(croise, indent=1, ensure_ascii=False))
    for f, v in out.items():
        journal(f"final16 retenu {f} {v['score_16']:.3f} {v['texte']}")


def rejouer_croise():
    """Rejoue final16 sur le cache seul (aucun rendu : le banc est interdit) depuis ce qu'il a lu au départ
    (meilleures-8raf.json, bilan-8raf.json du chantier), pour retrouver ses candidats et le contrôle croisé en médiane et
    p90 ; vérifie que le rejeu redonne les recettes retenues et les scores de croise.json. Écrit donnees/xt4-recettes-croise."""
    class SansBanc:
        def __init__(self, *a, **k):
            raise RuntimeError('rejeu : un rendu manque au cache, rien n\'est rendu')
    g = globals()
    vieux = g['Banc'], g['journal']
    g['Banc'], g['journal'] = SansBanc, (lambda m: None)
    try:
        best, croise, vus = final16(best8=json.loads((CHANTIER / 'meilleures-8raf.json').read_text()),
                                    bil=json.loads((CHANTIER / 'bilan-8raf.json').read_text()), rejeu=True)
    finally:
        g['Banc'], g['journal'] = vieux
    (CHANTIER / 'croise-candidats.json').write_text(json.dumps({f: list(cs.values()) for f, cs in vus.items()}, ensure_ascii=False))
    retenues = json.loads((CHANTIER / 'meilleures.json').read_text())
    ancien = json.loads((CHANTIER / 'croise.json').read_text())
    for f, (s_, r) in best.items():
        assert cle(r) == cle(retenues[f]['recette']), (f, recette_txt(r), retenues[f]['texte'])
        croise[f]['rejeu_contre_journal'] = {k: [croise[f][k], ancien[f][k]] for k in
                                             ('choisi_sur_A_note_sur_B', 'choisi_sur_B_note_sur_A', 'meilleur_sur_A', 'meilleur_sur_B')
                                             if abs(croise[f][k] - ancien[f][k]) >= 1e-3}
    bil = json.loads((DONNEES / 'xt4-recettes-bilan-2026-10-29.json').read_text())
    for f in croise:
        croise[f]['existantes'] = {k: {'recette': x['recette'], 'sur_A': x['recherche'], 'sur_B': x['tenus_a_part']}
                                   for k, x in bil[f]['recettes'].items() if k != 'nouvelle'}
    (DONNEES / 'xt4-recettes-croise-2026-10-29.json').write_text(json.dumps(croise, indent=1, ensure_ascii=False))
    for f, c in croise.items():
        print(f, c['candidats'], 'A→B', c['choisi_sur_A']['recette'], c['choisi_sur_A']['sur_B'],
              '| B→A', c['choisi_sur_B']['recette'], c['choisi_sur_B']['sur_A'])


# ---------------------------------------------------------------------------------------------------------------
# 8. Bilan sur les 16 RAF, par RAF, tenus à part ; couleurs rendues en gris
# ---------------------------------------------------------------------------------------------------------------
NOMMEES = {'trix': ['LC Tri-X', 'NZD Tri-X', 'RR Tri-X Push Process'],
           'hp5': ['NZD Ilford HP-5', 'RR Ilford HP-5+', 'RR Ilford HP-5+ Push Process'],
           'fp4': [],
           'portra': ['NZD Portra 400', 'RS Kodak Portra 400', 'RR Kodak Porta 400', 'PS Kodak Portra 160', 'RR Kodak Portra 160']}
CATEGORIES = {'bleus (ciel, ombres)': lambda L, C, h: (h > 200) & (h < 290) & (C > 8) & (L > 40),
              'peau': lambda L, C, h: (h > 25) & (h < 70) & (C > 10) & (C < 40) & (L > 35) & (L < 85),
              'rouge': lambda L, C, h: ((h > 330) | (h < 30)) & (C > 30),
              'vert': lambda L, C, h: (h > 100) & (h < 180) & (C > 12),
              'jaune': lambda L, C, h: (h > 70) & (h < 100) & (C > 30)}


def par_categorie(R, film, rec, cib, sc, noms=None):
    """Écart signé de clarté (rendu − cible, L*) par famille de couleur de la scène (N&B : rendu des couleurs en gris)."""
    dm = _dm()
    d, t = [], []
    lab = []
    for n in (noms or list(R.blocs)):
        L = dm.code_lab(R.moyennes(n, rec) / 255)
        d.append(L[:, 0] - cib[film][n][:, 0])
        lab.append(sc[n])
    d, lab = np.concatenate(d), np.concatenate(lab)
    C = np.hypot(lab[:, 1], lab[:, 2])
    h = np.degrees(np.arctan2(lab[:, 2], lab[:, 1])) % 360
    out = {}
    for k, f in CATEGORIES.items():
        m = f(lab[:, 0], C, h)
        if m.sum() >= 20:
            out[k] = {'blocs': int(m.sum()), 'ecart_L': round(float(np.median(d[m])), 1)}
    return out


def par_tranche(R, film, rec, cib, noms=None):
    """Écart signé médian par tranche de clarté de la cible : L* (et, en couleur, chroma et ΔE)."""
    dm = _dm()
    Ls, Ts = [], []
    for n in (noms or list(R.blocs)):
        Ls.append(dm.code_lab(R.moyennes(n, rec) / 255))
        Ts.append(cib[film][n])
    L, T = np.concatenate(Ls), np.concatenate(Ts)
    out = []
    for a, b in ((0, 15), (15, 30), (30, 45), (45, 60), (60, 75), (75, 90), (90, 101)):
        m = (T[:, 0] >= a) & (T[:, 0] < b)
        if m.sum() < 20:
            continue
        x = {'tranche': f'{a}-{min(b, 100)}', 'blocs': int(m.sum()), 'dL': round(float(np.median(L[m, 0] - T[m, 0])), 1)}
        if film not in FILMS_NB:
            x['dC'] = round(float(np.median(np.hypot(L[m, 1], L[m, 2]) - np.hypot(T[m, 1], T[m, 2]))), 1)
            x['dE'] = round(float(np.median(dm.de2000(L[m], T[m]))), 2)
            x['da'] = round(float(np.median(L[m, 1] - T[m, 1])), 1)
            x['db'] = round(float(np.median(L[m, 2] - T[m, 2])), 1)
        out.append(x)
    return out


def bilan(banc_exe=None):
    et = json.loads((CHANTIER / 'etalonnage.json').read_text())
    cib, sc = cibles(et['y18'])
    best = json.loads((CHANTIER / 'meilleures.json').read_text())
    ex = json.loads((CHANTIER / 'existantes.json').read_text())
    nb, portra = presets_existants()
    par_nom = {r['nom']: r for r in nb + portra}
    R = Rendus(banc_exe)
    tous = list(R.blocs)
    tenus = [n for n in tous if n not in RECHERCHE]
    out = {}
    for f in ('trix', 'hp5', 'fp4', 'portra'):
        nouv = best[f]['recette']
        ext = [x['nom'] for x in ex[f] if x['nom'] in par_nom][:3]
        noms_ex = list(dict.fromkeys(NOMMEES[f] + ext))
        recs = {'nouvelle': nouv, **{k: pour_mesure(par_nom[k]) for k in noms_ex}}
        if f in FILMS_NB:
            recs['Acros neutre'] = dict(NEUTRE, sim=12)
        else:
            recs['Provia neutre'] = dict(NEUTRE)
        R.lot(list(recs.values()))
        lignes = {}
        for k, r in recs.items():
            e = ecarts(R, f, r, cib)
            lignes[k] = {'recette': recette_txt(r if k == 'nouvelle' or k.endswith('neutre') else par_nom[k]),
                         'tous': resume(e), 'tenus_a_part': resume({n: e[n] for n in tenus}),
                         'recherche': resume({n: e[n] for n in RECHERCHE}),
                         'par_raf': {n: round(float(np.median(v)), 2) for n, v in e.items()},
                         'tranches': par_tranche(R, f, r, cib)}
            if f in FILMS_NB:
                lignes[k]['categories'] = par_categorie(R, f, r, cib, sc)
                dm = _dm()
                lignes[k]['de2000'] = resume({n: dm.de2000(dm.code_lab(R.moyennes(n, r) / 255), cib[f][n]) for n in tous})
            journal(f"bilan {f} {k:32s} {lignes[k]['tous']} tenus à part {lignes[k]['tenus_a_part']}")
        out[f] = {'recettes': lignes, 'existantes_classees': [x for x in ex[f] if x['nom'] in par_nom][:8]}
    R.fermer()
    DONNEES.mkdir(parents=True, exist_ok=True)
    (DONNEES / 'xt4-recettes-bilan-2026-10-29.json').write_text(json.dumps(out, indent=1, ensure_ascii=False))
    return out


# ---------------------------------------------------------------------------------------------------------------
# 9. Grain : choisi à part (la mesure des couleurs se fait grain coupé)
# ---------------------------------------------------------------------------------------------------------------
GRAIN_RAF = ['157-DSCF9412', '051-DSCF8719', '163-DSCF9423']
APERTURE_UM = 48.0            # ouverture de la granularité RMS diffuse Kodak (cercle de 48 µm)
PIXEL_JPEG_UM = 36000 / 3120  # un pixel du JPEG S de la conversion (3120 de large), ramené à un négatif 24 × 36


def grain(banc_exe=None):
    """Bruit ajouté par chaque réglage de grain (rendu − rendu grain coupé), en L*, moyenné sur un cercle de 48 µm
    ramené au format 24 × 36 (4,2 px du JPEG S), sur les blocs uniformes de L* 35 à 65 ; comparé, pour la Tri-X, à sa
    granularité RMS diffuse (17, fiche Kodak) passée au tirage (pente dL*/dD du tirage grade 2 au gris moyen)."""
    import cv2
    dm = _dm()
    best = json.loads((CHANTIER / 'meilleures.json').read_text())
    dossier = CHANTIER / 'grain'
    dossier.mkdir(exist_ok=True)
    R = Rendus(banc_exe)
    r_ap = APERTURE_UM / 2 / PIXEL_JPEG_UM
    k = int(np.ceil(r_ap))
    yy, xx = np.mgrid[-k:k + 1, -k:k + 1]
    noyau = ((xx ** 2 + yy ** 2) <= r_ap ** 2).astype(np.float32)
    noyau /= noyau.sum()
    out = {'ouverture_px_M': round(2 * r_ap, 2), 'films': {}}
    for f in ('trix', 'hp5', 'fp4', 'portra'):
        recs = {g: dict(best[f]['recette'], grain=g) for g in GRAIN}
        R.lot(list(recs.values()), GRAIN_RAF, garder=dossier)
        res = {}
        for g, r in recs.items():
            s_pix, s_ap = [], []
            for n in GRAIN_RAF:
                a = dm.code_lab(jpeg(dossier / f'{n}-{cle(r)}.jpg') / 255.0)[..., 0]
                z = dm.code_lab(jpeg(dossier / f'{n}-{cle(recs[1])}.jpg') / 255.0)[..., 0]
                diff = (a - z).astype(np.float32)
                filt = cv2.filter2D(diff, -1, noyau)
                H, W = diff.shape[0] // B * B, diff.shape[1] // B * B
                idx = R.blocs[n]['idx']
                ref = z[:H, :W].reshape(H // B, B, W // B, B).mean((1, 3)).ravel()[idx]
                sel = idx[(ref > 35) & (ref < 65)]
                for arr, acc in ((diff, s_pix), (filt, s_ap)):
                    blocs = arr[:H, :W].reshape(H // B, B, W // B, B).transpose(0, 2, 1, 3).reshape(-1, B * B)[sel]
                    acc.append(blocs.std(1))
            res[g] = {'reglage': '/'.join(GRAIN[g]).lower(), 'sigma_L_pixel': round(float(np.median(np.concatenate(s_pix))), 2),
                      'sigma_L_48um': round(float(np.median(np.concatenate(s_ap))), 2)}
        out['films'][f] = res
    R.fermer()
    # Tri-X : granularité 17 → σ_D = 0,017 ; pente du tirage au gris moyen
    v = np.array([0.18 / 1.05, 0.18 * 1.05])
    g8, D = courbe_nb('trix_fiche', v, densite=True)
    L = dm.code_lab(np.repeat(g8[:, None], 3, 1))[:, 0]
    pente = abs((L[1] - L[0]) / (D[1] - D[0]))
    out['trix_cible'] = {'granularite_rms': 17, 'pente_dL_dD_tirage': round(float(pente), 1), 'sigma_L_48um': round(float(pente * 0.017), 2)}
    (CHANTIER / 'grain.json').write_text(json.dumps(out, indent=1, ensure_ascii=False))
    journal('grain ' + json.dumps(out, ensure_ascii=False))
    return out


def choisir_grain():
    """Tri-X : le réglage dont le bruit au cercle de 48 µm est le plus proche de la granularité 17 passée au tirage (calcul).
    HP5 Plus : même réglage (Ilford ne publie aucune granularité ; même classe de sensibilité : hypothèse).
    FP4 Plus : un cran de moins dans l'ordre mesuré, sans descendre sous « faible, petit » (ISO 125, pas de chiffre : hypothèse).
    Portra 400 : « faible, petit » (Print Grain Index 37 en 135 tiré en 10 × 15, seuil de visibilité 25, fiche E-4050 ;
    l'indice ne se convertit pas en granularité RMS : choix par rang, hypothèse)."""
    g = json.loads((CHANTIER / 'grain.json').read_text())
    cible = g['trix_cible']['sigma_L_48um']
    m = g['films']['trix']
    ordre = sorted((k for k in m if k != '1'), key=lambda k: m[k]['sigma_L_48um'])
    tx = min(ordre, key=lambda k: abs(m[k]['sigma_L_48um'] - cible))
    fp = ordre[max(ordre.index(tx) - 1, 0)]
    choix = {'trix': int(tx), 'hp5': int(tx), 'fp4': int(fp), 'portra': 2}
    (CHANTIER / 'grain-choix.json').write_text(json.dumps(choix))
    journal(f'grain choisi {choix} (cible Tri-X {cible} L* au cercle de 48 µm ; ordre mesuré {ordre})')
    return choix


# ---------------------------------------------------------------------------------------------------------------
# 10. Planches avant / après, colonnes nommées dans l'image
# ---------------------------------------------------------------------------------------------------------------
PLANCHE_RAF = {'trix': ['157-DSCF9412', '176-DSCF0476', '041-DSCF6283'], 'hp5': ['157-DSCF9412', '176-DSCF0476', '041-DSCF6283'],
               'fp4': ['157-DSCF9412', '176-DSCF0476', '041-DSCF6283'], 'portra': ['006-DSCF9213', '176-DSCF0476', '157-DSCF9412']}
TUILE = (640, 427)


def image_cible(n, film, y18, taille=TUILE):
    """Rendu cible d'une image entière, dans la géométrie du JPEG du boîtier (pour les planches)."""
    from scipy.ndimage import gaussian_filter, map_coordinates
    dm = _dm()
    d = dict(np.load(CHANTIER / 'blocs' / f'{n}.npz'))
    raf = next(r for r in rafs() if nom_raf(r) == n)
    lin, wb, rgb_cam = lineaire(raf)
    lin = lin * wb
    pas = 3120 / taille[0]
    lin = np.stack([gaussian_filter(lin[..., c], pas / 2.5) for c in range(3)], -1)
    p = d['geometrie']
    cj = np.array([3120, 2080]) / 2
    nrm = np.hypot(*cj)
    ys, xs = np.mgrid[0:taille[1], 0:taille[0]]
    q = np.c_[(xs.ravel() + 0.5) * pas, (ys.ravel() + 0.5) * pas]
    u = (q - cj) / nrm
    r2 = (u ** 2).sum(1, keepdims=True)
    u = u * (1 + p[4] * r2 + p[5] * r2 ** 2 + p[6] * r2 ** 3)
    c, s = np.cos(p[3]), np.sin(p[3])
    q = np.c_[c * u[:, 0] - s * u[:, 1], s * u[:, 0] + c * u[:, 1]] * p[2] * nrm + p[:2]
    v = np.stack([map_coordinates(lin[..., k], [q[:, 1], q[:, 0]], order=1, mode='nearest') for k in range(3)], -1)
    srgb = v @ rgb_cam.T * (0.18 / y18)
    if film in FILMS_NB:
        g = courbe_nb(FILMS_NB[film], np.clip(srgb @ poids_nb(film), 0, None))
        code = np.repeat(g[:, None], 3, 1)
    else:
        import d750_cibles as dc
        portra = dc.paires(RACINE / 'd750' / 'recherche' / 'donnees-films' / 'd750-seances' / 'portra-preset-regle.json')
        code = dm.lab_code(portra(srgb @ M709.T))
    return (np.clip(code, 0, 1) * 255 + 0.5).astype(np.uint8).reshape(taille[1], taille[0], 3)


def _police(t):
    from PIL import ImageFont
    for f in ('/System/Library/Fonts/Supplemental/Arial.ttf', '/System/Library/Fonts/Helvetica.ttc'):
        if os.path.exists(f):
            return ImageFont.truetype(f, t)
    return ImageFont.load_default()


def planches(banc_exe=None):
    from PIL import Image, ImageDraw
    et = json.loads((CHANTIER / 'etalonnage.json').read_text())
    bil = json.loads((DONNEES / 'xt4-recettes-bilan-2026-10-29.json').read_text())
    nb, portra = presets_existants()
    par_nom = {r['nom']: r for r in nb + portra}
    dossier = CHANTIER / 'planches'
    dossier.mkdir(exist_ok=True)
    FIGURES.mkdir(parents=True, exist_ok=True)
    R = Rendus(banc_exe)
    unite = {f: ('|ΔL*|' if f in FILMS_NB else 'ΔE2000') for f in NOMS_FILMS}
    for f, noms in PLANCHE_RAF.items():
        lig = bil[f]['recettes']
        existantes = [k for k in lig if k not in ('nouvelle', 'Acros neutre', 'Provia neutre')]
        # la meilleure des recettes existantes faites pour ce film (sinon la meilleure de toutes)
        nommees = [k for k in existantes if k in NOMMEES[f]] or existantes
        ex = min(nommees, key=lambda k: lig[k]['tous']['score'])
        rec_ex, rec_nv = pour_mesure(par_nom[ex]), lig['nouvelle']
        rec_nv = json.loads((CHANTIER / 'meilleures.json').read_text())[f]['recette']
        R.lot([rec_ex, rec_nv], noms, garder=dossier)
        W, H = TUILE
        marge, haut = 12, 74
        img = Image.new('RGB', (3 * W + 4 * marge, haut + len(noms) * (H + marge) + marge), 'white')
        dr = ImageDraw.Draw(img)
        p1, p2 = _police(22), _police(17)
        titres = [(f'CIBLE : {NOMS_FILMS[f]}', 'fiches Kodak / Ilford, tirage grade 2' if f in FILMS_NB else "profil Portra du preset acheté, tel que l'auteur le règle"),
                  (f'EXISTANTE : {ex}', f"{unite[f]} médian {lig[ex]['tous']['mediane']:.1f} (16 RAF)"),
                  ('NOUVELLE RECETTE X-T4', f"{unite[f]} médian {lig['nouvelle']['tous']['mediane']:.1f} (16 RAF)")]
        for k, (t1, t2) in enumerate(titres):
            x = marge + k * (W + marge)
            dr.text((x, 10), t1, fill='black', font=p1)
            dr.text((x, 40), t2, fill=(70, 70, 70), font=p2)
        for i, n in enumerate(noms):
            y = haut + i * (H + marge)
            tuiles = [Image.fromarray(image_cible(n, f, et['y18'])),
                      Image.open(dossier / f'{n}-{cle(rec_ex)}.jpg').convert('RGB').resize(TUILE, Image.LANCZOS),
                      Image.open(dossier / f'{n}-{cle(rec_nv)}.jpg').convert('RGB').resize(TUILE, Image.LANCZOS)]
            for k, t in enumerate(tuiles):
                x = marge + k * (W + marge)
                img.paste(t, (x, y))
                if k:
                    v = lig[ex if k == 1 else 'nouvelle']['par_raf'][n]
                    etiq = f'{n[:3]} : {unite[f]} {v:.1f}'
                else:
                    etiq = f'{n[:3]} : cible'
                tw = dr.textlength(etiq, font=p2)
                dr.rectangle((x + 6, y + H - 30, x + 14 + tw, y + H - 6), fill=(255, 255, 255))
                dr.text((x + 10, y + H - 28), etiq, fill='black', font=p2)
        sortie = FIGURES / f'xt4-planche-{f}-2026-10-29.jpg'
        img.save(sortie, quality=88)
        journal(f'planche {sortie.name}')
    R.fermer()


def tableaux():
    """Tableaux markdown du rapport, tirés du bilan (aucun chiffre recopié à la main)."""
    bil = json.loads((DONNEES / 'xt4-recettes-bilan-2026-10-29.json').read_text())
    fc = DONNEES / 'xt4-recettes-croise-2026-10-29.json'
    croise = json.loads(fc.read_text()) if fc.exists() else {}
    noms = list(next(iter(bil.values()))['recettes']['nouvelle']['par_raf'])
    out = []
    for f, b in bil.items():
        u = '|ΔL*|' if f in FILMS_NB else 'ΔE2000'
        out.append(f'\n#### {NOMS_FILMS[f]} : écart {u}, médiane (p90)\n')
        out.append('| Recette | Réglages | 16 RAF | moitié A (8 RAF de recherche) | moitié B (8 autres) |' + (' ΔE2000 (teinte comprise), 16 RAF |' if f in FILMS_NB else ''))
        out.append('|---|---|---|---|---|' + ('---|' if f in FILMS_NB else ''))
        lig = b['recettes']
        ordre = ['nouvelle'] + sorted((k for k in lig if k != 'nouvelle'), key=lambda k: lig[k]['tous']['score'])
        for k in ordre:
            x = lig[k]
            c = lambda r: f"{r['mediane']:.2f} ({r['p90']:.1f})".replace('.', ',')
            nom = '**Nouvelle recette**' if k == 'nouvelle' else k
            ligne = f"| {nom} | {x['recette']} | {c(x['tous'])} | {c(x['recherche'])} | {c(x['tenus_a_part'])} |"
            if f in FILMS_NB:
                ligne += f" {c(x['de2000'])} |"
            out.append(ligne)
            if k == 'nouvelle' and f in croise:
                xa, xb = croise[f]['choisi_sur_B'], croise[f]['choisi_sur_A']
                out.append(f"| *choisie sur B, mesurée sur A* | {xa['recette']} | | **{c(xa['sur_A'])}** | *{c(xa['sur_B'])}* |" + (' |' if f in FILMS_NB else ''))
                out.append(f"| *choisie sur A, mesurée sur B* | {xb['recette']} | | *{c(xb['sur_A'])}* | **{c(xb['sur_B'])}** |" + (' |' if f in FILMS_NB else ''))
        ex = [k for k in ordre if k not in ('nouvelle', 'Acros neutre', 'Provia neutre')]
        meilleure = ex[0]
        out.append(f'\nPar RAF (médiane {u}) : nouvelle recette contre {meilleure}\n')
        out.append('| ' + ' | '.join(n[:3] for n in noms) + ' |')
        out.append('|' + '---|' * len(noms))
        out.append('| ' + ' | '.join(f"{lig['nouvelle']['par_raf'][n]:.1f}".replace('.', ',') for n in noms) + ' |')
        out.append('| ' + ' | '.join(f"{lig[meilleure]['par_raf'][n]:.1f}".replace('.', ',') for n in noms) + ' |')
        if f in FILMS_NB:
            out.append('\nCouleurs rendues en gris (écart signé médian de L*, rendu − cible ; + = trop clair)\n')
            cats = list(lig['nouvelle']['categories'])
            out.append('| Recette | ' + ' | '.join(f"{c} ({lig['nouvelle']['categories'][c]['blocs']} blocs)" for c in cats) + ' |')
            out.append('|---|' + '---|' * len(cats))
            for k in ['nouvelle', meilleure, 'Acros neutre']:
                out.append(f"| {k} | " + ' | '.join(f"{lig[k]['categories'].get(c, {}).get('ecart_L', float('nan')):+.1f}".replace('.', ',') for c in cats) + ' |')
        out.append('\nPar tranche de clarté de la cible (écart signé médian ' + ('de L*' if f in FILMS_NB else 'de L*, de chroma C*, ΔE2000') + ')\n')
        tr = lig['nouvelle']['tranches']
        out.append('| Recette | ' + ' | '.join(f"L* {t['tranche']}" for t in tr) + ' |')
        out.append('|---|' + '---|' * len(tr))
        for k in ['nouvelle', meilleure]:
            d = {t['tranche']: t for t in lig[k]['tranches']}
            if f in FILMS_NB:
                cel = [f"{d[t['tranche']]['dL']:+.1f}" if t['tranche'] in d else '' for t in tr]
            else:
                cel = [f"L {d[t['tranche']]['dL']:+.1f}, C {d[t['tranche']]['dC']:+.1f}, ΔE {d[t['tranche']]['dE']:.1f}" if t['tranche'] in d else '' for t in tr]
            out.append(f'| {k} | ' + ' | '.join(c.replace('.', ',') for c in cel) + ' |')
    print('\n'.join(out))


# ---------------------------------------------------------------------------------------------------------------
# 11. Livraison des .FP1, contrôles, ligne de commande
# ---------------------------------------------------------------------------------------------------------------
def livrer():
    """Écrit un .FP1 par film dans presets/recettes-2026/ (recette mesurée + grain choisi à part, grain.json)."""
    best = json.loads((CHANTIER / 'meilleures.json').read_text())
    choix = json.loads((CHANTIER / 'grain-choix.json').read_text())
    RECETTES.mkdir(parents=True, exist_ok=True)
    for f, nom in (('trix', 'XT4 Tri-X 400 mesure'), ('hp5', 'XT4 HP5 Plus mesure'), ('fp4', 'XT4 FP4 Plus mesure'), ('portra', 'XT4 Portra 400 mesure')):
        # netteté 0 et réduction du bruit −4 : choix (les blocs uniformes ne les mesurent pas), contrôlés par controle_livrees
        r = dict(best[f]['recette'], grain=choix[f], wb=WB['Auto'], dr=100, nettete=0, bruit=-4)
        ecrire_fp1(r, RECETTES / f'{nom}.FP1', nom)
        relu = lire_fp1(RECETTES / f'{nom}.FP1')
        for k in ('sim', 'h', 's', 'wb_r', 'wb_b', 'grain', 'cc', 'ccb', 'clarte', 'nettete', 'bruit'):
            assert float(relu.get(k, 0)) == float(r.get(k, 0)), (f, k, relu.get(k), r.get(k))
        print(RECETTES / f'{nom}.FP1', recette_txt(r))


def controle_livrees(banc_exe=None):
    """Les quatre .FP1 livrés, relus et rendus tels quels sur les 16 RAF (balance de prise de vue), avec et sans leur grain."""
    et = json.loads((CHANTIER / 'etalonnage.json').read_text())
    cib, _ = cibles(et['y18'])
    R = Rendus(banc_exe)
    out = {}
    for f, nom in (('trix', 'XT4 Tri-X 400 mesure'), ('hp5', 'XT4 HP5 Plus mesure'), ('fp4', 'XT4 FP4 Plus mesure'), ('portra', 'XT4 Portra 400 mesure')):
        r = lire_fp1(RECETTES / f'{nom}.FP1')
        m = {k: v for k, v in r.items() if k not in ('nom', 'source', 'kelvin')}
        m.update(wb=0)
        sans = dict(m, grain=1)
        R.lot([m, sans])
        out[f] = {'recette': recette_txt(r), 'grain': '/'.join(GRAIN[r['grain']]).lower(),
                  'avec_grain': resume(ecarts(R, f, m, cib)), 'grain_coupe': resume(ecarts(R, f, sans, cib))}
        journal(f"livrée {f} {out[f]}")
    R.fermer()
    (DONNEES / 'xt4-recettes-livrees-2026-10-29.json').write_text(json.dumps(out, indent=1, ensure_ascii=False))


def self_test():
    base = bytes(509) + b''.join(int(v).to_bytes(4, 'little', signed=True) for v in [0, 2, 7, 7, 2, 0, 100, 0, 11, 1, 1, 1, 0, 0, 0, 0,
                                                                                     -10, 5, 20, 10, 4096, 1, 1, 0, 1, 1, 0, 0])
    base = (28).to_bytes(2, 'little') + base[2:]
    r = dict(NEUTRE, sim=12, h=1.5, s=-2, bruit=-4, mono_wc=2, mono_mg=-1)
    _, p = d185_params(profil(base, r))
    assert p[8] == 12 and p[16] == 15 and p[17] == -20 and p[20] == 0x8000 and p[23] == 20 and p[26] == -10 and p[12] == 0
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        r2 = dict(NEUTRE, sim=17, h=-1.5, s=2, couleur=3, wb=WB['Auto'], wb_r=2, wb_b=-4, cc=2, ccb=3, grain=2, clarte=-1, bruit=-4)
        ecrire_fp1(r2, pathlib.Path(d) / 't.FP1', 'essai')
        lu = lire_fp1(pathlib.Path(d) / 't.FP1')
        for k in ('sim', 'h', 's', 'couleur', 'wb', 'wb_r', 'wb_b', 'cc', 'ccb', 'grain', 'clarte', 'bruit'):
            assert float(lu[k]) == float(r2[k]), (k, lu[k], r2[k])
    for f in FILMS_NB.values():
        assert abs(courbe_nb(f, np.array([0.18]))[0] * 255 - 118) < 0.01
    print('self-test OK')


if __name__ == '__main__':
    a = sys.argv[1:]
    if not a or a[0] in ('-h', '--help'):
        print(__doc__)
        sys.exit(2)
    if a[0] == '--self-test':
        self_test()
    elif a[0] == 'chercher':
        chercher(quoi=a[1] if len(a) > 1 else 'nb')
    else:
        globals()[a[0]]()
