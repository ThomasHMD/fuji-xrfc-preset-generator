#!/usr/bin/env python3
# SPDX-License-Identifier: CC-BY-NC-4.0
# Copyright (c) 2026 Thomas Hammoudi
"""Validation de la deuxième passe X-T4 (29/10/2026) : contrôle du banc, plage dynamique, lot varié hors échantillon.
Voir le README du dépôt (La méthode en clair, Rejouer la mesure). Un seul banc à la fois : jamais en même temps que
xt4_recherche_v2 (processus séparés, l'un après l'autre).

  xt4_validation.py preparer      liens des RAF de validation et de la séance du 29/10, référence et blocs (xt4_mesure.preparer)
  xt4_validation.py banc          chaque RAF de la séance développé avec ses propres réglages, contre le JPEG du déclenchement
  xt4_validation.py dr            DR100 / 200 / 400 pour chaque recette retenue → donnees/xt4-dr-2026-10-29.json, v2/dr-choix.json
  xt4_validation.py dr_retenues   la même comparaison pour les quatre recettes retenues absentes de dr → donnees/xt4-dr-retenues-2026-10-29.json
  xt4_validation.py familles      d'où viennent les écarts du lot varié, par famille de couleur (sans boîtier)
  xt4_validation.py validation    recettes figées et meilleures recettes de 2022 sur le lot varié (201 à 224, RAF d'au moins MIN_BLOCS blocs : 20 sur 24)

Chantier : XT4_CHANTIER/validation (raf/ : liens, base/, reference/, blocs/, cache/ : moyennes de toute la grille de
blocs de chaque rendu, controle/ : JPEG du contrôle du banc).
"""
import concurrent.futures as cf
import json
import math
import pathlib
import sys
import time

import numpy as np

ICI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))
import xt4_recherche_v2 as v  # noqa: E402  (importé d'abord : il fixe la scène et ses chemins sur le chantier principal)

xm, xs, xc, dm = v.xm, v.xs, v.xc, v.dm
PRINCIPAL = xm.CHANTIER
VAL = PRINCIPAL / 'validation'
SOURCE = PRINCIPAL.parent / 'xt4-validation'
CAPTURE = SOURCE / 'capture-2026-10-29'
Y18 = json.loads((PRINCIPAL / 'etalonnage.json').read_text())['y18']
DATE = v.DATE
SORTIE_BANC = xm.DONNEES / f'xt4-controle-banc-{DATE}.json'
SORTIE_DR = xm.DONNEES / f'xt4-dr-{DATE}.json'
SORTIE_VAL = xm.DONNEES / f'xt4-validation-24raf-{DATE}.json'
VARIE = [f'{i}' for i in range(201, 225)]
DR_SEULS = ['301', '302', '305', '309', '321', '322', '323', '324']    # pris en DR200 (et 324 en DR400) : le plus de hautes lumières
SCENES = {'dr': 'guitares', 'fenetre': 'fenetre', 'scene3': 'scene3'}
DH = (-1, 0, 1)            # hautes lumières reprises autour de la recette, à chaque DR
MIN_BLOCS = 50             # lot varié : un RAF presque sans blocs uniformes (scène très texturée) pèserait autant qu'un RAF de
                           # 1 000 blocs ; 202, 204, 205, 223 en ont 0 à 5, les autres au moins 303 (seuil fixé le 30/10/2026 à 02:20,
                           # avant tout résultat du lot varié : la première exécution s'est arrêtée sur le RAF 204, sans aucun bloc)
SEUIL_DR = 0.3            # gain net : au moins 0,3 au critère en moyenne sur les scènes, et sur au moins deux scènes sur trois


def journal(msg):
    v.journal('validation : ' + msg)


# ---------------------------------------------------------------------------------------------------------------
# RAF : liens, DR de la prise de vue, préparation
# ---------------------------------------------------------------------------------------------------------------
def inventaire():
    """{nom: (source, DR de la prise de vue, lot)} ; noms : « c-<scène>-DR<n> » pour la séance, « 2xx-DSCF… » sinon."""
    out = {}
    for d, sc in SCENES.items():
        for p in sorted((CAPTURE / d).glob('*.raf')):
            dr = int(p.stem.split('-DR')[1][:3])
            out[f'c-{sc}-DR{dr}'] = (p, dr, 'séance')
    lignes = (xm.DONNEES / 'xt4-validation-raf.tsv').read_text().splitlines()
    tete = lignes[0].split('\t')
    for l in lignes[1:]:
        c = dict(zip(tete, l.split('\t')))
        num = c['nom'].split('-')[0]
        if num in VARIE or num in DR_SEULS:
            dr = int(''.join(ch for ch in c['DR'].split('→')[-1] if ch.isdigit())[:3])
            out[c['nom']] = (SOURCE / 'raf' / f"{c['nom']}.RAF", dr, c['lot'])
    return out


INV = inventaire()


def basculer():
    """Ce processus travaille dans le chantier de validation (xt4_mesure lit CHANTIER à chaque appel)."""
    xm.CHANTIER = VAL
    xm.RAF_TSV = VAL / 'pas-de-copie.tsv'     # preparer ne recopie pas les 16 RAF du chantier principal
    for d in ('raf', 'base', 'reference', 'blocs', 'cache', 'controle', 'tmp'):
        (VAL / d).mkdir(parents=True, exist_ok=True)


def preparer():
    """Liens vers les RAF (rien n'est copié), puis référence Provia neutre à la DR de la prise de vue, géométrie et blocs."""
    basculer()
    for n, (src, dr, lot) in INV.items():
        lien = VAL / 'raf' / f'{n}.RAF'
        if not lien.exists():
            lien.symlink_to(src)
    neutre, rafs = dict(xm.NEUTRE), xm.rafs
    try:
        for dr in sorted({d for _, d, _ in INV.values()}):
            groupe = sorted(str(VAL / 'raf' / f'{n}.RAF') for n, (_, d, _) in INV.items() if d == dr)
            xm.NEUTRE = dict(neutre, dr=dr)
            xm.rafs = lambda g=groupe: g
            xm.preparer()
    finally:
        xm.NEUTRE, xm.rafs = neutre, rafs
    journal(f'préparés : {len(list((VAL / "blocs").glob("*.npz")))} RAF')


_BL = {}


def blocs(n):
    if n not in _BL:
        d = dict(np.load(VAL / 'blocs' / f'{n}.npz'))
        d['raf'] = str(VAL / 'raf' / f'{n}.RAF')
        _BL[n] = xs.convertir_blocs(d)
    return _BL[n]


def scene_xyz(n, d=None):
    """XYZ de la scène (gris de 18 % = 0,18) : un RAF pris en DR200 / 400 est sous-exposé de 1 / 2 IL au capteur (EXIF :
    biais d'exposition RAW −1,7 / −2,7 IL contre −0,7 en DR100), que le développement à la même DR rattrape."""
    d = d if d is not None else blocs(n)
    return xm.scene(d, Y18 * 100 / INV[n][1])[1]


# ---------------------------------------------------------------------------------------------------------------
# Rendus : moyennes de toute la grille de blocs (n'importe quels blocs se relisent ensuite)
# ---------------------------------------------------------------------------------------------------------------
class Rendus:
    def __init__(self):
        basculer()
        self.banc, self.n_rendus, self.t = None, 0, 0.0

    def chemin(self, n, rec):
        return VAL / 'cache' / n / f'{xm.cle(rec)}.npy'

    def lot(self, besoin, garder=None):
        for n, recs in besoin.items():
            manque = list({xm.cle(r): r for r in recs if not self.chemin(n, r).exists()
                           or (garder and not (garder / f'{n}-{xm.cle(r)}.jpg').exists())}.values())
            if not manque:
                continue
            if self.banc is None:
                self.banc = xm.Banc()
            (VAL / 'cache' / n).mkdir(exist_ok=True)
            base = VAL / 'base' / f'{n}.bin'
            t0 = time.time()
            self.banc.charger(str(VAL / 'raf' / f'{n}.RAF'), str(base))
            b = base.read_bytes()
            futs = [None] * 4
            with cf.ThreadPoolExecutor(2) as ex:
                for i, r in enumerate(manque):
                    k = i % 4
                    if futs[k] is not None:
                        futs[k].result()
                    pf = VAL / 'tmp' / 'profil.bin'
                    pf.write_bytes(xm.profil(b, r))
                    jp = garder / f'{n}-{xm.cle(r)}.jpg' if garder else VAL / 'tmp' / f'rendu{k}.jpg'
                    if jp.exists():
                        jp.unlink()
                    self.banc.rendre(str(pf), str(jp))
                    self.n_rendus += 1
                    futs[k] = ex.submit(self._mesurer, n, r, jp)
                for f in futs:
                    if f is not None:
                        f.result()
            self.t += time.time() - t0

    def _mesurer(self, n, r, jp):
        m, _ = xm.moyennes_blocs(xm.jpeg(jp))
        p = self.chemin(n, r)
        q = p.with_suffix('.part.npy')
        np.save(q, m.astype(np.float32))
        q.rename(p)

    def lab(self, n, rec, idx):
        return dm.code_lab(np.load(self.chemin(n, rec))[idx] / 255)

    def fermer(self):
        if self.banc:
            self.banc.fermer()
            self.banc = None


def ecart(look, L, T):
    return np.abs(L[:, 0] - T[:, 0]) if look in v.NB else dm.de2000(L, T)


_F = {}


def cible(look, X, e3=0):
    if look not in _F:
        _F[look] = xc.fonction(look)
    return _F[look](X * 2.0 ** (-e3 / 3))


def bandes(look, L, T, extra=None):
    out = []
    for a, b in ((0, 30), (30, 60), (60, 75), (75, 90), (90, 101)):
        m = (T[:, 0] >= a) & (T[:, 0] < b)
        if m.sum() >= 15:
            e = ecart(look, L[m], T[m])
            out.append({'tranche': f'{a}-{min(b, 100)}', 'blocs': int(m.sum()), 'mediane': round(float(np.median(e)), 2),
                        'dL': round(float(np.median(L[m, 0] - T[m, 0])), 1)})
    if extra is not None and extra.sum() >= 10:
        e = ecart(look, L[extra], T[extra])
        out.append({'tranche': 'écrêtés en DR100', 'blocs': int(extra.sum()), 'mediane': round(float(np.median(e)), 2),
                    'dL': round(float(np.median(L[extra, 0] - T[extra, 0])), 1)})
    return out


# ---------------------------------------------------------------------------------------------------------------
# 1. Contrôle du banc : conversion par USB contre JPEG du déclenchement
# ---------------------------------------------------------------------------------------------------------------
def banc():
    """Chaque RAF de la séance développé avec le profil lu dans ce RAF (réglages de la prise de vue, rien de changé), puis
    comparé au JPEG pris au déclenchement (taille L, ramené à la taille S de la conversion par moyenne 2 × 2) : ΔE2000 par
    bloc de 16 × 16, sur tous les blocs et sur les blocs uniformes (écart-type < 4 codes dans le JPEG du déclenchement)."""
    import subprocess
    R = Rendus()
    out = {}
    try:
        noms = [n for n in INV if n.startswith('c-')]
        R.lot({n: [{}] for n in noms}, garder=VAL / 'controle')
        for n in noms:
            src = INV[n][0]
            jpg_pdv = next(src.parent.glob(src.stem.rsplit('-', 1)[0] + '-*.jpg'))
            a = xm.jpeg(jpg_pdv).astype(np.float32)
            H, W = a.shape[0] // 2 * 2, a.shape[1] // 2 * 2
            s = a[:H, :W].reshape(H // 2, 2, W // 2, 2, 3).mean((1, 3))
            mp, sp = xm.moyennes_blocs(s)
            conv = xm.jpeg(VAL / 'controle' / f'{n}-{xm.cle({})}.jpg')
            mc, _ = xm.moyennes_blocs(conv)
            Lp, Lc = dm.code_lab(mp / 255), dm.code_lab(mc / 255)
            e = dm.de2000(Lc, Lp)
            uni = sp.max(1) < 4
            st = lambda x: {'blocs': int(len(x)), 'mediane': round(float(np.median(x)), 2), 'p90': round(float(np.percentile(x, 90)), 2),  # noqa: E731
                            'max': round(float(x.max()), 2)}
            ex = {}
            for f in (jpg_pdv, VAL / 'controle' / f'{n}-{xm.cle({})}.jpg'):
                r = subprocess.run(['exiftool', '-j', '-FilmMode', '-DynamicRangeSetting', '-DevelopmentDynamicRange', '-WhiteBalance',
                                    '-HighlightTone', '-ShadowTone', '-Saturation', '-Sharpness', '-NoiseReduction', '-GrainEffectRoughness',
                                    '-ColorChromeEffect', '-ImageWidth', '-ImageHeight', str(f)], capture_output=True, text=True)
                ex[f.name] = {k: x for k, x in json.loads(r.stdout)[0].items() if k != 'SourceFile'}
            out[n] = {'jpeg_declenchement': jpg_pdv.name, 'tous_les_blocs': st(e), 'blocs_uniformes': st(e[uni]),
                      'dL_moyen': round(float(np.mean(Lc[:, 0] - Lp[:, 0])), 2), 'da_moyen': round(float(np.mean(Lc[:, 1] - Lp[:, 1])), 2),
                      'db_moyen': round(float(np.mean(Lc[:, 2] - Lp[:, 2])), 2), 'exif': ex}
            journal(f"banc {n} : tous {out[n]['tous_les_blocs']} ; uniformes {out[n]['blocs_uniformes']}")
    finally:
        R.fermer()
    tous = np.array([x['tous_les_blocs']['mediane'] for x in out.values()])
    out['_resume'] = {'mediane_des_medianes': round(float(np.median(tous)), 2), 'pire_p90': max(x['tous_les_blocs']['p90'] for x in out.values()),
                      'pire_max': max(x['tous_les_blocs']['max'] for x in out.values())}
    SORTIE_BANC.write_text(json.dumps(out, indent=1, ensure_ascii=False))


# ---------------------------------------------------------------------------------------------------------------
# 2. Plage dynamique
# ---------------------------------------------------------------------------------------------------------------
def scene_triple(sc):
    """Blocs communs aux trois vues d'une scène de la séance (trépied) : ceux du RAF DR400 (le moins écrêté). Scène lue dans
    le RAF DR400 et ramenée à l'échelle du RAF DR100 (rapport mesuré sur les blocs non écrêtés des deux) ; blocs « écrêtés en
    DR100 » : ceux dont le RAW du DR400, ramené au DR100, dépasse 0,92 de la pleine échelle (calcul)."""
    n1, n4 = f'c-{sc}-DR100', f'c-{sc}-DR400'
    d1, d4 = blocs(n1), blocs(n4)
    g1, g4 = d1['geometrie'], d4['geometrie']
    dec = float(np.hypot(*(g1[:2] - g4[:2])))
    commun, i1, i4 = np.intersect1d(d1['idx'], d4['idx'], return_indices=True)
    Y1 = d1['srgb'][i1] @ xm.M709[1]
    Y4 = d4['srgb'][i4] @ xm.M709[1]
    k = float(np.median(Y1 / np.maximum(Y4, 1e-9)))
    s = d4['srgb'] * k * (0.18 / Y18)
    X = s @ xm.M709.T
    cam = d4['srgb'] @ np.linalg.inv(d4['rgb_cam']).T / d4['wb']            # RVB caméra brut du DR400
    ecr = (cam * k).max(1) > 0.92
    return {'idx': d4['idx'], 'X': X, 'ecretes_dr100': ecr, 'rapport_dr400_dr100': round(k, 3), 'decalage_geometrie_px': round(dec, 2),
            'blocs': int(len(d4['idx'])), 'blocs_communs': int(len(commun))}


def options(rec):
    """(dr, Δh) → recette ; h borné à −2..+4."""
    out = {}
    for dr in (100, 200, 400):
        for dh in DH:
            h = rec.get('h', 0) + dh
            if -2 <= h <= 4:
                out[(dr, dh)] = v.normaliser(dict(rec, dr=dr, drp=0, h=h))
    return out


def dr():
    """Pour chaque recette retenue : DR100 / 200 / 400 (et hautes lumières reprises de ±1) sur les trois scènes de la séance
    (chaque vue développée à sa DR, cible = scène du RAF DR100) et sur les RAF pris en DR200 / 400 du lot de validation
    (le même RAF développé à DR100 et à sa DR). Gain net : au moins SEUIL_DR au critère en moyenne et sur 2 scènes sur 3."""
    bil = json.loads(v.SORTIE.read_text())
    R = Rendus()
    triples = {sc: scene_triple(sc) for sc in SCENES.values()}
    seuls = [n for n in INV if n.split('-')[0] in DR_SEULS]
    out = {'scenes': {sc: {k: x for k, x in t.items() if k not in ('idx', 'X', 'ecretes_dr100')} | {'ecretes_dr100': int(t['ecretes_dr100'].sum())}
                      for sc, t in triples.items()}, 'looks': {}}
    choix = json.loads(v.DR_CHOIX.read_text()) if v.DR_CHOIX.exists() else {}
    try:
        for l, b in bil.items():
            rec, e3 = b['nouvelle']['rec'], b['nouvelle']['e3']
            opts = options(rec)
            besoin = {}
            for sc in SCENES.values():
                for dr_ in (100, 200, 400):
                    besoin[f'c-{sc}-DR{dr_}'] = [r for (d, _), r in opts.items() if d == dr_]
            for n in seuls:
                besoin[n] = [r for (d, _), r in opts.items() if d <= INV[n][1]]
            R.lot(besoin)
            res = {}
            for sc, t in triples.items():
                T = cible(l, t['X'], e3)
                for (d, dh), r in opts.items():
                    L = R.lab(f'c-{sc}-DR{d}', r, t['idx'])
                    res.setdefault(f'{d}/{dh:+d}', {})[sc] = {**xm.resume({sc: ecart(l, L, T)}), 'tranches': bandes(l, L, T, t['ecretes_dr100'])}
            for n in seuls:
                d0 = blocs(n)
                T = cible(l, scene_xyz(n, d0), e3)
                for (d, dh), r in opts.items():
                    if d <= INV[n][1]:
                        L = R.lab(n, r, d0['idx'])
                        res.setdefault(f'{d}/{dh:+d}', {})[n] = {**xm.resume({n: ecart(l, L, T)}), 'tranches': bandes(l, L, T)}
            # comparaison : la meilleure reprise des hautes lumières à chaque DR, contre DR100 sur les mêmes scènes
            meilleure = {}
            for d in (100, 200, 400):
                cles = [k for k in res if k.startswith(f'{d}/')]
                sc_tri = list(SCENES.values())
                meilleure[d] = min(cles, key=lambda k: np.mean([res[k][s]['score'] for s in sc_tri]))
            comp = {}
            for d in (200, 400):
                k, k0 = meilleure[d], meilleure[100]
                communes = [s for s in res[k] if s in res[k0]]
                g = {s: round(res[k0][s]['score'] - res[k][s]['score'], 3) for s in communes}
                tri = [g[s] for s in SCENES.values()]
                comp[d] = {'reglage': k, 'contre': k0, 'gain_par_scene': g, 'gain_moyen_seance': round(float(np.mean(tri)), 3),
                           'gain_moyen_tout': round(float(np.mean(list(g.values()))), 3),
                           'net': bool(np.mean(tri) >= SEUIL_DR and sum(x > 0 for x in tri) >= 2)}
            nets = [d for d in (200, 400) if comp[d]['net']]
            gagnante = max(nets, key=lambda d: comp[d]['gain_moyen_seance']) if nets else 100
            out['looks'][l] = {'options': res, 'meilleure_par_dr': meilleure, 'comparaison': comp, 'dr_retenue': gagnante}
            if gagnante != 100:
                dh = int(meilleure[gagnante].split('/')[1])
                choix[l] = {'dr': gagnante, 'h': v.normaliser({'h': rec.get('h', 0) + dh})['h']}
            else:
                choix.pop(l, None)
            journal(f"DR {l} : " + ' ; '.join(f"DR{d} {comp[d]['reglage']} gain séance {comp[d]['gain_moyen_seance']} tout {comp[d]['gain_moyen_tout']}"
                                              for d in (200, 400)) + f' → DR{gagnante}')
    finally:
        R.fermer()
    SORTIE_DR.write_text(json.dumps(out, indent=1, ensure_ascii=False, default=float))
    v.ecrire_atomique(v.DR_CHOIX, json.dumps(choix, indent=1))


# recettes retenues pour C1 à C7 absentes de dr : (fichier, look noté, consigne en tiers d'IL, DR d'origine du .FP1)
RETENUES = {'DC Classic Chrome II': (xm.PRESETS / 'DC Classic Chrome II.FP1', 'cc_130_contraste', 0, 100),
            'NZD Ektar 100': (xm.PRESETS / 'NZD Ektar 100.FP1', 'portra', 1, 'AUTO'),
            'RR Acros Push Process': (xm.PRESETS / 'RR Acros Push Process.FP1', 'trix', 0, 200),
            'TH Ektar 100': (xm.RECETTES / 'TH Ektar 100.FP1', 'ektar', 0, 100)}
SANS_SCENE3 = ('guitares', 'fenetre')


def comparer_dr(res, scenes):
    """Meilleure reprise de H à chaque DR, choisie sur ces scènes ; gain contre DR100, la règle de dr() sur ces scènes."""
    meilleure = {d: min((k for k in res if k.startswith(f'{d}/')), key=lambda k: np.mean([res[k][s]['score'] for s in scenes]))
                 for d in (100, 200, 400)}
    comp = {}
    for d in (200, 400):
        g = {s: round(res[meilleure[100]][s]['score'] - res[meilleure[d]][s]['score'], 3) for s in scenes}
        moyen = float(np.mean(list(g.values())))
        comp[d] = {'reglage': meilleure[d], 'contre': meilleure[100], 'gain_par_scene': g, 'gain_moyen': round(moyen, 3),
                   'scenes_gagnees': sum(x > 0 for x in g.values()), 'net': bool(moyen >= SEUIL_DR and sum(x > 0 for x in g.values()) >= 2)}
    return {'meilleure_par_dr': meilleure, 'comparaison': comp, 'dr_retenue': max((d for d in comp if comp[d]['net']),
            key=lambda d: comp[d]['gain_moyen'], default=100)}


def origine_dr(res, dr0, scenes):
    """La recette telle quelle (H inchangé) contre DR100 : à sa DR, ou, en DR Auto, la meilleure DR scène par scène, ce que le
    boîtier pourrait atteindre au mieux en choisissant toujours juste (borne : son choix réel ne se mesure pas sur ces RAF)."""
    if dr0 == 'AUTO':
        borne = lambda ds: {s: round(res['100/+0'][s]['score'] - min(res[f'{d}/+0'][s]['score'] for d in ds), 3) for s in scenes}  # noqa: E731
        return {f'borne_{"_".join(map(str, ds))}': {'gain_par_scene': (g := borne(ds)), 'gain_moyen': round(float(np.mean(list(g.values()))), 3)}
                for ds in ((100, 200), (100, 200, 400))}
    g = {s: round(res['100/+0'][s]['score'] - res[f'{dr0}/+0'][s]['score'], 3) for s in scenes}
    return {'gain_par_scene': g, 'gain_moyen': round(float(np.mean(list(g.values()))), 3)}


def dr_retenues():
    """Comme dr(), sur les triples du trépied seulement, pour RETENUES : rendu à la balance de la prise de vue, grain coupé, chaque vue
    développée à sa DR, cible de son look (consigne : cible décalée). Résultat avec les trois scènes (décision) et sans la scène 3,
    aux cadrages non superposés (H rechoisi sur les deux autres ; il faut alors gagner sur les deux). Rien n'entre dans un .FP1."""
    regle = f"gain moyen >= {SEUIL_DR} et au moins 2 scènes gagnées, inchangée ; sans la scène 3 : les 2 scènes restantes"
    journal(f'DR des recettes retenues : règle fixée avant tout rendu : {regle}')
    R = Rendus()
    triples = {sc: scene_triple(sc) for sc in SCENES.values()}
    out = {'regle': regle, 'recettes': {}}
    try:
        for nom, (fp1, l, e3, dr0) in RETENUES.items():
            opts = options(v.sans_balance(v.pour_mesure_v2(xm.lire_fp1(fp1)))[0])
            R.lot({f'c-{sc}-DR{d}': [r for (x, _), r in opts.items() if x == d] for sc in SCENES.values() for d in (100, 200, 400)})
            res = {}
            for sc, t in triples.items():
                T = cible(l, t['X'], e3)
                for (d, dh), r in opts.items():
                    res.setdefault(f'{d}/{dh:+d}', {})[sc] = xm.resume({sc: ecart(l, R.lab(f'c-{sc}-DR{d}', r, t['idx']), T)})
            tous = tuple(SCENES.values())
            out['recettes'][nom] = {'look': l, 'e3': e3, 'dr_origine': dr0, 'options': res, 'trois_scenes': comparer_dr(res, tous),
                                    'sans_scene3': comparer_dr(res, SANS_SCENE3)}
            if dr0 != 100:
                out['recettes'][nom]['origine'] = {'trois_scenes': origine_dr(res, dr0, tous), 'sans_scene3': origine_dr(res, dr0, SANS_SCENE3)}
            x = out['recettes'][nom]
            journal(f"DR retenue {nom} : trois scènes DR{x['trois_scenes']['dr_retenue']}, sans la scène 3 DR{x['sans_scene3']['dr_retenue']}")
    finally:
        R.fermer()
        journal(f'DR des recettes retenues : {R.n_rendus} rendus')
    (xm.DONNEES / f'xt4-dr-retenues-{DATE}.json').write_text(json.dumps(out, indent=1, ensure_ascii=False, default=float))


# ---------------------------------------------------------------------------------------------------------------
# 3. Lot varié : verdict final hors échantillon
# ---------------------------------------------------------------------------------------------------------------
def validation():
    """Recettes figées (celles cherchées sur les 16 RAF, grain coupé, DR100) et recettes de 2022 (les trois meilleures sur les
    16, celle nommée pour le look, la meilleure avec une consigne d'exposition) sur le lot varié (RAF d'au moins MIN_BLOCS blocs uniformes), jamais vus par la
    recherche. Comparateur fixé d'avance : la meilleure recette de 2022 sur les 16 RAF."""
    bil = json.loads(v.SORTIE.read_text())
    P = v.presets()
    tous = sorted(n for n in INV if n.split('-')[0] in VARIE)
    noms = [n for n in tous if len(blocs(n)['idx']) >= MIN_BLOCS]
    exclus = {n: int(len(blocs(n)['idx'])) for n in tous if n not in noms}
    journal(f'lot varié : {len(noms)} RAF sur {len(tous)} ; écartés faute de blocs uniformes (moins de {MIN_BLOCS}) : {exclus}')
    X = {n: scene_xyz(n) for n in noms}
    R = Rendus()
    out = {}
    try:
        cands = {}
        for l, b in bil.items():
            c = {'nouvelle': (b['nouvelle']['rec'], b['nouvelle']['e3'])}
            # recettes de 2022 à la balance de la prise de vue : plus aucune balance forcée (voir xt4_recherche_v2.DOM_NB)
            sb = lambda nom: v.sans_balance(P[nom]['rec'])[0]  # noqa: E731
            for e in b['existantes_classees'][:3]:
                c[e['nom']] = (sb(e['nom']), 0)
            c[b['existante_nommee']['nom']] = (sb(b['existante_nommee']['nom']), 0)
            x = b['meilleure_existante_16_avec_exposition']
            c[f"{x['nom']} ({x['exposition']} IL)"] = (sb(x['nom']), x['e3'])
            cands[l] = c
        R.lot({n: [r for c in cands.values() for r, _ in c.values()] for n in noms})
        for l, c in cands.items():
            b = bil[l]
            res = {}
            for k, (r, e3) in c.items():
                ec = {n: ecart(l, R.lab(n, r, blocs(n)['idx']), cible(l, X[n], e3)) for n in noms}
                res[k] = {**xm.resume(ec), 'par_raf': {n: round(float(np.median(x)), 2) for n, x in ec.items()},
                          'recette': v.texte(r, e3)}
            ref = b['meilleure_existante_16']['nom']
            meilleure_24 = min((k for k in res if k != 'nouvelle'), key=lambda k: res[k]['score'])
            gagne = res['nouvelle']['score'] < res[ref]['score']
            raf_gagnes = sum(res['nouvelle']['par_raf'][n] < res[ref]['par_raf'][n] for n in noms)
            out[l] = {'nom': b['nom'], 'unite': b['unite'], 'resultats': res, 'comparateur': ref, 'meilleure_existante_sur_24': meilleure_24,
                      'verdict': 'gain' if gagne else 'pas de gain', 'raf_gagnes': f'{raf_gagnes}/{len(noms)}',
                      'raf_notes': len(noms), 'raf_ecartes': exclus}
            journal(f"validation {l} : nouvelle {res['nouvelle']['mediane']} ({res['nouvelle']['p90']}) contre {ref} "
                    f"{res[ref]['mediane']} ({res[ref]['p90']}) ; meilleure sur 24 {meilleure_24} {res[meilleure_24]['mediane']} : "
                    f"{out[l]['verdict']}, {raf_gagnes}/{len(noms)} RAF")
    finally:
        R.fermer()
    SORTIE_VAL.write_text(json.dumps(out, indent=1, ensure_ascii=False, default=float))


def familles():
    """Sans boîtier, d'après les rendus du lot varié (cache) : d'où viennent les écarts. Pour chaque look, écart médian par famille
    de couleur de la scène (xt4_mesure.CATEGORIES, plus neutres, clairs, sombres), recette TH contre le comparateur et la meilleure
    recette de 2022 sur le lot ; et la part de chaque famille dans le lot varié et dans les 16 RAF de la recherche."""
    bil, res = json.loads(v.SORTIE.read_text()), json.loads(SORTIE_VAL.read_text())
    P = v.presets()
    noms = [n for n in sorted(n for n in INV if n.split('-')[0] in VARIE) if len(blocs(n)['idx']) >= MIN_BLOCS]
    R = Rendus.__new__(Rendus)          # lecture du cache seulement : aucun banc ouvert

    def masques(S):
        C, h = np.hypot(S[:, 1], S[:, 2]), np.degrees(np.arctan2(S[:, 2], S[:, 1])) % 360
        m = {k: f(S[:, 0], C, h) for k, f in xm.CATEGORIES.items()}
        return m | {'neutres': C < 6, 'clairs (L* > 80)': S[:, 0] > 80, 'sombres (L* < 25)': S[:, 0] < 25}
    v.cibles()
    S_var = np.concatenate([dm.xyz_lab(scene_xyz(n)) for n in noms])
    S_16 = np.concatenate([v.SC[n] for n in v.TOUS])
    out = {'part_des_familles': {k: {'lot_varie': round(float(m.mean()), 3), 'recherche_16': round(float(masques(S_16)[k].mean()), 3)}
                                 for k, m in masques(S_var).items()}, 'looks': {}}
    for l, x in res.items():
        b = bil[l]
        cands = {'TH': (b['nouvelle']['rec'], b['nouvelle']['e3'])}
        for k in {x['comparateur'], x['meilleure_existante_sur_24']}:
            nom, e3 = k, 0
            if k.endswith(' IL)'):
                nom = k.rsplit(' (', 1)[0]
                e3 = b['meilleure_existante_16_avec_exposition']['e3']
            cands[k] = (v.sans_balance(P[nom]['rec'])[0], e3)
        y = {}
        for k, (r, e3) in cands.items():
            E = np.concatenate([ecart(l, R.lab(n, r, blocs(n)['idx']), cible(l, scene_xyz(n), e3)) for n in noms])
            y[k] = {f: round(float(np.median(E[m])), 2) for f, m in masques(S_var).items() if m.sum() >= 20}
        out['looks'][l] = y
        journal(f"familles {l} : " + ' ; '.join(f"{k} {y[k]}" for k in y))
    (xm.DONNEES / f'xt4-validation-familles-{DATE}.json').write_text(json.dumps(out, indent=1, ensure_ascii=False))


if __name__ == '__main__':
    a = sys.argv[1:]
    if not a:
        print(__doc__)
        sys.exit(2)
    for etape in a:
        globals()[etape]()
