#!/usr/bin/env python3
# SPDX-License-Identifier: CC-BY-NC-4.0
# Copyright (c) 2026 Thomas Hammoudi
"""Illustrations du traitement des couleurs du X-T4 : chaque réglage seul, à partir du Provia neutre, sur des photos sans
personne. Le boîtier développe chaque variante (xt4_banc.swift) ; les JPEG restent dans le chantier, hors du dépôt.

  python3 xt4_illustrations.py plan                 liste des rendus, sans boîtier
  python3 xt4_illustrations.py rendre               ce qui manque, balance de la prise de vue seulement
  python3 xt4_illustrations.py rendre --balance     ajoute les balances forcées (Kelvin, préréglages) : à la toute fin
  python3 xt4_illustrations.py figures              bandes légendées → recherche/figures/traitement-couleur/
  python3 xt4_illustrations.py mesures              balance, virage, plage dynamique chiffrés (sans boîtier) → donnees/

Passe par les gardes de xt4_recherche_v2 (rythme, rotation des sessions, sonde) ; un seul banc à la fois.

Variables : XT4_BANC (binaire compilé de xt4_banc.swift, hors du dépôt), XT4_CHANTIER (dossier lourd : RAF, cache, JPEG ;
par défaut <dossier temporaire>/xt4-mesure), XT4_RIB (clone du dépôt retro-ingenierie-boitiers). Les RAF de la séance
de validation sont lus dans xt4-validation/raf, le dossier frère de XT4_CHANTIER.
"""
import pathlib
import sys
import time

ICI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))
import xt4_recherche_v2 as v  # noqa: E402

xm = v.xm
SORTIE = xm.CHANTIER / 'illustrations'
VALID = xm.CHANTIER.parent / 'xt4-validation' / 'raf'
FIG = xm.FIGURES / 'traitement-couleur'
# photo : (RAF, plage dynamique de la prise de vue) ; aucune personne dans le cadre (vérifié à l'œil, 29/10/2026)
PHOTOS = {'florence': (VALID / '216-DSCF7918.RAF', 100), 'fleurs': (VALID / '207-DSCF0448.RAF', 100),
          'voiture': (xm.CHANTIER / 'raf' / '131-DSCF9386.RAF', 100), 'cascade': (xm.CHANTIER / 'raf' / '100-DSCF9267.RAF', 100),
          'mer': (VALID / '222-DSCF7442.RAF', 100), 'ville': (VALID / '323-DSCF7518.RAF', 200)}
# mesure seule, jamais en figure (photos de famille) : RAF pris en DR200 (324 : DR400), pour la plage dynamique
MESURE_DR = {f'mesure-{n}': (VALID / f'{n}.RAF', 400 if n.startswith('324') else 200) for n in
             ('301-DSCF8744', '302-DSCF8745', '305-DSCF8757', '309-DSCF8762', '321-DSCF0882', '322-DSCF7210', '323-DSCF7518',
              '324-DSCF1073')}
PHOTOS.update(MESURE_DR)
ORDRE_SIMS = [1, 2, 3, 11, 4, 5, 17, 16, 18, 12, 13, 14, 15, 6, 7, 8, 9, 10]
NOM_GRAIN = {1: 'sans grain', 2: 'faible, petit', 3: 'fort, petit', 4: 'faible, gros', 5: 'fort, gros'}
NOM_NIVEAU = {1: 'off', 2: 'faible', 3: 'fort'}


def signe(x):
    return f'{x:+g}'.replace('.', ',') if x else '0'


def variantes(balance=False):
    """[(groupe, photo, étiquette, recette)] ; chaque recette = Provia neutre + un réglage (DR de la prise de vue)."""
    out = []

    def a(groupe, photo, etiq, **ch):
        out.append((groupe, photo, etiq, v.normaliser(dict(xm.NEUTRE, dr=PHOTOS[photo][1], **ch))))
    for p in ('florence', 'fleurs', 'voiture'):
        for s in ORDRE_SIMS:
            a('simulations', p, xm.SIMS[s], sim=s)
    for p in ('florence', 'voiture'):
        for x in v.TONS:
            a('hautes', p, f'hautes lumières {signe(x)}', h=x)
            a('ombres', p, f'ombres {signe(x)}', s=x)
    for p in ('fleurs', 'florence'):
        for x in (-4, -2, 0, 2, 4):
            a('couleur', p, f'couleur {signe(x)}', couleur=x)
        for x in (1, 2, 3):
            a('color_chrome', p, f'Color Chrome {NOM_NIVEAU[x]}', cc=x)
    for p in ('florence', 'mer'):
        for x in (1, 2, 3):
            a('fx_blue', p, f'FX Blue {NOM_NIVEAU[x]}', ccb=x)
    for r in (-9, 0, 9):
        for b in (-9, 0, 9):
            a('decalage', 'voiture', f'R {signe(r)}, B {signe(b)}', wb_r=r, wb_b=b)
    for x in (-5, 0, 5):
        a('clarte', 'cascade', f'clarté {signe(x)}', clarte=x)
    for x in (-4, 0, 4):
        a('nettete', 'cascade', f'netteté {signe(x)}', nettete=x)
        a('bruit', 'cascade', f'réduction du bruit {signe(x)}', bruit=x)
    for g in NOM_GRAIN:
        a('grain', 'cascade', f'grain {NOM_GRAIN[g]}', grain=g)
    for k, x in (('mono_wc', -5), ('mono_wc', 5), ('mono_mg', -5), ('mono_mg', 5)):
        a('virage', 'florence', f"Acros, {'chaud/froid' if k == 'mono_wc' else 'magenta/vert'} {signe(x)}", sim=12, **{k: x})
    a('virage', 'florence', 'Acros', sim=12)
    # DR au plus celle de la prise de vue : un RAF pris en DR200 développé en DR400 sort vert (30/10/2026, ville : a* −37,
    # b* +33 en médiane, contre +1,0 / +0,4 en DR100 ; RAF 301 : −17 / +36), comme le fait aussi xt4_validation.dr
    for d in (x for x in (100, 200, 400) if x <= PHOTOS['ville'][1]):
        out.append(('dr', 'ville', f'DR{d}', v.normaliser(dict(xm.NEUTRE, dr=d))))
    for k in ('mono_wc', 'mono_mg'):                       # virage : a*, b* par cran (mesure, pas de figure)
        for x in (-9, -6, -3, 3, 6, 9):
            a('virage_mesure', 'florence', f'{k} {signe(x)}', sim=12, **{k: x})
    for m in MESURE_DR:                                    # plage dynamique sur des RAF pris en DR200 / 400 (mesure)
        for d in (x for x in (100, 200, 400) if x <= PHOTOS[m][1]):
            out.append(('dr_mesure', m, f'DR{d}', v.normaliser(dict(xm.NEUTRE, dr=d))))
        for q in (1, 2):
            out.append(('dr_mesure', m, f'priorité D-Range {q}', v.normaliser(dict(xm.NEUTRE, dr=PHOTOS[m][1], drp=q))))
    if balance:
        for k in (2500, 4000, 5500, 7500, 10000):
            a('balance', 'voiture', f'{k} K', wb=xm.WB['Temperature'], kelvin=k)
        for nom, w in (('Lumière du jour', 'Daylight'), ('Ombre', 'Shade'), ('Incandescent', 'Incand')):
            a('balance', 'voiture', nom, wb=xm.WB[w])
        a('balance', 'voiture', 'balance de la prise de vue (Auto)')
    return out


def chemin(photo, rec):
    return SORTIE / f'{photo}-{xm.cle(rec)}.jpg'


def plan(balance=False):
    vs = variantes(balance)
    uniques = {(p, xm.cle(r)) for _, p, _, r in vs}
    faits = sum(chemin(p, r).exists() for p, r in {(p, xm.cle(r)): (p, r) for _, p, _, r in vs}.values())
    print(f'{len(vs)} cases, {len(uniques)} rendus distincts, {faits} déjà faits')
    return vs


def rendre(balance=False):
    if balance:
        v.BALANCE_PERMISE = True          # Kelvin et préréglages : seulement à la toute fin (voir xt4_recherche_v2, blocages)
    vs = variantes(balance)
    (SORTIE / 'base').mkdir(parents=True, exist_ok=True)
    banc, n = None, 0
    t0 = time.time()
    try:
        for photo, (raf, _) in PHOTOS.items():
            manque = {xm.cle(r): r for _, p, _, r in vs if p == photo and not chemin(p, r).exists()}
            if not manque:
                continue
            if banc is None:
                banc = xm.Banc()
            base = SORTIE / 'base' / f'{photo}.bin'
            banc.charger(str(raf), str(base))
            b = base.read_bytes()
            for r in manque.values():
                pf, jp = SORTIE / 'profil.bin', chemin(photo, r)
                pf.write_bytes(xm.profil(b, r))
                q = jp.with_suffix('.part.jpg')
                banc.rendre(str(pf), str(q))
                q.rename(jp)
                n += 1
    finally:
        if banc:
            banc.fermer()
        v.journal(f'illustrations : {n} rendus en {(time.time() - t0) / 60:.1f} min')
    caracteriser()


def purs():
    """Les 18 simulations, tout le reste à 0 (Provia neutre) : la signature de chacune contre la scène (xt4_effets)."""
    return [v.normaliser(dict(xm.NEUTRE, sim=s)) for s in ORDRE_SIMS]


def caracteriser():
    """Chaque simulation pure sur les 16 RAF de la recherche, en moyennes de blocs (cache, pas de JPEG gardé)."""
    R = v.RendusV2()
    t0, n0 = time.time(), R.n_rendus
    try:
        R.lot_par_raf({n: purs() for n in v.TOUS})
    finally:
        R.fermer()
        v.journal(f'caractérisation des simulations : {R.n_rendus - n0} rendus en {(time.time() - t0) / 60:.1f} min')


def _tuile(jp, largeur):
    from PIL import Image, ImageOps
    im = ImageOps.exif_transpose(Image.open(jp)).convert('RGB')
    return im.resize((largeur, round(largeur * im.height / im.width)), Image.LANCZOS)


def _recadrage(jp, boite):
    from PIL import Image, ImageOps
    return ImageOps.exif_transpose(Image.open(jp)).convert('RGB').crop(boite)


def bande(cases, sortie, titre, colonnes=None, largeur=520, recadre=None):
    """Une figure : cases [(étiquette, jpeg)] en grille, chaque étiquette écrite dans l'image, sous la vignette."""
    from PIL import Image, ImageDraw
    colonnes = colonnes or len(cases)
    tuiles = [(e, _recadrage(j, recadre).resize((largeur, round(largeur * (recadre[3] - recadre[1]) / (recadre[2] - recadre[0]))),
                                                Image.LANCZOS) if recadre else _tuile(j, largeur)) for e, j in cases]
    h = max(t.height for _, t in tuiles)
    marge, haut_titre, haut_etiq = 14, 46, 34
    lignes = (len(tuiles) + colonnes - 1) // colonnes
    img = Image.new('RGB', (colonnes * (largeur + marge) + marge, haut_titre + lignes * (h + haut_etiq + marge)), 'white')
    d = ImageDraw.Draw(img)
    p1, p2 = xm._police(26), xm._police(20)
    d.text((marge, 10), titre, fill='black', font=p1)
    for i, (e, t) in enumerate(tuiles):
        x = marge + (i % colonnes) * (largeur + marge)
        y = haut_titre + (i // colonnes) * (h + haut_etiq + marge)
        img.paste(t, (x, y))
        while e and d.textlength(e, font=p2) > largeur:
            e = e[:-2] + '…'
        d.text((x, y + t.height + 6), e, fill='black', font=p2)
    FIG.mkdir(parents=True, exist_ok=True)
    img.save(FIG / sortie, quality=84, optimize=True, progressive=True)
    print(sortie, img.size)


def figures():
    vs = variantes(balance=True)
    par = {}
    for g, p, e, r in vs:
        if chemin(p, r).exists():
            par.setdefault((g, p), []).append((e, chemin(p, r)))
    titres = {'simulations': 'Simulations de film, tout le reste à 0 (Provia neutre, balance de la prise de vue)',
              'hautes': 'Hautes lumières, de −2 à +4', 'ombres': 'Ombres, de −2 à +4', 'couleur': 'Couleur, de −4 à +4',
              'color_chrome': 'Color Chrome Effect', 'fx_blue': 'Color Chrome FX Blue',
              'decalage': 'Décalage de balance : R en lignes, B en colonnes', 'clarte': 'Clarté (détail à 100 %)',
              'nettete': 'Netteté (détail agrandi 2 fois)', 'bruit': 'Réduction du bruit (détail agrandi 2 fois, ISO 800)',
              'grain': 'Grain (détail agrandi 2 fois)', 'virage': 'Virage monochrome (Acros)',
              'dr': 'Plage dynamique, sur un RAF pris en DR200', 'balance': 'Balance des blancs du profil'}
    # tuiles assez grandes pour une colonne de site (≈ 900 px) : 4 colonnes au plus en paysage, plus en portrait
    cols = {('simulations', 'fleurs'): 6, 'simulations': 4, 'decalage': 3, 'hautes': 4, 'ombres': 4, 'grain': 3,
            'virage': 3, ('couleur', 'fleurs'): 5, 'couleur': 3, 'bruit': 3, 'nettete': 3, 'clarte': 3}
    # détails de la cascade : rochers et mousse (tons moyens, où le grain se voit), agrandis 2 fois ; la clarté à 100 %
    recadres = {'clarte': (1300, 500, 1900, 900), 'grain': (2300, 650, 2600, 850), 'bruit': (2300, 650, 2600, 850),
                'nettete': (2300, 650, 2600, 850)}
    for (g, p), cases in par.items():
        if g not in titres or p.startswith('mesure-'):   # mesures seules : jamais en figure
            continue
        if len(cases) < 2:              # balance : rien à comparer tant que les Kelvin ne sont pas rendus
            continue
        rec = recadres.get(g) if p == 'cascade' else None
        larg = 600 if rec else (420 if (g, p) == ('simulations', 'fleurs') or (g, p) == ('couleur', 'fleurs') else 520)
        bande(cases, f'{g}-{p}.jpg', titres[g], cols.get((g, p), cols.get(g)), larg, rec)


def mesures():
    """Chiffres de la doc tirés des JPEG du chantier, sans boîtier : balance du profil contre Auto (voiture), virage cran par
    cran (Acros, florence), plage dynamique sur les RAF pris en DR200 / 400 (dont la vue de ville de la figure). Moyennes de
    blocs de 16 px sur l'image entière, Lab D65 → donnees/xt4-illustrations-mesures-<DATE>.json."""
    import json
    import numpy as np
    dm = v.dm
    vs = variantes(balance=True)
    memo = {}

    def lab(p, r):
        k = (p, xm.cle(r))
        if k not in memo:
            jp = chemin(p, r)
            memo[k] = dm.code_lab(xm.moyennes_blocs(xm.jpeg(jp))[0] / 255) if jp.exists() else None
        return memo[k]

    def med(x):
        return round(float(np.median(x)), 2) if len(x) >= 20 else None
    par = {}
    for g, p, e, r in vs:
        par.setdefault((g, p), []).append((e, r))
    out = {'date': v.DATE, 'methode': mesures.__doc__.split('\n')[0]}
    # balance : chaque réglage contre la balance de la prise de vue, sur toute l'image et sur les blocs neutres du rendu Auto
    cases = dict(par.get(('balance', 'voiture'), []))
    ref = lab('voiture', cases['balance de la prise de vue (Auto)']) if 'balance de la prise de vue (Auto)' in cases else None
    if ref is not None:
        neutres = np.hypot(ref[:, 1], ref[:, 2]) < 8
        out['balance'] = {}
        for e, r in cases.items():
            L = lab('voiture', r)
            if L is None or e.startswith('balance de la prise'):
                continue
            d = L - ref
            out['balance'][e] = {'image': {'dL': med(d[:, 0]), 'da': med(d[:, 1]), 'db': med(d[:, 2])},
                                 'neutres': {'blocs': int(neutres.sum()), 'a': med(L[neutres, 1]), 'b': med(L[neutres, 2]),
                                             'a_auto': med(ref[neutres, 1]), 'b_auto': med(ref[neutres, 2])}}
    # virage : a*, b* de l'image en Acros (tons moyens), par cran
    acros = lab('florence', v.normaliser(dict(xm.NEUTRE, sim=12)))
    if acros is not None:
        m = (acros[:, 0] > 20) & (acros[:, 0] < 90)
        out['virage'] = {'Acros': {'a': med(acros[m, 1]), 'b': med(acros[m, 2])}}
        for e, r in par.get(('virage_mesure', 'florence'), []) + par.get(('virage', 'florence'), []):
            L = lab('florence', r)
            if L is not None and e != 'Acros':
                out['virage'][e] = {'a': med(L[m, 1]), 'b': med(L[m, 2]), 'dL': med(L[m, 0] - acros[m, 0])}
    # plage dynamique : chaque RAF développé à DR100 / 200 / 400 et en priorité D-Range, contre son développement à la DR de la
    # prise de vue ; tranches de clarté de ce dernier
    bords = [0, 15, 30, 45, 60, 75, 90, 101]
    out['plage_dynamique'] = {}
    for p in [x for x in PHOTOS if x.startswith('mesure-')] + ['ville']:
        g = 'dr' if p == 'ville' else 'dr_mesure'
        cases = dict(par.get((g, p), []))
        dr0 = PHOTOS[p][1]
        r0 = cases.get(f'DR{dr0}')
        L0 = lab(p, r0) if r0 else None
        if L0 is None:
            continue
        x = {'dr_prise_de_vue': dr0, 'figure': p == 'ville', 'blocs': int(len(L0))}
        for e, r in cases.items():
            L = lab(p, r)
            if L is None:
                continue
            x[e] = {'L_median': med(L[:, 0]), 'blancs_L97': round(float((L[:, 0] > 97).mean()), 4),
                    'noirs_L5': round(float((L[:, 0] < 5).mean()), 4)}
            if e != f'DR{dr0}':
                x[e]['dL_par_tranche'] = {f'{a}-{min(b, 100)}': med(L[(L0[:, 0] >= a) & (L0[:, 0] < b), 0] - L0[(L0[:, 0] >= a) & (L0[:, 0] < b), 0])
                                          for a, b in zip(bords[:-1], bords[1:])}
        out['plage_dynamique'][p.replace('mesure-', '')] = x
    f = xm.DONNEES / f'xt4-illustrations-mesures-{v.DATE}.json'
    f.write_text(json.dumps(out, indent=1, ensure_ascii=False))
    print(f.name, {k: len(x) for k, x in out.items() if isinstance(x, dict)})


if __name__ == '__main__':
    a = sys.argv[1:]
    if a[:1] == ['plan']:
        plan('--balance' in a)
    elif a[:1] == ['rendre']:
        rendre('--balance' in a)
    elif a[:1] == ['figures']:
        figures()
    elif a[:1] == ['mesures']:
        mesures()
    else:
        print(__doc__)
        sys.exit(2)
