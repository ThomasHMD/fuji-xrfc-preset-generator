#!/usr/bin/env python3
# SPDX-License-Identifier: CC-BY-NC-4.0
# Copyright (c) 2026 Thomas Hammoudi
"""Pré-tri des propositions de la recherche v2 par transfert : moins de conversions au boîtier pour la même décision.

Constat (29/10/2026, cache de la passe 2, sans le boîtier) : le rendu d'une recette se déduit du rendu Provia neutre du
même bloc (blocs[n]['jpg_ref']), d'un RAF à l'autre. Prédit depuis les 15 autres RAF, l'écart médian est de 0,1 à 0,3 ΔE
en N&B, de 0,6 à 0,9 en couleur ; il monte vers 3 quand la recette sort ce que le neutre a écrêté. Depuis le seul brut
(sRGB linéaire des blocs), il reste à 0,7 à 2 ΔE : le neutre porte ce que chaque RAF a de propre (objectif, balance).

Méthode, pour chaque recherche (look, moitié) et chaque proposition :
1. la proposition est rendue sur K RAF « support » de l'ensemble noté, choisis pour couvrir au mieux les rendus neutres des
   autres (glouton) ;
2. sur les autres RAF, rendu prédit = rendu de la recette courante (déjà connu partout) + écart proposition − courante
   appris sur le support, aux plus proches voisins dans le Lab du rendu neutre ;
3. les TOP meilleures propositions prédites, si elles sont à moins de MARGE de la note courante, sont rendues partout et
   notées en vrai ; la décision (même règle que xt4_recherche_v2.evaluer) ne lit que des notes réelles.

Une proposition déjà rendue partout (exposition seule, cache) est notée en vrai sans rien rendre.

Mesuré sur le cache, sans le boîtier (29/10/2026) :
- notes prédites (K = 3) contre réelles, paires de recettes à un paramètre d'écart : erreur médiane 0,05 à 0,11 en N&B,
  0,05 à 0,07 en couleur (Portra, Classic Chrome, CC × 1,3) ; décision « meilleure ou non » juste à 96 à 99 % ;
- 300 étapes de descente simulées (K = 3, MARGE = 0,15, TOP = 2) : étape moins bonne que la descente complète dans 3 % des
  cas, perte moyenne 0,004 au critère (max 0,5), rattrapable au tour suivant ;
- 5 étapes réelles rejouées depuis etat-nb.json, cache masqué (h, s, wb_r, wb_b, sim ; 9 recherches) : 855 rendus au lieu
  de 5 982 (14 %), décisions identiques à la descente complète dans les 45 cas.

  python3 xt4_transfert.py --self-test     contrôles sans boîtier (support, prédiction exacte quand tout est rendu)
  XT4_TRANSFERT=0                          dans xt4_recherche_v2 : revenir à la descente complète
"""
import os
from collections import defaultdict

import numpy as np
from scipy.spatial import cKDTree

K = int(os.environ.get('XT4_TRANSFERT_K', '3'))
MARGE = float(os.environ.get('XT4_TRANSFERT_MARGE', '0.15'))
TOP = int(os.environ.get('XT4_TRANSFERT_TOP', '2'))
VOISINS = 6
_SUP, _REF = {}, {}
STATS = {'propositions': 0, 'sans_rendu': 0, 'verifiees': 0}


def ref(v2, n):
    """Lab du rendu Provia neutre des blocs du RAF n."""
    if n not in _REF:
        _REF[n] = v2.dm.code_lab(v2.charger_blocs_v2()[n]['jpg_ref'] / 255)
    return _REF[n]


def support(v2, noms, k=None):
    """k RAF de noms qui couvrent le mieux les rendus neutres des autres : chaque ajout minimise la moyenne, sur les RAF
    restants, de la distance médiane d'un bloc à son plus proche voisin du support."""
    k = K if k is None else k
    cle = (tuple(noms), k)
    if cle not in _SUP:
        S = []
        for _ in range(min(k, len(noms))):
            best = None
            for n in noms:
                if n in S:
                    continue
                t = cKDTree(np.vstack([ref(v2, m) for m in S + [n]]))
                reste = [m for m in noms if m not in S + [n]]
                d = float(np.mean([np.median(t.query(ref(v2, m))[0]) for m in reste])) if reste else 0.0
                if best is None or d < best[0]:
                    best = (d, n)
            S.append(best[1])
        _SUP[cle] = S
    return _SUP[cle]


def predire(v2, R, o, r, S):
    """Lab de la recette r sur les RAF de la recherche o : rendu réel là où il existe, prédit ailleurs."""
    cur = o['rec']
    t = cKDTree(np.vstack([ref(v2, n) for n in S]))
    V = np.vstack([v2.lab(R, n, r) - v2.lab(R, n, cur) for n in S])
    out = {}
    for n in o['noms']:
        if R.chemin(n, r).exists():
            out[n] = v2.lab(R, n, r)
            continue
        dd, ii = t.query(ref(v2, n), k=VOISINS)
        w = 1 / (dd + 0.5)
        w /= w.sum(1, keepdims=True)
        out[n] = v2.lab(R, n, cur) + (V[ii] * w[..., None]).sum(1)
    return out


def note_lab(v2, L, look, e3, noms):
    e = {n: np.abs(L[n][:, 0] - v2.CIB[look][e3][n][:, 0]) if look in v2.NB else v2.dm.de2000(L[n], v2.CIB[look][e3][n])
         for n in noms}
    return v2.xm.resume(e)['score']


def evaluer(v2, R, objs, props, seuil=1e-3):
    """Remplace xt4_recherche_v2.evaluer : même décision, sur notes réelles, avec moins de rendus."""
    complet = lambda r, noms: all(R.chemin(n, r).exists() for n in noms)  # noqa: E731
    besoin = defaultdict(dict)
    for o in objs:
        S = support(v2, o['noms'])
        for r, _ in props.get(o['id'], []):
            if not complet(r, o['noms']):
                for n in S:
                    besoin[n][v2.xm.cle(r)] = r
    R.lot_par_raf({n: list(d.values()) for n, d in besoin.items()})
    retenues, besoin = {}, defaultdict(dict)
    for o in objs:
        pl = props.get(o['id'], [])
        if not pl:
            continue
        S = support(v2, o['noms'])
        reelles, pred = [], []
        for r, e3 in pl:
            STATS['propositions'] += 1
            if complet(r, o['noms']):
                STATS['sans_rendu'] += 1
                reelles.append((r, e3))
            else:
                pred.append((note_lab(v2, predire(v2, R, o, r, S), o['look'], e3, o['noms']), r, e3))
        garde = [(r, e3) for s, r, e3 in sorted(pred, key=lambda x: x[0]) if s < o['s'] + MARGE][:TOP]
        STATS['verifiees'] += len(garde)
        retenues[o['id']] = reelles + garde
        for r, _ in garde:
            for n in o['noms']:
                besoin[n][v2.xm.cle(r)] = r
    R.lot_par_raf({n: list(d.values()) for n, d in besoin.items()})
    for o in objs:
        for r, e3 in retenues.get(o['id'], []):
            s = v2.note(R, o['look'], e3, r, o['noms'])['score']
            sl = max(seuil, v2.SEUIL_EXPO) if e3 != o['e3'] and o['look'] != 'hp5' else seuil
            if s < o['s'] - sl:
                o.update(rec=r, e3=e3, s=s, bouge=True)


def self_test():
    """Sans boîtier : support stable et dans l'ensemble ; prédiction égale au réel quand la proposition est rendue partout ;
    evaluer ne demande aucun rendu quand tout est au cache."""
    import json
    import xt4_recherche_v2 as v2
    v2.cibles()
    objs = json.loads((v2.V2 / 'etat-nb.json').read_text())
    for o in objs:
        S = support(v2, o['noms'])
        assert len(S) == min(K, len(o['noms'])) and set(S) <= set(o['noms']) and S == support(v2, o['noms']), o['id']

    class SansBanc(v2.RendusV2):
        def lot_par_raf(self, besoin):
            manque = [(n, v2.xm.cle(r)) for n, rs in besoin.items() for r in rs if not self.chemin(n, r).exists()]
            assert not manque, f'rendu demandé : {manque[:3]}'

    R = SansBanc()
    o = next(o for o in objs if complet_partout(R, o['rec'], o['noms']))
    L = predire(v2, R, o, o['rec'], support(v2, o['noms']))
    assert abs(note_lab(v2, L, o['look'], o['e3'], o['noms']) - o['s']) < 1e-6, 'prédiction ≠ réel sur une recette rendue'
    copie = [dict(x) for x in objs]
    evaluer(v2, R, copie, {x['id']: [(x['rec'], e) for e in v2.E3 if e != x['e3']] for x in copie if x['look'] == 'hp5'})
    print(f'self-test xt4_transfert : ok (K={K}, MARGE={MARGE}, TOP={TOP}) ; supports : '
          + ' ; '.join(f"{o['id']} {support(v2, o['noms'])}" for o in objs[:3]))


def complet_partout(R, r, noms):
    return all(R.chemin(n, r).exists() for n in noms)


if __name__ == '__main__':
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    if '--self-test' in sys.argv:
        self_test()
    else:
        print(__doc__)
