#!/usr/bin/env python3
# SPDX-License-Identifier: CC-BY-NC-4.0
# Copyright (c) 2026 Thomas Hammoudi
"""Effet mesuré de chaque réglage du X-T4, sans le boîtier : paires de recettes à un seul paramètre d'écart, prises dans le
cache des rendus (moyennes de blocs des 16 RAF de la recherche). Sert la doc « Le traitement des couleurs du X-T4,
réglage par réglage » (docs/traitement-couleur-x-t4.md).

  python3 xt4_effets.py cles            retrouve la recette derrière chaque clé du cache (JSON du chantier, grille N&B, voisins)
  python3 xt4_effets.py analyse         → donnees/xt4-effets-reglages-<DATE>.json (médianes par tranche, chroma, famille)

Les clés du cache sont des empreintes (xt4_mesure.cle) : la recette se retrouve en la recalculant. Familles de teinte et
tranches de clarté lues sur le Provia neutre de chaque bloc.

Variables : XT4_CHANTIER (dossier lourd : cache des rendus, JSON de la recherche ; par défaut <dossier temporaire>/xt4-mesure),
XT4_RIB (clone du dépôt retro-ingenierie-boitiers).
"""
import itertools
import json
import pickle
import sys
from collections import defaultdict

import numpy as np

import xt4_recherche_v2 as v

xm, dm = v.xm, v.dm
CACHE = xm.CHANTIER / 'cache'
CLES = xm.CHANTIER / 'effets-cles.pkl'
SORTIE = xm.DONNEES / f'xt4-effets-reglages-{v.DATE}.json'
BL = [0, 15, 30, 45, 60, 75, 90, 101]
BC = [0, 10, 25, 40, 60, 200]
FAM = [('rouges', 345, 35), ('oranges', 35, 70), ('jaunes', 70, 105), ('verts', 105, 170), ('cyans', 170, 230),
       ('bleus', 230, 300), ('magentas', 300, 345)]
PARAMS = ['sim', 'h', 's', 'couleur', 'wb_r', 'wb_b', 'cc', 'ccb', 'clarte', 'dr']


def _nv(x):
    return int(x) if float(x).is_integer() else x


def cles():
    """Recettes du cache : celles des JSON du chantier, la grille N&B de la recherche, puis leurs voisins (1 ou 2 paramètres)
    tant qu'il s'en trouve."""
    cache = {f.stem for d in CACHE.iterdir() if d.is_dir() for f in d.glob('*.npy') if not f.name.endswith('.part.npy')}
    connus = {}

    def walk(o):
        if isinstance(o, dict):
            if isinstance(o.get('sim'), (int, float)):
                try:
                    k = xm.cle(o)
                    if k in cache:
                        connus[k] = {a: b for a, b in o.items() if a not in ('nom', 'source')}
                except TypeError:
                    pass
            for x in o.values():
                walk(x)
        elif isinstance(o, list):
            for x in o:
                walk(x)
    for f in xm.CHANTIER.rglob('*.json'):
        try:
            walk(json.loads(f.read_text()))
        except (ValueError, OSError):
            pass
    T, D = [_nv(x / 2) for x in range(-4, 9)], list(range(-9, 10))
    for sim, cc, k in itertools.product([12, 13, 14, 15, 6, 7, 8, 9], [1, 2, 3], v.KELVINS):
        for h, s, r_, b_ in itertools.product(T, T, D, D):
            r = {'sim': sim, 'dr': 100, 'drp': 0, 'grain': 1, 'cc': cc, 'ccb': 1, 'wb': xm.WB['Temperature'] if k else 0,
                 'wb_r': r_, 'wb_b': b_, 'h': h, 's': s, 'couleur': 0, 'nettete': 0, 'bruit': 0, 'clarte': 0}
            if k:
                r['kelvin'] = k
            c = xm.cle(r)
            if c in cache:
                connus[c] = r
    dom = {'sim': [17, 5, 4, 3, 1, 11, 16, 2, 18, 10, 12, 13, 14, 15, 6, 7, 8, 9], 'h': T, 's': T, 'couleur': list(range(-4, 5)),
           'wb_r': D, 'wb_b': D, 'cc': [1, 2, 3], 'ccb': [1, 2, 3], 'clarte': [0, -2, 2, 4], 'dr': [100, 200, 400]}
    front = list(connus.values())
    while front:
        nouv = []
        for r in front:
            for p, vals in dom.items():
                if p in r:
                    for x in vals:
                        q = dict(r, **{p: x})
                        c = xm.cle(q)
                        if x != r[p] and c in cache and c not in connus:
                            connus[c] = q
                            nouv.append(q)
            for a, b in (('h', 's'), ('wb_r', 'wb_b')):
                if a in r and b in r:
                    for da, db in itertools.product((-1, -.5, .5, 1), repeat=2):
                        q = dict(r, **{a: _nv(r[a] + da), b: _nv(r[b] + db)})
                        c = xm.cle(q)
                        if c in cache and c not in connus:
                            connus[c] = q
                            nouv.append(q)
        front = nouv
    CLES.write_bytes(pickle.dumps(connus))
    print(f'{len(connus)} recettes identifiées sur {len(cache)} clés')


def analyse(cles_pkl=None):
    K = pickle.loads((cles_pkl or CLES).read_bytes())
    B = v.charger_blocs_v2()
    v.cibles()
    ref = {n: dm.code_lab(B[n]['jpg_ref'] / 255) for n in B}
    memo = {}

    def lab(n, k):
        if (n, k) not in memo:
            p = CACHE / n / f'{k}.npy'
            memo[(n, k)] = dm.code_lab(np.load(p) / 255) if p.exists() else None
        return memo[(n, k)]

    def lch(L):
        return np.hypot(L[:, 1], L[:, 2]), np.degrees(np.arctan2(L[:, 2], L[:, 1])) % 360

    def fam(h, c):
        out = {nom: (((h >= a) | (h < b)) if a > b else ((h >= a) & (h < b))) & (c > 12) for nom, a, b in FAM}
        out['neutres'] = c < 6
        return out

    def med(x):
        return round(float(np.median(x)), 2) if len(x) > 20 else None
    groupes = {}
    for p in PARAMS:
        g = defaultdict(dict)
        for k, r in K.items():
            g[tuple(sorted((a, b) for a, b in r.items() if a != p))][r.get(p)] = (k, r)
        groupes[p] = g

    def paires(p, a, b, f):
        D, R0, A = [], [], []
        for d in groupes[p].values():
            if a in d and b in d and f(d[a][1]):
                for n in B:
                    La, Lb = lab(n, d[a][0]), lab(n, d[b][0])
                    if La is not None and Lb is not None:
                        D.append(Lb - La)
                        R0.append(ref[n])
                        A.append(La)
        return (np.vstack(D), np.vstack(R0), np.vstack(A), len(D)) if D else None

    def resume(p, a, b, f=lambda r: True):
        x = paires(p, a, b, f)
        if x is None:
            return None
        D, R0, A, npaires = x
        cR, hR = lch(R0)
        cA, hA = lch(A)
        cB, hB = lch(A + D)
        dC, dh = cB - cA, (hB - hA + 180) % 360 - 180
        out = {'n_rendus_paires': npaires,
               'dL_tranche': {f'{BL[i]}-{BL[i+1]}': med(D[(R0[:, 0] >= BL[i]) & (R0[:, 0] < BL[i + 1]), 0]) for i in range(len(BL) - 1)},
               'dC_chroma': {f'{lo}-{hi}': med(dC[(cA >= lo) & (cA < hi)]) for lo, hi in zip(BC[:-1], BC[1:])},
               'ratioC_chroma': {f'{lo}-{hi}': med((cB / np.maximum(cA, .1))[(cA >= lo) & (cA < hi)]) if lo >= 10 else None
                                 for lo, hi in zip(BC[:-1], BC[1:])},
               'famille': {nom: {'dL': med(D[m, 0]), 'dC': med(dC[m]), 'dh': med(dh[m & (cA > 12)]), 'da': med(D[m, 1]),
                                 'db': med(D[m, 2])} for nom, m in fam(hR, cR).items()},
               'global': {'dL': med(D[:, 0]), 'dC': med(dC), 'dE00_med': round(float(np.median(dm.de2000(A, A + D))), 2)}}
        sat = cR >= 25
        out['dL_tranche_satures'] = {f'{BL[i]}-{BL[i+1]}': med(D[sat & (R0[:, 0] >= BL[i]) & (R0[:, 0] < BL[i + 1]), 0])
                                     for i in range(len(BL) - 1)}
        bl = (hR >= 230) & (hR < 300) & (cR > 12)
        out['bleus_dL_chroma'] = {f'{lo}-{hi}': med(D[bl & (cR >= lo) & (cR < hi), 0]) for lo, hi in zip(BC[:-1], BC[1:])}
        return out
    coul, mono = (lambda r: r['sim'] not in xm.SIMS_MONO), (lambda r: r['sim'] in xm.SIMS_MONO)
    res = {}
    for p, trans in [('h', [(0, x) for x in (-2, -1, 1, 2, 3, 4)]), ('s', [(0, x) for x in (-2, -1, 1, 2, 3, 4)]),
                     ('couleur', [(0, x) for x in (-4, -2, 2, 4)]), ('cc', [(1, 2), (1, 3)]), ('ccb', [(1, 2), (1, 3)]),
                     ('wb_r', [(0, x) for x in (-9, -6, -3, 3, 6, 9)]), ('wb_b', [(0, x) for x in (-9, -6, -3, 3, 6, 9)]),
                     ('clarte', [(0, x) for x in (-2, 2, 4)]), ('dr', [(100, 200), (100, 400)])]:
        for a, b in trans:
            for nomf, f in (('couleur', coul), ('mono', mono)):
                r = resume(p, a, b, f)
                if r:
                    res[f'{p} {a}->{b} [{nomf}]'] = r
    for s in [2, 3, 4, 5, 11, 16, 17, 18, 10]:
        r = resume('sim', 1, s)
        if r:
            res[f'sim Provia->{xm.SIMS[s]}'] = r
    for a, b in [(12, 13), (12, 14), (12, 15), (6, 7), (6, 8), (6, 9), (6, 12)]:
        r = resume('sim', a, b)
        if r:
            res[f'sim {xm.SIMS[a]}->{xm.SIMS[b]}'] = r
    # courbes de base (recettes « pures » : tout à 0 sauf la simulation) et mélange N&B contre la clarté de la scène
    neutre = {'h': 0, 's': 0, 'couleur': 0, 'wb_r': 0, 'wb_b': 0, 'cc': 1, 'ccb': 1, 'clarte': 0, 'dr': 100, 'drp': 0, 'wb': 0}
    purs = {}
    for k, r in K.items():
        if all(r.get(p, x) == x for p, x in neutre.items()) and r.get('nettete', 0) == 0 and r.get('bruit', 0) == 0:
            purs.setdefault(xm.SIMS[r['sim']], k)
    comp = {}
    for nom, k in purs.items():
        Ls, Lr, mel, sig = [], [], defaultdict(list), defaultdict(list)
        for n in B:
            L = lab(n, k)
            if L is None:
                continue
            S = v.SC[n]
            Y = (S[:, 0] + 16) / 116
            Y = np.where(Y > 6 / 29, Y ** 3, (Y - 4 / 29) * 3 * (6 / 29) ** 2)
            Ls.append(np.log2(np.maximum(Y, 1e-6) / 0.18))
            Lr.append(L[:, 0])
            c, h = lch(S)
            m = (S[:, 0] > 40) & (S[:, 0] < 70)
            cL, hL = lch(L)
            for f, mf in fam(h, c).items():
                mel[f].append(L[m & mf, 0] - S[m & mf, 0])
                if f != 'neutres':        # signature couleur : chroma rendu / chroma de la scène, glissement de teinte
                    sig[f].append(np.c_[cL[mf] / np.maximum(c[mf], .1), (hL[mf] - h[mf] + 180) % 360 - 180])
        Ls, Lr = np.concatenate(Ls), np.concatenate(Lr)
        comp[f'courbe {nom} (IL scène -> L* rendu)'] = {f'{e:+d}': med(Lr[(Ls >= e - .5) & (Ls < e + .5)]) for e in range(-2, 4)}
        if sig and nom not in [xm.SIMS[s] for s in xm.SIMS_MONO] + [xm.SIMS[10]]:
            comp[f'{nom} : chroma rendu / scène et teinte rendu − scène, par famille de la scène'] = {
                f: [med(np.concatenate(x)[:, 0]), med(np.concatenate(x)[:, 1])] for f, x in sig.items()}
        if nom in (xm.SIMS[12], xm.SIMS[6]):
            comp[f'{nom} : L* rendu − L* scène (scène L* 40-70) par famille'] = {f: med(np.concatenate(x)) for f, x in mel.items()}
    SORTIE.write_text(json.dumps({'date': v.DATE, 'methode': __doc__.strip().splitlines()[0], 'n_recettes': len(K),
                                  'effets': res, 'complements': comp}, ensure_ascii=False, indent=1))
    print(f'{SORTIE.name} : {len(res)} transitions, {len(comp)} compléments')


if __name__ == '__main__':
    a = sys.argv[1:]
    if a[:1] == ['cles']:
        cles()
    elif a[:1] == ['analyse']:
        analyse(next((__import__('pathlib').Path(x.split('=', 1)[1]) for x in a if x.startswith('--cles=')), None))
    else:
        print(__doc__)
        sys.exit(2)
