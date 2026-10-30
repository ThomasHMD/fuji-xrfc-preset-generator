#!/usr/bin/env python3
# SPDX-License-Identifier: CC-BY-NC-4.0
# Copyright (c) 2026 Thomas Hammoudi
"""Leviers cachés et non explorés du profil de conversion 0xD185 du X-T4, mesurés sur le boîtier (séance du 29/10/2026).
Le boîtier rend chaque variante d'un RAF (xt4_banc.swift, comme xt4_mesure) ; chaque variante est comparée, bloc par bloc
(blocs uniformes de xt4_mesure), au rendu de référence du même RAF : écart de L*, de chroma et ΔE2000 par tranche de
clarté, écart de L* par famille de couleur de la scène, différences de l'EXIF (exiftool).

  xt4_leviers.py index     index sans nom chez FilmKit (0, 1, 2, 3, 5, 21, 22, 24), sur le Provia neutre
  xt4_leviers.py balance   balance Température 2 500 à 10 000 K (Acros, Monochrome, Astia, Provia) ; décalages R/B ±9
  xt4_leviers.py dr        DR200, DR400, priorité D-Range faible et forte (Provia, Acros)
  xt4_leviers.py ccnb      Color Chrome et FX Blue en Acros et Monochrome
  xt4_leviers.py grain     réduction du bruit −4 et netteté −4 avec le grain fort et gros : σ L* au cercle de 48 µm
  xt4_leviers.py bornes    tons et couleur hors des bornes de l'écran, pas de 0,1 ; index 2 et 3 sur d'autres valeurs
  xt4_leviers.py exif      relit l'EXIF des JPEG gardés (exiftool) et note ce qui change
  xt4_leviers.py bilan     écrit recherche/donnees/xt4-leviers-2026-10-29.json

Rien n'est écrit dans le boîtier hors du profil de conversion (0xD185, 0xD183) : chaque rendu envoie un profil complet,
construit sur celui que le boîtier lit dans le RAF ; le dernier rendu de chaque essai renvoie ce profil d'origine tel quel.
Deux erreurs de suite autres qu'un refus du profil : arrêt (boîtier perdu ?), sans nouvelle tentative.
JPEG et résultats intermédiaires : CHANTIER/leviers/ (hors du dépôt).
"""
import json
import pathlib
import subprocess
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import xt4_mesure as xm  # noqa: E402

DOSSIER = xm.CHANTIER / 'leviers'
SORTIE = xm.DONNEES / 'xt4-leviers-2026-10-29.json'
TRANCHES = ((0, 15), (15, 30), (30, 45), (45, 60), (60, 75), (75, 90), (90, 101))
CACHES = [0, 1, 2, 3, 5, 21, 22, 24]
VALEURS = [-100, -30, -10, 0, 1, 2, 3, 10, 30, 100, 10000]
KELVINS = [2500, 3200, 4000, 5000, 6500, 8000, 10000]


class Arret(Exception):
    pass


class Session:
    """Un banc ouvert pour tout l'essai ; rend des recettes (dict de xt4_mesure, champ « brut » pour un index nu)."""

    def __init__(self, essai):
        self.dossier = DOSSIER / essai
        self.dossier.mkdir(parents=True, exist_ok=True)
        self.banc = None
        self.erreurs = 0
        self.dernier = None
        self.journal = {}

    def rendre(self, n, variantes):
        raf = xm.CHANTIER / 'raf' / f'{n}.RAF'
        base = self.dossier / f'base-{n}.bin'
        out = {}
        for nom, rec in variantes.items():
            jp = self.dossier / f'{n}-{nom}.jpg'
            if jp.exists():
                out[nom] = jp
                continue
            if self.banc is None:
                self.banc = xm.Banc()
            self.banc.charger(str(raf), str(base))
            pf = self.dossier / 'profil.bin'
            pf.write_bytes(xm.profil(base.read_bytes(), rec) if rec is not None else base.read_bytes())
            try:
                self.banc.rendre(str(pf), str(jp))
                out[nom] = jp
                self.erreurs = 0
            except RuntimeError as e:
                msg = str(e)
                out[nom] = msg
                self.journal[f'{n}-{nom}'] = msg
                if 'profil refusé' not in msg:
                    self.erreurs += 1
                    if self.erreurs >= 2:
                        raise Arret(f'deux erreurs de suite ({msg}) : arrêt, boîtier à vérifier')
            self.dernier = (n, base)
        return out

    def fermer(self):
        """Dernier rendu : le profil d'origine du dernier RAF, tel quel ; puis fermeture du banc."""
        if self.banc is not None:
            if self.dernier:
                n, base = self.dernier
                pf = self.dossier / 'profil.bin'
                pf.write_bytes(base.read_bytes())
                try:
                    self.banc.rendre(str(pf), str(self.dossier / f'{n}-remise-origine.jpg'))
                except RuntimeError as e:
                    self.journal['remise'] = str(e)
            self.banc.fermer()
            self.banc = None
        (self.dossier / 'erreurs.json').write_text(json.dumps(self.journal, indent=1, ensure_ascii=False))


# ---------------------------------------------------------------------------------------------------------------
# Mesure : une variante contre la référence du même RAF
# ---------------------------------------------------------------------------------------------------------------
_ctx = {}


def contexte():
    if not _ctx:
        et = json.loads((xm.CHANTIER / 'etalonnage.json').read_text())
        _, sc = xm.cibles(et['y18'])
        _ctx.update(blocs=xm.charger_blocs(), sc=sc, dm=xm._dm())
    return _ctx


def labs(n, a):
    c = contexte()
    m, _ = xm.moyennes_blocs(a, c['blocs'][n]['idx'])
    return c['dm'].code_lab(m / 255)


def comparer(paires):
    """paires : [(n, jpeg variante, jpeg référence)] ; blocs de tous les RAF mis ensemble."""
    c = contexte()
    dm = c['dm']
    La, Lr, S, pix, formes = [], [], [], [], set()
    for n, jv, jr in paires:
        if not isinstance(jv, pathlib.Path) or not isinstance(jr, pathlib.Path):
            return {'erreur': jv if not isinstance(jv, pathlib.Path) else jr}
        av, ar = xm.jpeg(jv), xm.jpeg(jr)
        if av.shape != ar.shape:
            formes.add(f'{av.shape[1]}×{av.shape[0]}')
            continue
        lv, lr = labs(n, av), labs(n, ar)
        pix.append(float(np.abs(av.astype(np.int16) - ar.astype(np.int16)).mean()))
        La.append(lv)
        Lr.append(lr)
        S.append(c['sc'][n])
    if not La:
        return {'forme_differente': sorted(formes)}
    La, Lr, S = np.concatenate(La), np.concatenate(Lr), np.concatenate(S)
    de = dm.de2000(La, Lr)
    Ca, Cr = np.hypot(La[:, 1], La[:, 2]), np.hypot(Lr[:, 1], Lr[:, 2])
    out = {'blocs': int(len(La)), 'pixels_ecart_moyen': round(float(np.mean(pix)), 2),
           'dE_mediane': round(float(np.median(de)), 2), 'dE_p90': round(float(np.quantile(de, 0.9)), 2),
           'dL_mediane': round(float(np.median(La[:, 0] - Lr[:, 0])), 2), 'dC_mediane': round(float(np.median(Ca - Cr)), 2),
           'da_mediane': round(float(np.median(La[:, 1] - Lr[:, 1])), 2), 'db_mediane': round(float(np.median(La[:, 2] - Lr[:, 2])), 2),
           'tranches': {}, 'familles': {}}
    if formes:
        out['forme_differente'] = sorted(formes)
    for a, b in TRANCHES:
        m = (Lr[:, 0] >= a) & (Lr[:, 0] < b)
        if m.sum() >= 20:
            out['tranches'][f'{a}-{min(b, 100)}'] = {'blocs': int(m.sum()), 'dL': round(float(np.median(La[m, 0] - Lr[m, 0])), 2),
                                                    'dC': round(float(np.median(Ca[m] - Cr[m])), 2)}
    C = np.hypot(S[:, 1], S[:, 2])
    h = np.degrees(np.arctan2(S[:, 2], S[:, 1])) % 360
    for k, f in xm.CATEGORIES.items():
        m = f(S[:, 0], C, h)
        if m.sum() >= 15:
            out['familles'][k] = {'blocs': int(m.sum()), 'dL': round(float(np.median(La[m, 0] - Lr[m, 0])), 2)}
    return out


def ecrire(essai, res):
    (DOSSIER / f'{essai}.json').write_text(json.dumps(res, indent=1, ensure_ascii=False))


# ---------------------------------------------------------------------------------------------------------------
# Essais
# ---------------------------------------------------------------------------------------------------------------
def index():
    rafs = ['167-DSCF0467', '176-DSCF0476']
    s = Session('index')
    res = {}
    jp = {}
    try:
        for n in rafs:
            jp[n] = s.rendre(n, {'ref': dict(xm.NEUTRE)})
            o = xm.d185_params((s.dossier / f'base-{n}.bin').read_bytes())[1]
            jp[n] |= s.rendre(n, {f'i{i:02d}_{v}': dict(xm.NEUTRE, brut={i: v}) for i in CACHES for v in VALEURS if v != o[i]})
    finally:
        s.fermer()
    o = xm.d185_params((s.dossier / f'base-{rafs[0]}.bin').read_bytes())[1]
    for i in CACHES:
        res[i] = {'origine': o[i], 'valeurs': {}}
        for v in [x for x in VALEURS if x != o[i]]:
            nom = f'i{i:02d}_{v}'
            r = comparer([(n, jp[n].get(nom), jp[n]['ref']) for n in rafs])
            r['taille_fichier_rel'] = [round(jp[n][nom].stat().st_size / jp[n]['ref'].stat().st_size, 3)
                                       if isinstance(jp[n].get(nom), pathlib.Path) else None for n in rafs]
            res[i]['valeurs'][v] = r
    ecrire('index', res)
    return res


def balance():
    rafs = ['176-DSCF0476', '179-DSCF0479', '006-DSCF9213', '041-DSCF6283', '167-DSCF0467']
    s = Session('balance')
    res = {}
    try:
        for sim in (12, 6, 3, 1):
            base = dict(xm.NEUTRE, sim=sim)
            var = {f's{sim}_ref': base}
            var |= {f's{sim}_k{k}': dict(base, wb=xm.WB['Temperature'], kelvin=k) for k in KELVINS}
            var |= {f's{sim}_jour': dict(base, wb=xm.WB['Daylight']), f's{sim}_tungstene': dict(base, wb=xm.WB['Incand'])}
            var |= {f's{sim}_{c}{v:+d}': dict(base, **{c: v}) for c in ('wb_r', 'wb_b') for v in (-9, 9)}
            jp = {n: s.rendre(n, var) for n in rafs}
            res[xm.SIMS[sim]] = {nom.split('_', 1)[1]: comparer([(n, jp[n][nom], jp[n][f's{sim}_ref']) for n in rafs])
                                 for nom in var if not nom.endswith('_ref')}
            ecrire('balance', res)
    finally:
        s.fermer()
    ecrire('balance', res)
    return res


def balance2():
    """Balance avec l'index 11 (WBShootCond) à 0 : Auto recalculée contre la balance de la prise de vue, décalages R/B ±9
    et Température 2 500 / 10 000 K, en Acros et Monochrome ; écarts contre Auto (index 11 = 0, sans décalage)."""
    rafs = ['176-DSCF0476', '179-DSCF0479', '006-DSCF9213', '041-DSCF6283', '167-DSCF0467']
    s = Session('balance2')
    res = {}
    try:
        for sim in (12, 6):
            pdv = dict(xm.NEUTRE, sim=sim)                                  # index 11 laissé à 1 : prise de vue
            auto = dict(pdv, wb=xm.WB['Auto'], brut={11: 0})
            var = {f's{sim}_ref': auto, f's{sim}_pdv': pdv}
            var |= {f's{sim}_{c}{v:+d}': dict(auto, **{c: v}) for c in ('wb_r', 'wb_b') for v in (-9, 9)}
            var |= {f's{sim}_k{k}': dict(pdv, wb=xm.WB['Temperature'], kelvin=k, brut={11: 0}) for k in (2500, 10000)}
            jp = {n: s.rendre(n, var) for n in rafs}
            res[xm.SIMS[sim]] = {nom.split('_', 1)[1]: comparer([(n, jp[n][nom], jp[n][f's{sim}_ref']) for n in rafs])
                                 for nom in var if not nom.endswith('_ref')}
            ecrire('balance2', res)
    finally:
        s.fermer()
    ecrire('balance2', res)
    return res


def expo():
    """Index 4 (ExposureBias chez FilmKit) : Acros et Provia neutres, plusieurs codages possibles de la valeur."""
    rafs = ['167-DSCF0467', '157-DSCF9412']
    vals = (-300, -100, -30, -10, -3, -1, 1, 3, 10, 30, 100, 300, 1000)
    s = Session('expo')
    res = {}
    try:
        for sim in (12, 1):
            base = dict(xm.NEUTRE, sim=sim)
            var = {f's{sim}_ref': base} | {f's{sim}_e{v:+d}': dict(base, brut={4: v}) for v in vals}
            jp = {n: s.rendre(n, var) for n in rafs}
            res[xm.SIMS[sim]] = {nom.split('_', 1)[1]: comparer([(n, jp[n][nom], jp[n][f's{sim}_ref']) for n in rafs])
                                 for nom in var if not nom.endswith('_ref')}
    finally:
        s.fermer()
    ecrire('expo', res)
    return res


def dr():
    rafs = ['157-DSCF9412', '051-DSCF8719', '163-DSCF9423', '167-DSCF0467']
    s = Session('dr')
    res = {}
    try:
        for sim in (1, 12):
            base = dict(xm.NEUTRE, sim=sim)
            var = {f's{sim}_ref': base, f's{sim}_dr200': dict(base, dr=200), f's{sim}_dr400': dict(base, dr=400),
                   f's{sim}_drp1': dict(base, drp=1), f's{sim}_drp2': dict(base, drp=2)}
            jp = {n: s.rendre(n, var) for n in rafs}
            res[xm.SIMS[sim]] = {nom.split('_', 1)[1]: comparer([(n, jp[n][nom], jp[n][f's{sim}_ref']) for n in rafs])
                                 for nom in var if not nom.endswith('_ref')}
            ecrire('dr', res)
    finally:
        s.fermer()
    ecrire('dr', res)
    return res


def ccnb():
    rafs = ['176-DSCF0476', '179-DSCF0479', '006-DSCF9213', '041-DSCF6283', '167-DSCF0467']
    s = Session('ccnb')
    res = {}
    try:
        for sim in (12, 6):
            base = dict(xm.NEUTRE, sim=sim)
            var = {f's{sim}_ref': base}
            var |= {f's{sim}_{c}{v}': dict(base, **{c: v}) for c in ('cc', 'ccb') for v in (2, 3)}
            jp = {n: s.rendre(n, var) for n in rafs}
            res[xm.SIMS[sim]] = {nom.split('_', 1)[1]: comparer([(n, jp[n][nom], jp[n][f's{sim}_ref']) for n in rafs])
                                 for nom in var if not nom.endswith('_ref')}
            ecrire('ccnb', res)
    finally:
        s.fermer()
    ecrire('ccnb', res)
    return res


def grain():
    """σ de L* au cercle de 48 µm sur les blocs de L* 35 à 65 (méthode de xt4_mesure.grain) : grain ajouté (rendu − même
    rendu grain coupé) et bruit total du rendu (écart-type dans le bloc, moins celui du rendu de référence sans grain ni
    réglage, qui compte la texture de la scène)."""
    import cv2
    dm = xm._dm()
    best = json.loads((xm.CHANTIER / 'meilleures.json').read_text())['trix']['recette']
    s = Session('grain')
    r_ap = xm.APERTURE_UM / 2 / xm.PIXEL_JPEG_UM
    k = int(np.ceil(r_ap))
    yy, xx = np.mgrid[-k:k + 1, -k:k + 1]
    noyau = ((xx ** 2 + yy ** 2) <= r_ap ** 2).astype(np.float32)
    noyau /= noyau.sum()
    configs = {'nr0_n0': dict(bruit=0, nettete=0), 'nr-4_n0': dict(bruit=-4, nettete=0), 'nr-4_n-4': dict(bruit=-4, nettete=-4)}
    var = {f'{c}_g{g}': dict(best, grain=g, **p) for c, p in configs.items() for g in (1, 3, 5)}
    res = {}
    try:
        jp = {n: s.rendre(n, var) for n in xm.GRAIN_RAF}
    finally:
        s.fermer()
    B = xm.B
    blocs = contexte()['blocs']

    def sig(arr, sel):
        f = cv2.filter2D(arr.astype(np.float32), -1, noyau)
        H, W = arr.shape[0] // B * B, arr.shape[1] // B * B
        return f[:H, :W].reshape(H // B, B, W // B, B).transpose(0, 2, 1, 3).reshape(-1, B * B)[sel].std(1)

    for nom in var:
        aj, tot = [], []
        for n in xm.GRAIN_RAF:
            L = lambda q: dm.code_lab(xm.jpeg(jp[n][q]) / 255.0)[..., 0]  # noqa: E731
            a, z, z0 = L(nom), L(nom.rsplit('_', 1)[0] + '_g1'), L('nr0_n0_g1')
            H, W = a.shape[0] // B * B, a.shape[1] // B * B
            idx = blocs[n]['idx']
            ref = z0[:H, :W].reshape(H // B, B, W // B, B).mean((1, 3)).ravel()[idx]
            sel = idx[(ref > 35) & (ref < 65)]
            aj.append(sig(a - z, sel))
            tot.append(np.sqrt(np.maximum(sig(a, sel) ** 2 - sig(z0, sel) ** 2, 0)))
        res[nom] = {'grain_ajoute_48um': round(float(np.median(np.concatenate(aj))), 2),
                    'bruit_en_plus_du_rendu_de_base_48um': round(float(np.median(np.concatenate(tot))), 2)}
    res['cible_trix_48um'] = json.loads((xm.CHANTIER / 'grain.json').read_text())['trix_cible']['sigma_L_48um']
    ecrire('grain', res)
    return res


def bornes():
    """Tons et couleur hors des bornes de l'écran (H, S : −2 à +4 ; couleur : ±4), pas de 0,1 ; index 2 et 3 (taille,
    format) sur d'autres valeurs. Chaque valeur hors bornes est comparée à la référence et à la borne la plus proche."""
    rafs = ['167-DSCF0467', '176-DSCF0476']
    base = dict(xm.NEUTRE)
    var = {'ref': base}
    var |= {f'h{v:+g}': dict(base, h=v) for v in (-4, -3, -2.5, -2, 1, 1.2, 1.5, 4, 4.5, 5, 6)}
    var |= {f's{v:+g}': dict(base, s=v) for v in (-4, -3, -2.5, -2, 4, 4.5, 5, 6)}
    var |= {f'c{v:+g}': dict(base, couleur=v) for v in (-6, -5, -4, 4, 5, 6)}
    var |= {f'i02_{v}': dict(base, brut={2: v}) for v in (4, 5, 6, 8, 9, 15)}
    var |= {f'i03_{v}': dict(base, brut={3: v}) for v in (4, 5, 6, 8, 9)}
    s = Session('bornes')
    try:
        jp = {n: s.rendre(n, var) for n in rafs}
    finally:
        s.fermer()
    borne = {'h': (-2, 4), 's': (-2, 4), 'c': (-4, 4)}
    res = {}
    for nom in var:
        if nom == 'ref':
            continue
        r = {'contre_ref': comparer([(n, jp[n][nom], jp[n]['ref']) for n in rafs])}
        k = nom[0]
        if k in borne and not nom.startswith('i'):
            v = float(nom[1:])
            lo, hi = borne[k]
            if v < lo or v > hi:
                b = f'{k}{(lo if v < lo else hi):+g}'
                r['contre_borne'] = {'borne': b, **comparer([(n, jp[n][nom], jp[n][b]) for n in rafs])}
        if nom == 'h+1.2':
            r['contre_h+1'] = comparer([(n, jp[n][nom], jp[n]['h+1']) for n in rafs])
            r['contre_h+1.5'] = comparer([(n, jp[n][nom], jp[n]['h+1.5']) for n in rafs])
        res[nom] = r
    ecrire('bornes', res)
    return res


def exif():
    """EXIF des JPEG gardés : pour chaque variante, les balises qui diffèrent de la référence du même RAF et du même essai."""
    ignore = {'SourceFile', 'FileName', 'Directory', 'FileSize', 'FileModifyDate', 'FileAccessDate', 'FileInodeChangeDate',
              'FilePermissions', 'ThumbnailImage', 'ThumbnailOffset', 'ThumbnailLength', 'PreviewImage'}
    out = {}
    for essai in ('index', 'balance', 'dr', 'ccnb', 'grain', 'bornes', 'balance2', 'expo'):
        d = DOSSIER / essai
        if not d.exists():
            continue
        r = subprocess.run(['exiftool', '-j', '-a', '-G1', '-n', *sorted(map(str, d.glob('*.jpg')))], capture_output=True, text=True)
        tags = {pathlib.Path(x['SourceFile']).stem: {k: v for k, v in x.items() if k.split(':')[-1] not in ignore} for x in json.loads(r.stdout or '[]')}
        diffs = {}
        for nom, t in tags.items():
            n, var = nom.split('-', 2)[0] + '-' + nom.split('-', 2)[1], nom.split('-', 2)[2]
            refs = [k for k in tags if k.startswith(n + '-') and (k.endswith('-ref') or k.endswith('_ref') or k.endswith('nr0_n0_g1'))
                    and (essai in ('index', 'grain', 'bornes') or k.split('-', 2)[2].split('_')[0] == var.split('_')[0])]
            if not refs or nom in refs or 'remise' in nom:
                continue
            ref = tags[refs[0]]
            dif = {k: [ref.get(k), v] for k, v in t.items() if ref.get(k) != v and 'Date' not in k and 'Time' not in k}
            if dif:
                diffs[nom] = dif
        out[essai] = diffs
    ecrire('exif', out)
    return out


def bilan():
    out = {}
    for essai in ('index', 'balance', 'dr', 'ccnb', 'grain', 'bornes', 'balance2', 'expo', 'exif'):
        f = DOSSIER / f'{essai}.json'
        if f.exists():
            out[essai] = json.loads(f.read_text())
    SORTIE.write_text(json.dumps(out, indent=1, ensure_ascii=False))
    print(SORTIE)


if __name__ == '__main__':
    a = sys.argv[1:]
    if not a:
        print(__doc__)
        sys.exit(2)
    for etape in (['index', 'balance', 'dr', 'ccnb', 'grain', 'bornes', 'exif', 'bilan'] if a[0] == 'tout' else a):
        globals()[etape]()
        print('fini', etape, flush=True)
