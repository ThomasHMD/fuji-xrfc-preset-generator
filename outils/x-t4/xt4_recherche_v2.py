#!/usr/bin/env python3
# SPDX-License-Identifier: CC-BY-NC-4.0
# Copyright (c) 2026 Thomas Hammoudi
"""Deuxième passe des recettes JPEG du X-T4 (29/10/2026), le boîtier développant lui-même les RAF (xt4_banc.swift).
Voir docs/methode.md. Ce qui change depuis la première passe (xt4_mesure) :
- scène : xt4_scene (matrice ajustée sur les mires du X-T3 et du X-T30), blocs convertis par xt4_scene.convertir_blocs
  (mêmes blocs, donc les rendus déjà gardés en cache restent valables) ;
- cibles : xt4_cibles (celles du D750) : trix, hp5, fp4, portra, classic_chrome et ses trois variantes de goût ;
- balance : en N&B, la balance en Kelvin (2 500 à 10 000 K, index 11 du profil à 0) est une coordonnée de la recherche,
  contre la balance de la prise de vue ; en couleur, balance de la prise de vue (les cibles supposent un blanc adapté) ;
- exposition à la prise de vue (consigne, C1-C7 ne la gardent pas) : l'index 4 du profil est sans effet à la conversion
  (mesuré), elle est donc simulée côté cible : une vue surexposée de e IL rend T(RAW × 2^e) ; on note T(RAW) contre la
  cible de la scène assombrie de e IL, ce qui revient au même hors écrêtage (hypothèse : écrêtage non compté) ;
- validation : trois recherches complètes par look, sur la moitié A, sur la moitié B, sur les 16 RAF ; la recette
  cherchée sur A est notée sur B et l'inverse ; les recettes de 2022 sont notées sur les mêmes moitiés.

  xt4_recherche_v2.py existantes        les 161 .FP1 de 2022 rendus sur les 16 RAF (leur balance appliquée)
  xt4_recherche_v2.py chercher nb       Tri-X, HP5, FP4 (9 recherches menées ensemble : rendus partagés)
  xt4_recherche_v2.py chercher couleur  Portra, Classic Chrome et ses trois variantes (15 recherches)
  xt4_recherche_v2.py bilan             notes sur A, B, 16, contrôle croisé, recettes de 2022 → donnees/
  xt4_recherche_v2.py grain             σ de L* ajouté par chaque grain, au cercle de 48 µm
  xt4_recherche_v2.py livrer            .FP1 « TH … » dans presets/recettes-2026/
  xt4_recherche_v2.py controle          les .FP1 livrés relus et rendus tels quels
  xt4_recherche_v2.py planches          cible, meilleure recette de 2022, nouvelle (colonnes nommées dans l'image)
  xt4_recherche_v2.py etat              où en est la recherche (sans le boîtier)

Variables : XT4_BANC (binaire de xt4_banc.swift, hors du dépôt), XT4_CHANTIER (dossier lourd, hors du dépôt), XT4_RIB (clone du
dépôt retro-ingenierie-boitiers), XT4_TRANSFERT (0 : descente complète, sans pré-tri). Un seul banc ouvert à la fois.
"""
import concurrent.futures as cf
import json
import pathlib
import sys
import time
from collections import defaultdict

import numpy as np

ICI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))
import xt4_mesure as xm  # noqa: E402
import xt4_scene as xs  # noqa: E402
import xt4_cibles as xc  # noqa: E402

DATE = '2026-10-29'
V2 = xm.CHANTIER / 'v2'
SORTIE = xm.DONNEES / f'xt4-recettes-v2-{DATE}.json'
NB = ('trix', 'hp5', 'fp4')
COULEUR = ('portra', 'classic_chrome', 'cc_115', 'cc_130', 'cc_130_contraste')
COULEUR2 = ('provia', 'ektar', 'fp400h', 'velvia', 'ektachrome', 'kodachrome')   # seconde série, ordre de l'auteur
LOOKS = NB + COULEUR + COULEUR2
GROUPES = {'nb': NB, 'couleur': COULEUR, 'couleur2': COULEUR2}
E3 = list(range(-3, 6))                      # exposition à la prise de vue, en tiers d'IL (−1 à +5/3)
KELVINS = [0, 2500, 3200, 4000, 5000, 6500, 8000, 10000]   # 0 : balance de la prise de vue
TONS = list(range(-2, 5))
DECALAGES = [-9, -6, -3, 0, 3, 6, 9]
# Kelvin retiré de la recherche le 29/10/2026 à 17:00 : trois blocages du boîtier (15:30, 15:58, 16:52), tous pendant ou après
# des rendus à balance forcée (index 11 à 0) ; la première passe, sans balance forcée, avait tenu plus de 5 000 conversions.
# Hypothèse (à confirmer par la suite) : fuite du firmware quand la balance du profil est forcée. Le Kelvin n'est plus essayé
# qu'à la toute fin, en duel borné (kelvin_duel), et n'entre dans un .FP1 que s'il gagne au moins 0,3 hors échantillon.
DOM_NB = {'sim': [12, 13, 14, 15, 6, 7, 8, 9], 'h': TONS, 's': TONS, 'wb_r': DECALAGES, 'wb_b': DECALAGES, 'e3': E3}
BALANCE_PERMISE = False      # garde : aucun profil à balance forcée n'est envoyé au boîtier, sauf dans kelvin_duel
KELVINS_DUEL = [3200, 4000, 5000, 6500]
SEUIL_KELVIN = 0.3
DOM_COUL = {'sim': [17, 5, 4, 3, 1, 11, 16, 2], 'h': TONS, 's': TONS, 'couleur': list(range(-4, 5)), 'wb_r': DECALAGES,
            'wb_b': DECALAGES, 'cc': [1, 2, 3], 'ccb': [1, 2, 3], 'e3': E3}
CLARTES = [-2, 2, 4]
FP1_NOMS = {'trix': 'TH Tri-X 400', 'hp5': 'TH HP5 Plus', 'fp4': 'TH FP4 Plus', 'portra': 'TH Portra 400',
            'classic_chrome': 'TH Classic Chrome', 'cc_115': 'TH Classic Chrome 1.15', 'cc_130': 'TH Classic Chrome 1.3',
            'cc_130_contraste': 'TH CC 1.3 contraste', 'provia': 'TH Provia 100F', 'ektar': 'TH Ektar 100',
            'fp400h': 'TH Pro 400H', 'velvia': 'TH Velvia 100', 'ektachrome': 'TH Ektachrome E100', 'kodachrome': 'TH Kodachrome 64'}          # 25 caractères ASCII au plus (nom d'emplacement du X-T4)
SEUIL_EXPO = 0.05   # hors HP5, dans la recherche : une exposition ne bouge que si elle gagne au moins 0,05 au critère
SEUIL_EXPO_HORS = 0.3   # hors HP5, au bilan : consigne gardée seulement si elle gagne au moins 0,3 hors échantillon (moyenne
                        # des deux sens du contrôle croisé, contre la même recherche menée à exposition 0)
# recettes de 2022 « faites pour » chaque look (planches) ; sinon la meilleure de sa famille
_CC = r'(?<!koda)(?<!ekta)(?<!elite )chrome'
NOMMEES = {'trix': r'tri-?x', 'hp5': r'hp-?5', 'fp4': r'fp4', 'portra': r'portra(?!it)|porta\b',
           'classic_chrome': _CC, 'cc_115': _CC, 'cc_130': _CC, 'cc_130_contraste': _CC,
           'provia': r'provia|sensia', 'ektar': r'ektar', 'fp400h': r'400h', 'velvia': r'velvia|valvia',
           'ektachrome': r'ektachrome|elite chrome', 'kodachrome': r'kodachrome'}
dm = xm._dm()

# ---------------------------------------------------------------------------------------------------------------
# Scène et cibles de la deuxième passe
# ---------------------------------------------------------------------------------------------------------------
_charger_v1 = xm.charger_blocs
_BLOCS = {}


def charger_blocs_v2():
    if not _BLOCS:
        _BLOCS.update({n: xs.convertir_blocs(d) for n, d in _charger_v1().items()})
    return _BLOCS


xm.charger_blocs = charger_blocs_v2          # Rendus, xt4_cibles.cibles et scene_image passent par là
xm.lineaire = xs.lineaire                    # images entières des planches (image_cible)
TOUS = sorted(n.stem for n in (xm.CHANTIER / 'blocs').glob('*.npz'))
A = list(xm.RECHERCHE)
B = [n for n in TOUS if n not in A]
CIB, SC, Y18 = {}, {}, None


def cibles():
    global Y18
    if CIB:
        return
    Y18 = json.loads((xm.CHANTIER / 'etalonnage.json').read_text())['y18']
    fs = {l: xc.fonction(l) for l in LOOKS}
    for l in LOOKS:
        CIB[l] = {e: {} for e in E3}
    for n, d in charger_blocs_v2().items():
        _, X = xm.scene(d, Y18)
        SC[n] = dm.xyz_lab(X)
        for l, f in fs.items():
            for e in E3:
                CIB[l][e][n] = f(X * 2.0 ** (-e / 3))


def journal(msg):
    V2.mkdir(parents=True, exist_ok=True)
    print(msg, flush=True)
    with open(V2 / 'recherche-v2.log', 'a', encoding='utf-8') as f:
        f.write(time.strftime('%H:%M:%S ') + msg + '\n')


# ---------------------------------------------------------------------------------------------------------------
# Banc gardé (29/10/2026, après deux blocages du boîtier vers 1 500 et 2 000 rendus d'affilée, voyant vert et orange) :
# - rythme plancher de 0,7 s par conversion (celui de la première passe, qui a tenu 5 323 rendus) ;
# - toutes les 250 conversions : session fermée, 60 s de pause, sonde (xt4_recettes sonde, lecture seule), session rouverte ;
# - objets du boîtier comptés après chaque rendu (xt4_banc : « objets=… fup=… ») : arrêt si le compte monte ;
# - envois de RAF comptés par session, écrits au journal ;
# - toute erreur du banc : session fermée, 120 s, sonde ; si elle répond, session rouverte et même commande refaite une seule
#   fois ; sinon, ou si la commande refaite échoue encore, arrêt (l'état de la recherche est sauvé à chaque paramètre).
# ---------------------------------------------------------------------------------------------------------------
RYTHME_S, SESSION_MAX, PAUSE_SESSION_S, ATTENTE_S, REPRISES_MAX, OBJETS_MARGE = 0.7, 250, 60, 120, 3, 3


class ArretBanc(RuntimeError):
    """Arrêt voulu (compte d'objets en hausse, sonde muette) : jamais repris."""


class BancGarde(xm.Banc):
    conversions = 0
    reprises = 0

    def __init__(self, exe=None):
        self.exe = exe
        self._ouvrir()

    def _ouvrir(self):
        super().__init__(self.exe)
        self.n_session, self.envois, self.objets_base, self.t_dernier = 0, 0, None, 0.0
        self.dernier = getattr(self, 'dernier', None)
        self.en_reprise = getattr(self, 'en_reprise', False)

    def _fermer_session(self, motif):
        try:
            self.fermer(motif)
        except Exception:  # noqa: BLE001
            self.p.kill()
            self.p.wait(timeout=10)

    def _champs(self, r):
        return dict(x.split('=', 1) for x in r.split() if '=' in x)

    def _surveiller(self, r):
        c = self._champs(r)
        if 'objets' not in c:
            return
        n = int(c['objets'])
        if self.objets_base is None:
            self.objets_base = n
        elif n > self.objets_base + OBJETS_MARGE:
            raise ArretBanc(f"objets du boîtier en hausse : {n} contre {self.objets_base} à l'ouverture ({r}) : arrêt avant blocage")
        if c.get('effacement', '0x2001') != '0x2001':
            journal(f'banc : effacement du JPEG refusé ({r})')

    def _cmd(self, *champs):
        if champs[0] == 'fin':
            return super()._cmd(*champs)
        try:
            r = super()._cmd(*champs)
        except ArretBanc:
            raise
        except (RuntimeError, OSError) as e:
            if self.en_reprise or BancGarde.reprises >= REPRISES_MAX:
                raise
            self.en_reprise = True
            BancGarde.reprises += 1
            journal(f'{e} ({champs[0]}) : reprise {BancGarde.reprises}/{REPRISES_MAX} du processus : session fermée, {ATTENTE_S} s, sonde')
            self._fermer_session('erreur')
            time.sleep(ATTENTE_S)
            if not sonde():
                raise ArretBanc(f'{e} ; sonde muette après {ATTENTE_S} s : arrêt, état sauvé') from e
            self._ouvrir()
            if champs[0] == 'rendre' and self.dernier:
                self.charge = None
                super().charger(*self.dernier)
            r = super()._cmd(*champs)                 # une seule fois : une nouvelle erreur remonte et arrête tout
            self.en_reprise = False
            journal('reprise réussie : même commande refaite')
        if champs[0] == 'charger':
            self.envois += 1
            c = self._champs(r)
            if self.envois == 1 or self.envois % 50 == 0 or c.get('fup_effaces', '0') != '0' or c.get('codes'):
                journal(f'banc : envoi de RAF n° {self.envois} de la session ({r})')
        elif champs[0] == 'rendre' and (self.n_session <= 3 or self.n_session % 100 == 0):
            journal(f'banc : conversion n° {self.n_session} de la session ({r})')
        self._surveiller(r)
        return r

    def charger(self, raf, base):
        self.dernier = (raf, base)
        super().charger(raf, base)

    def rendre(self, prof, jpg):
        if self.n_session >= SESSION_MAX:
            self._fermer_session('rotation')
            time.sleep(PAUSE_SESSION_S)
            if not sonde():
                raise ArretBanc(f'sonde muette après la pause de {PAUSE_SESSION_S} s : arrêt, état sauvé')
            self._ouvrir()
            if self.dernier:
                super().charger(*self.dernier)
        attente = RYTHME_S - (time.time() - self.t_dernier)
        if attente > 0:
            time.sleep(attente)
        self.t_dernier = time.time()
        BancGarde.conversions += 1
        self.n_session += 1
        return super().rendre(prof, jpg)

    def fermer(self, motif='fin'):
        journal(f'banc : session fermée ({motif}) après {self.n_session} conversions et {self.envois} envois de RAF')
        super().fermer()


def sonde():
    """xt4_recettes sonde (lecture seule : la liste blanche de l'outil refuse toute écriture) : le boîtier répond-il, en mode 6 ?"""
    import subprocess
    exe = pathlib.Path(xm.BANC or '').with_name('xt4_recettes')
    try:
        sortie = V2 / 'sondes' / time.strftime('%Y%m%d-%H%M%S')          # journaux de la sonde hors du dépôt
        r = subprocess.run([str(exe), 'sonde', '--sortie', str(sortie)], capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.TimeoutExpired) as e:
        journal(f'sonde : {e}')
        return False
    t = r.stdout + r.stderr
    # code 0 : tout est là ; 4 : boîtier joint mais un prérequis d'écriture des recettes manque (sans objet ici) ; 1 : absent
    ok = r.returncode in (0, 4) and not any(x in t for x in ('Aucun X-T4', 'Session refusée', 'Mode USB différent', 'pas un X-T4'))
    journal(f"sonde : code {r.returncode}, {'répond' if ok else 'muet'} ; " + ' / '.join(t.strip().splitlines()[-2:])[:300])
    return ok


xm.Banc = BancGarde        # xt4_mesure (Rendus, preparer) et xt4_validation passent tous par xm.Banc


# ---------------------------------------------------------------------------------------------------------------
# Rendus : la mesure d'un JPEG se fait pendant que le boîtier rend le suivant
# ---------------------------------------------------------------------------------------------------------------
class RendusV2(xm.Rendus):
    def lot_par_raf(self, besoin):
        """besoin : {raf: [recettes]} ; rend ce qui manque au cache, RAF par RAF."""
        tmp = V2 / 'tmp'
        tmp.mkdir(parents=True, exist_ok=True)
        for n, recs in besoin.items():
            manque = list({xm.cle(r): r for r in recs if not self.chemin(n, r).exists()}.values())
            if not manque:
                continue
            if self.banc is None:
                self.banc = xm.Banc(self.banc_exe)
            (self.cache / n).mkdir(exist_ok=True)
            base = xm.CHANTIER / 'base' / f'{n}.bin'
            t0 = time.time()
            self.banc.charger(self.blocs[n]['raf'], str(base))
            b = base.read_bytes()
            futs = [None] * 4
            with cf.ThreadPoolExecutor(2) as ex:
                for i, r in enumerate(manque):
                    k = i % 4
                    if futs[k] is not None:
                        futs[k].result()
                    pf, jp = tmp / 'profil.bin', tmp / f'rendu{k}.jpg'
                    pf.write_bytes(xm.profil(b, r))
                    if jp.exists():
                        jp.unlink()
                    self.banc.rendre(str(pf), str(jp))
                    self.n_rendus += 1
                    futs[k] = ex.submit(self._mesurer, n, r, jp)
                for f in futs:
                    if f is not None:
                        f.result()
            self.t_banc += time.time() - t0

    def _mesurer(self, n, r, jp):
        m, _ = xm.moyennes_blocs(xm.jpeg(jp), self.blocs[n]['idx'])
        p = self.chemin(n, r)
        q = p.with_suffix('.part.npy')
        np.save(q, m.astype(np.float32))
        q.rename(p)


_LAB = {}


def lab(R, n, r):
    k = (n, xm.cle(r))
    v = _LAB.get(k)
    if v is None:
        if len(_LAB) > 8000:
            _LAB.clear()
        v = _LAB[k] = dm.code_lab(R.moyennes(n, r) / 255)
    return v


def ecarts(R, look, e3, r, noms):
    out = {}
    for n in noms:
        L, T = lab(R, n, r), CIB[look][e3][n]
        out[n] = np.abs(L[:, 0] - T[:, 0]) if look in NB else dm.de2000(L, T)
    return out


def note(R, look, e3, r, noms):
    return xm.resume(ecarts(R, look, e3, r, noms))


# ---------------------------------------------------------------------------------------------------------------
# Recettes : forme, texte
# ---------------------------------------------------------------------------------------------------------------
def normaliser(r):
    r = dict(r)
    for k in ('h', 's', 'couleur', 'clarte', 'nettete'):
        if k in r and r[k] is not None:
            v = float(r[k])
            r[k] = int(v) if v.is_integer() else v
    for k in ('wb_r', 'wb_b', 'sim', 'cc', 'ccb', 'grain', 'dr', 'drp', 'wb', 'bruit'):
        if k in r and r[k] is not None:
            r[k] = int(r[k])
    return r


def avec(r, p, v):
    r = dict(r)
    if p == 'k':
        if v:
            r['wb'], r['kelvin'] = xm.WB['Temperature'], int(v)
        else:
            r['wb'] = 0
            r.pop('kelvin', None)
    else:
        r[p] = v
    return normaliser(r)


def kelvin(r):
    return r.get('kelvin', 0) if r.get('wb') == xm.WB['Temperature'] else 0


def pour_recherche(r, look):
    """Point de départ tiré d'une recette : grain coupé, DR100, netteté, bruit, clarté et virage à 0, balance de la prise de
    vue (aucune balance forcée depuis le 29/10 17:00)."""
    m = {k: v for k, v in r.items() if k not in ('nom', 'source', 'mono_wc', 'mono_mg')}
    m.update(grain=1, dr=100, drp=0, nettete=0, bruit=0, clarte=0)
    if look in NB:
        m['couleur'] = 0
    m['wb'] = 0
    m.pop('kelvin', None)
    return normaliser(m)


def sans_balance(r):
    """Une recette de 2022 rendue à la balance de la prise de vue (planches, lot varié) : la sienne n'est plus forcée."""
    if not r.get('wb'):
        return r, False
    m = dict(r, wb=0)
    m.pop('kelvin', None)
    return m, True


_profil = xm.profil


def profil_garde(base, rec):
    if not BALANCE_PERMISE and (rec.get('wb') or (rec.get('brut') or {}).get(11) == 0):
        raise ArretBanc(f'profil à balance forcée refusé par la garde (BALANCE_PERMISE) : {rec}')
    return _profil(base, rec)


xm.profil = profil_garde


def pour_mesure_v2(p):
    """Une recette de 2022 telle qu'on la mesure : grain coupé, DR100 (DR200/400 et priorité D-Range virent au vert sur
    un RAF pris en DR100), sa balance appliquée (index 11 à 0), sauf Auto = balance de la prise de vue (RAF en Auto)."""
    m = {k: v for k, v in p.items() if k not in ('nom', 'source')}
    m.update(grain=1, dr=100, drp=0)
    if m['wb'] in (0, xm.WB['Auto']):
        m['wb'] = 0
        m.pop('kelvin', None)
    return m


def texte(r, e3=0):
    t = [xm.SIMS[r['sim']], f"H {r.get('h', 0):+g} S {r.get('s', 0):+g}"]
    if r['sim'] not in xm.SIMS_MONO:
        t.append(f"couleur {r.get('couleur', 0):+g}")
    k = kelvin(r)
    if k:
        t.append(f'{k} K')
    elif r.get('wb'):
        t.append(xm.WB_NOM.get(r['wb'], str(r['wb'])))
    t.append(f"R{r.get('wb_r', 0):+d} B{r.get('wb_b', 0):+d}")
    if r.get('cc', 1) != 1 or r.get('ccb', 1) != 1:
        t.append(f"CC {xm.NIVEAU[r.get('cc', 1)].lower()} / FX bleu {xm.NIVEAU[r.get('ccb', 1)].lower()}")
    if r.get('clarte', 0):
        t.append(f"clarté {r['clarte']:+g}")
    if e3:
        t.append(f'exposer {tiers(e3)} IL')
    return ', '.join(t)


def tiers(e3):
    s = '+' if e3 > 0 else '−'
    a, b = divmod(abs(e3), 3)
    return s + (f'{a}' if a else '') + (' ' if a and b else '') + (f'{b}/3' if b else '') if e3 else '0'


# ---------------------------------------------------------------------------------------------------------------
# Recettes de 2022
# ---------------------------------------------------------------------------------------------------------------
def presets():
    out = {}
    for p in sorted(xm.PRESETS.glob('*.FP1')):
        r = xm.lire_fp1(p)
        out[r['nom']] = {'source': p.name, 'nb': r['sim'] in xm.SIMS_MONO, 'brute': r, 'rec': pour_mesure_v2(r)}
    return out


def existantes():
    P = presets()
    R = RendusV2()
    try:
        R.lot_par_raf({n: [p['rec'] for p in P.values()] for n in TOUS})
    finally:
        R.fermer()
    journal(f'existantes v2 : {len(P)} recettes, {R.n_rendus} rendus, {R.t_banc / 60:.1f} min')


# ---------------------------------------------------------------------------------------------------------------
# Recherche : départ, descente coordonnée par coordonnée, raffinements, clarté ; plusieurs recherches menées ensemble
# ---------------------------------------------------------------------------------------------------------------
def dom(o):
    """Domaine de la recherche ; une recherche peut porter le sien (xt4_relance_fx : FX Blue fixé, sans exposition)."""
    return o.get('dom') or (DOM_NB if o['look'] in NB else DOM_COUL)


TRANSFERT = __import__('os').environ.get('XT4_TRANSFERT', '1') == '1'   # pré-tri de xt4_transfert.py (29/10, 18:30)


def evaluer(R, objs, props, seuil=1e-3):
    """Rend ce qui manque, puis garde pour chaque recherche la meilleure proposition qui bat la sienne d'au moins seuil
    (SEUIL_EXPO pour une nouvelle consigne d'exposition hors HP5). Par défaut, pré-tri par transfert (xt4_transfert.py :
    propositions rendues sur 3 RAF, les autres prédits, seules les 2 meilleures rendues partout) ; XT4_TRANSFERT=0 : tout
    rendre partout."""
    if TRANSFERT:
        import xt4_transfert
        return xt4_transfert.evaluer(sys.modules[__name__], R, objs, props, seuil)
    besoin = defaultdict(dict)
    for o in objs:
        for r, _ in props.get(o['id'], []):
            for n in o['noms']:
                besoin[n][xm.cle(r)] = r
    R.lot_par_raf({n: list(d.values()) for n, d in besoin.items()})
    for o in objs:
        for r, e3 in props.get(o['id'], []):
            s = note(R, o['look'], e3, r, o['noms'])['score']
            sl = max(seuil, SEUIL_EXPO) if e3 != o['e3'] and o['look'] != 'hp5' else seuil
            if s < o['s'] - sl:
                o.update(rec=r, e3=e3, s=s, bouge=True)


def proposer(o, p, vals):
    out = []
    for v in vals:
        if p == 'e3':
            if v != o['e3'] and not o.get('e3_fixe'):
                out.append((o['rec'], v))
        elif p == 'k':
            if v != kelvin(o['rec']):
                out.append((avec(o['rec'], 'k', v), o['e3']))
        elif o['rec'].get(p) != v:
            out.append((avec(o['rec'], p, v), o['e3']))
    return out


def ecrire_atomique(chemin, texte):
    t = chemin.with_name(chemin.name + '.part')
    t.write_text(texte)
    t.replace(chemin)


def sauver(objs, groupe):
    ecrire_atomique(V2 / f'etat-{groupe}.json', json.dumps(objs, indent=1, ensure_ascii=False, default=float))


def log_etape(R, groupe, etape, objs):
    journal(f'{groupe} {etape} [{R.n_rendus} rendus, {R.t_banc / 60:.1f} min] ' +
            ' | '.join(f"{o['id']} {o['s']:.3f}" for o in objs))


def descente(R, objs, groupe, tours=2, actifs=None):
    actifs = list(objs if actifs is None else actifs)
    for t in range(tours):
        for o in actifs:
            o['bouge'] = False
        for p in ('sim', 'h', 's', 'couleur', 'wb_r', 'wb_b', 'k', 'cc', 'ccb', 'e3'):
            props = {o['id']: proposer(o, p, dom(o)[p]) for o in actifs if p in dom(o)}
            if props:
                evaluer(R, actifs, props)
                log_etape(R, groupe, f'tour {t + 1} {p}', objs)
                sauver(objs, groupe)
        actifs = [o for o in actifs if o['bouge']]
        if not actifs:
            break


def raffiner(R, objs, groupe, actifs=None):
    actifs = objs if actifs is None else actifs
    for a, b, pas, (lo, hi) in (('h', 's', 0.5, (-2, 4)), ('wb_r', 'wb_b', 1, (-9, 9))):
        props = {}
        for o in actifs:
            r, L = o['rec'], []
            for da in (-1, 0, 1):
                for db in (-1, 0, 1):
                    va, vb = r.get(a, 0) + da * pas, r.get(b, 0) + db * pas
                    if (da or db) and lo <= va <= hi and lo <= vb <= hi:
                        L.append((avec(avec(r, a, va), b, vb), o['e3']))
            props[o['id']] = L
        evaluer(R, objs, props)
        log_etape(R, groupe, f'raffinement {a}×{b}', objs)
    props = {o['id']: [(avec(o['rec'], 'k', k), o['e3']) for k in (kelvin(o['rec']) + d for d in (-400, -200, 200, 400))
                       if 2500 <= k <= 10000] for o in actifs if kelvin(o['rec'])}
    if props:
        evaluer(R, objs, props)
        log_etape(R, groupe, 'raffinement Kelvin', objs)
    sauver(objs, groupe)


def clarte(R, objs, groupe, actifs=None):
    """Clarté essayée à la fin (1,6 s par rendu au boîtier), gardée seulement si elle gagne au moins 0,05 au critère."""
    actifs = objs if actifs is None else actifs
    evaluer(R, objs, {o['id']: [(avec(o['rec'], 'clarte', c), o['e3']) for c in CLARTES] for o in actifs}, seuil=0.05)
    log_etape(R, groupe, 'clarté', objs)
    sauver(objs, groupe)


def departs(R, looks):
    """Pour chaque look et chaque moitié : la meilleure, au critère (à sa meilleure exposition pour la HP5), des recettes de 2022
    de la famille (déjà rendues), de la recette de la première passe et des simulations neutres ; ramenée à la forme de
    recherche (grain, netteté, bruit, clarté à 0)."""
    P = presets()
    v1 = json.loads((xm.CHANTIER / 'meilleures.json').read_text())
    objs = []
    for look in looks:
        nb = look in NB
        cands = {k: p['rec'] for k, p in P.items() if p['nb'] == nb}
        if look in v1:
            cands['première passe'] = v1[look]['recette']
        for sim in ([12, 6] if nb else [1, 11, 3]):
            cands[f'{xm.SIMS[sim]} neutre'] = dict(xm.NEUTRE, sim=sim)
        R.lot_par_raf({n: list(cands.values()) for n in TOUS})
        for moitie, noms in (('A', A), ('B', B), ('16', TOUS)):
            es = E3 if look == 'hp5' else [0]
            best = min(((note(R, look, e, r, noms)['score'], k, e) for k, r in cands.items() for e in es))
            r = pour_recherche(cands[best[1]], look)
            objs.append({'id': f'{look}@{moitie}', 'look': look, 'moitie': moitie, 'noms': noms, 'rec': r, 'e3': best[2],
                         'depart': best[1], 's': None})
    R.lot_par_raf({n: [o['rec'] for o in objs if n in o['noms']] for n in TOUS})
    for o in objs:
        o['s'] = note(R, o['look'], o['e3'], o['rec'], o['noms'])['score']
        journal(f"départ {o['id']} : {o['depart']} → {texte(o['rec'], o['e3'])} ({o['s']:.3f})")
    return objs


def chercher(groupe):
    cibles()
    looks = GROUPES.get(groupe) or tuple(groupe.split(','))
    R = RendusV2()
    f = V2 / f'etat-{groupe}.json'
    try:
        if f.exists():
            objs = json.loads(f.read_text())
            journal(f'{groupe} : reprise de {f.name}')
            migres = [o for o in objs if o['rec'].get('wb')]
            if migres:
                for o in migres:
                    o['rec'] = avec(o['rec'], 'k', 0)
                    o['depart'] = f"{o.get('depart')} ; Kelvin retiré le 29/10 (balance de la prise de vue)"
                R.lot_par_raf({n: [o['rec'] for o in migres if n in o['noms']] for n in TOUS})
                for o in migres:
                    o['s'] = note(R, o['look'], o['e3'], o['rec'], o['noms'])['score']
                ecrire_atomique(V2 / f'etapes-{groupe}.json', '[]')      # descente refaite sans Kelvin (rendus déjà faits : cache)
                sauver(objs, groupe)
                journal(f"{groupe} : Kelvin retiré de {', '.join(o['id'] + ' (' + format(o['s'], '.3f') + ')' for o in migres)}")
        else:
            objs = departs(R, looks)
            sauver(objs, groupe)
        faits = set(json.loads((V2 / f'etapes-{groupe}.json').read_text())) if (V2 / f'etapes-{groupe}.json').exists() else set()
        def raffiner_():
            for o in objs:
                o['bouge'] = False
            raffiner(R, objs, groupe)
            for o in objs:
                o['a_reprendre'] = o['bouge']

        def sans_expo():
            """Hors HP5 : pour chaque look dont une recherche a pris une exposition, les trois mêmes recherches menées à
            exposition 0 (départ : la recette trouvée), pour juger la consigne hors échantillon au bilan."""
            avec_e = {o['look'] for o in objs if o['look'] != 'hp5' and not o.get('e3_fixe') and o['e3']}
            ids = {o['id'] for o in objs}
            clones = []
            for o in [o for o in objs if o['look'] in avec_e and not o.get('e3_fixe') and o['id'] + '#0' not in ids]:
                c = dict(o, id=o['id'] + '#0', e3=0, e3_fixe=True, depart=f"{o['id']} ramenée à l'exposition 0", a_reprendre=bool(o['e3']))
                c['s'] = note(R, c['look'], 0, c['rec'], c['noms'])['score']
                clones.append(c)
            objs.extend(clones)
            sauver(objs, groupe)
            act = [o for o in objs if o.get('e3_fixe') and o.get('a_reprendre')]
            if act:
                descente(R, objs, groupe, 2, act)
                raffiner(R, objs, groupe, act)
                clarte(R, objs, groupe, act)
            journal(f"{groupe} sans exposition : {sorted(avec_e) or 'aucun look concerné'}")

        for nom, fn in (('descente', lambda: descente(R, objs, groupe, 2)), ('raffiner', raffiner_),
                        ('descente2', lambda: descente(R, objs, groupe, 1, [o for o in objs if o.get('a_reprendre')])),
                        ('clarte', lambda: clarte(R, objs, groupe)), ('sans_expo', sans_expo)):
            if nom in faits:
                continue
            fn()
            faits.add(nom)
            ecrire_atomique(V2 / f'etapes-{groupe}.json', json.dumps(sorted(faits)))
        for o in objs:
            journal(f"retenu {o['id']} {o['s']:.3f} {texte(o['rec'], o['e3'])}")
    finally:
        R.fermer()
        pre = f" ; pré-tri : {sys.modules['xt4_transfert'].STATS}" if 'xt4_transfert' in sys.modules else ''
        journal(f'{groupe} : {R.n_rendus} rendus, {R.t_banc / 60:.1f} min de boîtier{pre}')


def etat():
    for f in sorted(V2.glob('etat-*.json')):
        for o in json.loads(f.read_text()):
            print(f"{o['id']:24s} {o['s']:.3f}  {texte(o['rec'], o['e3'])}")


# ---------------------------------------------------------------------------------------------------------------
# Bilan : notes sur A, B et 16, contrôle croisé, recettes de 2022
# ---------------------------------------------------------------------------------------------------------------
def par_tranche(R, look, e3, r):
    Ls = np.concatenate([lab(R, n, r) for n in TOUS])
    Ts = np.concatenate([CIB[look][e3][n] for n in TOUS])
    out = []
    for a, b in ((0, 15), (15, 30), (30, 45), (45, 60), (60, 75), (75, 90), (90, 101)):
        m = (Ts[:, 0] >= a) & (Ts[:, 0] < b)
        if m.sum() < 20:
            continue
        x = {'tranche': f'{a}-{min(b, 100)}', 'blocs': int(m.sum()), 'dL': round(float(np.median(Ls[m, 0] - Ts[m, 0])), 1)}
        if look not in NB:
            x['dC'] = round(float(np.median(np.hypot(Ls[m, 1], Ls[m, 2]) - np.hypot(Ts[m, 1], Ts[m, 2]))), 1)
            x['db'] = round(float(np.median(Ls[m, 2] - Ts[m, 2])), 1)
            x['dE'] = round(float(np.median(dm.de2000(Ls[m], Ts[m]))), 2)
        out.append(x)
    return out


def par_famille(R, look, e3, r):
    Ls = np.concatenate([lab(R, n, r) for n in TOUS])
    Ts = np.concatenate([CIB[look][e3][n] for n in TOUS])
    S = np.concatenate([SC[n] for n in TOUS])
    C, h = np.hypot(S[:, 1], S[:, 2]), np.degrees(np.arctan2(S[:, 2], S[:, 1])) % 360
    out = {}
    for k, f in xm.CATEGORIES.items():
        m = f(S[:, 0], C, h)
        if m.sum() >= 20:
            out[k] = {'blocs': int(m.sum()), 'dL': round(float(np.median(Ls[m, 0] - Ts[m, 0])), 1)}
            if look not in NB:
                out[k]['dE'] = round(float(np.median(dm.de2000(Ls[m], Ts[m]))), 1)
    return out


def fiche(R, look, e3, r, detail=False):
    x = {'recette': texte(r, e3), 'rec': r, 'e3': e3, 'tous': note(R, look, e3, r, TOUS), 'A': note(R, look, e3, r, A),
         'B': note(R, look, e3, r, B)}
    if look in NB:
        x['de2000'] = xm.resume({n: dm.de2000(lab(R, n, r), CIB[look][e3][n]) for n in TOUS})
    if detail:
        x['par_raf'] = {n: round(float(np.median(v)), 2) for n, v in ecarts(R, look, e3, r, TOUS).items()}
        x['tranches'] = par_tranche(R, look, e3, r)
        x['familles'] = par_famille(R, look, e3, r)
    return x


def choisie(ex, moitie, avec_expo):
    """Recette de 2022 choisie sur une moitié (au critère), à l'exposition 0 ou à sa meilleure exposition sur cette moitié."""
    k, e3 = min(((k, e) for k in ex for e in (ex[k]['par_e3'] if avec_expo else [0])),
                key=lambda ke: ex[ke[0]]['par_e3'][ke[1]][moitie]['score'])
    return {'nom': k, 'e3': e3, 'exposition': tiers(e3), **ex[k]['par_e3'][e3]}


def bilan():
    """Notes de la recette cherchée sur les 16 (livrée), contrôle croisé (cherchée sur A notée sur B, et l'inverse) contre les
    recettes de 2022 choisies sur les mêmes moitiés, telles quelles (exposition 0) et avec la meilleure consigne
    d'exposition de la moitié (comparaison stricte : le gain ne vient alors pas de la seule exposition)."""
    import re
    cibles()
    P = presets()
    etats = {}
    for f in V2.glob('etat-*.json'):
        for o in json.loads(f.read_text()):
            etats[o['id']] = o
    R = RendusV2()
    out = json.loads(SORTIE.read_text()) if SORTIE.exists() else {}
    try:
        looks = [l for l in LOOKS if all(f'{l}@{m}' in etats for m in ('A', 'B', '16'))]
        R.lot_par_raf({n: [etats[i]['rec'] for l in looks for m in ('A', 'B', '16') for i in (f'{l}@{m}', f'{l}@{m}#0') if i in etats]
                       for n in TOUS})
        for l in looks:
            fam = {k: p for k, p in P.items() if p['nb'] == (l in NB)}
            o16, oA, oB = (etats[f'{l}@{m}'] for m in ('16', 'A', 'B'))
            consigne = None
            if l != 'hp5' and all(f'{l}@{m}#0' in etats for m in ('16', 'A', 'B')):
                z16, zA, zB = (etats[f'{l}@{m}#0'] for m in ('16', 'A', 'B'))
                sens = {'A→B': (note(R, l, oA['e3'], oA['rec'], B), note(R, l, 0, zA['rec'], B)),
                        'B→A': (note(R, l, oB['e3'], oB['rec'], A), note(R, l, 0, zB['rec'], A))}
                gain = float(np.mean([z['score'] - e['score'] for e, z in sens.values()]))
                garde = gain >= SEUIL_EXPO_HORS
                consigne = {'expositions': {m: tiers(x['e3']) for m, x in (('A', oA), ('B', oB), ('16', o16))},
                            'hors_echantillon': {k: {'avec': e, 'sans': z} for k, (e, z) in sens.items()},
                            'gain_moyen_critere': round(gain, 3), 'seuil': SEUIL_EXPO_HORS, 'gardee': garde}
                if not garde:
                    o16, oA, oB = z16, zA, zB
            ex = {k: {'par_e3': {e: {'tous': note(R, l, e, p['rec'], TOUS), 'A': note(R, l, e, p['rec'], A),
                                     'B': note(R, l, e, p['rec'], B)} for e in E3}} for k, p in fam.items()}
            telles = {m: choisie(ex, m, False) for m in ('A', 'B', 'tous')}
            expo = {m: choisie(ex, m, True) for m in ('A', 'B', 'tous')}
            nommees = [k for k in ex if re.search(NOMMEES[l], k.lower())]
            exn = min(nommees or list(ex), key=lambda k: ex[k]['par_e3'][0]['tous']['score'])
            nv = fiche(R, l, o16['e3'], o16['rec'], detail=True)
            fA, fB = fiche(R, l, oA['e3'], oA['rec']), fiche(R, l, oB['e3'], oB['rec'])
            verdicts = {}
            for nom_c, c in (('telles_quelles', telles), ('avec_exposition', expo)):
                gB = fA['B']['score'] < c['A']['B']['score']
                gA = fB['A']['score'] < c['B']['A']['score']
                verdicts[nom_c] = {'gain_sur_B': gB, 'gain_sur_A': gA,
                                   'verdict': 'gain' if gA and gB else 'pas de gain' if not (gA or gB) else 'partagé'}
            ex16 = telles['tous']['nom']
            out[l] = {'nom': xc.FILMS[l][0], 'cible': xc.FILMS[l][2], 'nb': l in NB, 'unite': '|ΔL*|' if l in NB else 'ΔE2000',
                      'nouvelle': nv, 'sans_exposition': fiche(R, l, 0, o16['rec']) if o16['e3'] else None,
                      'depart': o16.get('depart'), 'cherchee_sur_A': fA, 'cherchee_sur_B': fB,
                      'existante_choisie_sur_A': telles['A'], 'existante_choisie_sur_B': telles['B'],
                      'existante_expo_choisie_sur_A': expo['A'], 'existante_expo_choisie_sur_B': expo['B'],
                      'meilleure_existante_16': {'nom': ex16, **fiche(R, l, 0, P[ex16]['rec'], detail=True)},
                      'meilleure_existante_16_avec_exposition': expo['tous'],
                      'existante_nommee': {'nom': exn, **fiche(R, l, 0, P[exn]['rec'])},
                      'existantes_classees': sorted(({'nom': k, **v['par_e3'][0], 'recette': texte(fam[k]['rec'])} for k, v in ex.items()),
                                                    key=lambda x: x['tous']['score'])[:10],
                      'verdicts': verdicts, 'verdict': verdicts['avec_exposition']['verdict'], 'consigne_exposition': consigne}
            journal(f"bilan {l} : {nv['tous']} ; A→B {fA['B']} contre {telles['A']['nom']} {telles['A']['B']} "
                    f"(avec exposition {expo['A']['nom']} {expo['A']['exposition']} {expo['A']['B']}) ; B→A {fB['A']} contre "
                    f"{telles['B']['nom']} {telles['B']['A']} (avec exposition {expo['B']['nom']} {expo['B']['exposition']} "
                    f"{expo['B']['A']}) : {verdicts}")
    finally:
        R.fermer()
    SORTIE.write_text(json.dumps(out, indent=1, ensure_ascii=False, default=float))
    return out


# ---------------------------------------------------------------------------------------------------------------
# Grain, livraison, contrôle, planches
# ---------------------------------------------------------------------------------------------------------------
def grain():
    """σ de L* ajouté par chaque grain (rendu − rendu grain coupé) au cercle de 48 µm, méthode de xt4_mesure.grain."""
    import cv2
    bil = json.loads(SORTIE.read_text())
    dossier = V2 / 'grain'
    dossier.mkdir(parents=True, exist_ok=True)
    R = RendusV2()
    r_ap = xm.APERTURE_UM / 2 / xm.PIXEL_JPEG_UM
    k = int(np.ceil(r_ap))
    yy, xx = np.mgrid[-k:k + 1, -k:k + 1]
    noyau = ((xx ** 2 + yy ** 2) <= r_ap ** 2).astype(np.float32)
    noyau /= noyau.sum()
    B_ = xm.B
    out = {}
    try:
        for l, b in bil.items():
            if l not in NB + ('portra',):          # Classic Chrome et ses variantes : la LUT n'a pas de grain, grain coupé
                continue
            recs = {g: dict(b['nouvelle']['rec'], grain=g, bruit=-4) for g in xm.GRAIN}
            R.lot(list(recs.values()), xm.GRAIN_RAF, garder=dossier)
            res = {}
            for g, r in recs.items():
                s_ap = []
                for n in xm.GRAIN_RAF:
                    a = dm.code_lab(xm.jpeg(dossier / f'{n}-{xm.cle(r)}.jpg') / 255.0)[..., 0]
                    z = dm.code_lab(xm.jpeg(dossier / f'{n}-{xm.cle(recs[1])}.jpg') / 255.0)[..., 0]
                    filt = cv2.filter2D((a - z).astype(np.float32), -1, noyau)
                    H, W = a.shape[0] // B_ * B_, a.shape[1] // B_ * B_
                    idx = R.blocs[n]['idx']
                    ref = z[:H, :W].reshape(H // B_, B_, W // B_, B_).mean((1, 3)).ravel()[idx]
                    sel = idx[(ref > 35) & (ref < 65)]
                    s_ap.append(filt[:H, :W].reshape(H // B_, B_, W // B_, B_).transpose(0, 2, 1, 3).reshape(-1, B_ * B_)[sel].std(1))
                res[g] = {'reglage': '/'.join(xm.GRAIN[g]).lower(), 'sigma_L_48um': round(float(np.median(np.concatenate(s_ap))), 2)}
            out[l] = res
    finally:
        R.fermer()
    cible = json.loads((xm.CHANTIER / 'grain.json').read_text())['trix_cible']['sigma_L_48um']
    m = out['trix']
    ordre = sorted((g for g in m if g != 1), key=lambda g: m[g]['sigma_L_48um'])
    tx = min(ordre, key=lambda g: abs(m[g]['sigma_L_48um'] - cible))
    choix = {'trix': tx, 'hp5': tx, 'fp4': ordre[max(ordre.index(tx) - 1, 0)], 'portra': 2}
    choix |= {l: 1 for l in COULEUR if l != 'portra'}          # la LUT du Classic Chrome n'a pas de grain
    # seconde série (hypothèse, par rang comme la Portra) : Pro 400H, négatif ISO 400, comme la Portra ; Ektar 100 et les
    # diapositives (Provia, Velvia, Ektachrome, Kodachrome : granularités RMS 8 à 10) sous le plus faible réglage : coupé
    choix |= {'fp400h': 2} | {l: 1 for l in COULEUR2 if l != 'fp400h'}
    (V2 / 'grain.json').write_text(json.dumps({'mesure': out, 'choix': choix, 'cible_trix_48um': cible}, indent=1, ensure_ascii=False))
    journal(f'grain v2 choisi {choix}')


DR_CHOIX = V2 / 'dr-choix.json'     # écrit par xt4_validation.dr : {look: {'dr': 200, 'h': …}} quand le gain est net


RELANCE_FX = V2 / 'relance-fx.json'   # écrit par xt4_relance_fx.noter : {look: {'rec': …, 'remplace': bool}}
RELANCE_STRATES = V2 / 'relance-strates.json'   # écrit par xt4_relance_strates.noter, même forme


def base_livree(l, b):
    """(recette, note sur les 16 RAF) d'où part le .FP1 : celle d'une relance (strates de chroma, sinon FX Blue) quand elle
    a remplacé la recherche."""
    for f in (RELANCE_STRATES, RELANCE_FX):
        x = json.loads(f.read_text()).get(l) if f.exists() else None
        if x and x.get('remplace'):
            return x['rec'], x['note_16']
    return b['nouvelle']['rec'], b['nouvelle']['tous']


def recette_livree(l, b, choix):
    r = dict(base_livree(l, b)[0], grain=choix[l], dr=100, drp=0, nettete=0, bruit=-4)
    d = json.loads(DR_CHOIX.read_text()).get(l) if DR_CHOIX.exists() else None
    if d:
        r.update(dr=int(d['dr']), h=d['h'])
    k = json.loads(KELVIN_CHOIX.read_text()).get(l) if KELVIN_CHOIX.exists() else None
    if k:
        r.update(wb=xm.WB['Temperature'], kelvin=int(k))
    if not kelvin(r):
        r['wb'] = xm.WB['Auto']
        r.pop('kelvin', None)
    return r


def nom_fp1(l, e3):
    """(nom du fichier sans extension, étiquette) : une consigne d'exposition se lit dans le nom (l'auteur, 30/10/2026), elle ne
    s'écrit nulle part ailleurs dans un .FP1 ; pas de barre dans un nom de fichier. Étiquette : 25 caractères ASCII au plus."""
    if not e3:
        return FP1_NOMS[l], FP1_NOMS[l]
    c = tiers(e3).replace('−', '-')
    return f"{FP1_NOMS[l]} {c.replace('/', '-')} IL", f'{FP1_NOMS[l]} {c}'


def livrer():
    bil = json.loads(SORTIE.read_text())
    choix = {k: int(v) for k, v in json.loads((V2 / 'grain.json').read_text())['choix'].items()}
    for l, b in bil.items():
        r = recette_livree(l, b, choix)
        fichier, etiquette = nom_fp1(l, b['nouvelle']['e3'])
        p = xm.RECETTES / f'{fichier}.FP1'
        xm.ecrire_fp1(r, p, etiquette)
        relu = xm.lire_fp1(p)
        for k in ('sim', 'h', 's', 'couleur', 'wb', 'wb_r', 'wb_b', 'grain', 'cc', 'ccb', 'clarte', 'nettete', 'bruit'):
            if l in NB and k == 'couleur':
                continue
            assert float(relu.get(k, 0)) == float(r.get(k, 0)), (l, k, relu.get(k), r.get(k))
        assert kelvin(relu) == kelvin(r), (l, kelvin(relu), kelvin(r))
        journal(f'livré {p.name} : {texte(r, b["nouvelle"]["e3"])}')


def controle():
    """Les .FP1 livrés relus et rendus tels quels sur les 16 RAF (Auto = balance de la prise de vue), avec et sans grain."""
    cibles()
    bil = json.loads(SORTIE.read_text())
    R = RendusV2()
    out = {}
    try:
        for l, b in bil.items():
            r = xm.lire_fp1(xm.RECETTES / f"{nom_fp1(l, b['nouvelle']['e3'])[0]}.FP1")
            m = normaliser({k: v for k, v in r.items() if k not in ('nom', 'source')})
            if m['wb'] == xm.WB['Auto']:
                m['wb'] = 0
                m.pop('kelvin', None)
            if l not in NB:
                m.pop('mono_wc', None)
                m.pop('mono_mg', None)
            if m.get('dr', 100) != 100:      # les 16 RAF sont en DR100 : DR200 / 400 y virent au vert ; contrôle en DR100
                m['dr'] = 100
            sans = dict(m, grain=1)
            global BALANCE_PERMISE
            BALANCE_PERMISE = bool(m.get('wb'))        # seulement si le duel Kelvin l'a fait entrer dans le .FP1
            try:
                R.lot_par_raf({n: [m, sans] for n in TOUS})
            finally:
                BALANCE_PERMISE = False
            e3 = b['nouvelle']['e3']
            out[l] = {'recette': texte(m, e3), 'avec_grain': note(R, l, e3, m, TOUS), 'grain_coupe': note(R, l, e3, sans, TOUS),
                      'cherchee': base_livree(l, b)[1]}
            journal(f'contrôle {l} {out[l]}')
    finally:
        R.fermer()
    (xm.DONNEES / f'xt4-recettes-v2-livrees-{DATE}.json').write_text(json.dumps(out, indent=1, ensure_ascii=False))


PLANCHE_RAF = {'trix': ['157-DSCF9412', '176-DSCF0476', '041-DSCF6283'], 'hp5': ['157-DSCF9412', '176-DSCF0476', '041-DSCF6283'],
               'fp4': ['157-DSCF9412', '176-DSCF0476', '041-DSCF6283'], 'portra': ['006-DSCF9213', '176-DSCF0476', '157-DSCF9412'],
               'classic_chrome': ['176-DSCF0476', '167-DSCF0467', '157-DSCF9412'], 'cc_115': ['176-DSCF0476', '167-DSCF0467', '157-DSCF9412'],
               'cc_130': ['176-DSCF0476', '167-DSCF0467', '157-DSCF9412'], 'cc_130_contraste': ['176-DSCF0476', '167-DSCF0467', '157-DSCF9412']}
PLANCHE_RAF |= {l: ['167-DSCF0467', '176-DSCF0476', '159-DSCF9414'] for l in COULEUR2}   # peau et rouge ; couleurs mêlées ; verts et ciel


def courbe_tons(R, l, r):
    """L* rendu par la recette en fonction de l'exposition de la scène (blocs peu colorés des 16 RAF), pour simuler une
    surexposition sur l'image entière : L' = T(T⁻¹(L) + e)."""
    x, y = [], []
    for n in TOUS:
        m = np.hypot(SC[n][:, 1], SC[n][:, 2]) < 6
        _, X = xm.scene(charger_blocs_v2()[n], Y18)
        x.append(np.log2(np.maximum(X[m, 1], 1e-6) / 0.18))
        y.append(lab(R, n, r)[m, 0])
    x, y = np.concatenate(x), np.concatenate(y)
    bords = np.arange(-6, 3.01, 1 / 6)
    cx, cy = [], []
    for a, b in zip(bords[:-1], bords[1:]):
        s = (x >= a) & (x < b)
        if s.sum() >= 10:
            cx.append((a + b) / 2)
            cy.append(np.median(y[s]))
    return np.array(cx), np.maximum.accumulate(np.array(cy))


def simuler_expo(img, cx, cy, e):
    L = dm.code_lab(img.reshape(-1, 3) / 255.0)
    xv = np.interp(L[:, 0], cy, cx)
    pente = (cy[-1] - cy[-4]) / (cx[-1] - cx[-4])          # au-delà de la courbe mesurée : prolongée, plafonnée à 100
    L2 = np.where(xv + e <= cx[-1], np.interp(xv + e, cx, cy), cy[-1] + pente * (xv + e - cx[-1]))
    lab2 = L.copy()
    lab2[:, 0] = np.clip(L2, 0, 100)
    return (np.clip(dm.lab_code(lab2), 0, 1) * 255 + 0.5).astype(np.uint8).reshape(img.shape)


def planches():
    from PIL import Image, ImageDraw
    cibles()
    bil = json.loads(SORTIE.read_text())
    P = presets()
    dossier = V2 / 'planches'
    dossier.mkdir(parents=True, exist_ok=True)
    R = RendusV2()
    TUILE = xm.TUILE
    try:
        for l, b in bil.items():
            noms = PLANCHE_RAF[l]
            exn = b['meilleure_existante_16']['nom']
            (rec_ex, change), (rec_nv, note_nv), e3 = sans_balance(P[exn]['rec']), base_livree(l, b), b['nouvelle']['e3']
            R.lot([rec_ex, rec_nv], noms, garder=dossier)
            par_raf = {1: {n: float(np.median(x)) for n, x in ecarts(R, l, 0, rec_ex, noms).items()},
                       2: {n: float(np.median(x)) for n, x in ecarts(R, l, e3, rec_nv, noms).items()}}
            cx, cy = courbe_tons(R, l, rec_nv) if e3 else (None, None)
            W, H = TUILE
            marge, haut = 12, 104
            img = Image.new('RGB', (3 * W + 4 * marge, haut + len(noms) * (H + marge) + marge), 'white')
            dr = ImageDraw.Draw(img)
            p1, p2 = xm._police(22), xm._police(17)
            u = b['unite']
            f2 = lambda v: f'{v:.1f}'.replace('.', ',')  # noqa: E731
            titres = [('CIBLE', f"{b['nom']} : {xc.FILMS[l][2]}", ''),
                      ('MEILLEURE RECETTE DE THOMAS', exn + (' (balance de la prise de vue)' if change else ''),
                       f"{u} médian {f2(b['meilleure_existante_16']['tous']['mediane'])} (16 RAF), grain coupé"),
                      ('NOUVELLE RECETTE', FP1_NOMS[l] + (f', exposée {tiers(e3)} IL (simulé)' if e3 else ''),
                       f"{u} médian {f2(note_nv['mediane'])} (16 RAF), grain coupé")]
            for k, lignes in enumerate(titres):
                x = marge + k * (W + marge)
                for j, (t, pol, coul) in enumerate(zip(lignes, (p1, p2, p2), ('black', 'black', (70, 70, 70)))):
                    while t and dr.textlength(t, font=pol) > W - 4:     # jamais sur la colonne voisine
                        t = t[:-2] + '…'
                    dr.text((x, 10 + 32 * j), t, fill=coul, font=pol)
            for i, n in enumerate(noms):
                y = haut + i * (H + marge)
                nv = np.asarray(Image.open(dossier / f'{n}-{xm.cle(rec_nv)}.jpg').convert('RGB').resize(TUILE, Image.LANCZOS))
                if e3:
                    nv = simuler_expo(nv, cx, cy, e3 / 3)
                tuiles = [Image.fromarray(xc.image(n, l, Y18, TUILE)),
                          Image.open(dossier / f'{n}-{xm.cle(rec_ex)}.jpg').convert('RGB').resize(TUILE, Image.LANCZOS),
                          Image.fromarray(nv)]
                for k, t in enumerate(tuiles):
                    x = marge + k * (W + marge)
                    img.paste(t, (x, y))
                    etiq = f'{n[:3]} : cible' if k == 0 else f"{n[:3]} : {u} {f2(par_raf[k][n])}"
                    tw = dr.textlength(etiq, font=p2)
                    dr.rectangle((x + 6, y + H - 30, x + 14 + tw, y + H - 6), fill=(255, 255, 255))
                    dr.text((x + 10, y + H - 28), etiq, fill='black', font=p2)
            sortie = xm.FIGURES / f'xt4-planche-v2-{l.replace("_", "-")}-{DATE}.jpg'
            img.save(sortie, quality=86)
            journal(f'planche {sortie.name}')
    finally:
        R.fermer()


KELVIN_CHOIX = V2 / 'kelvin-choix.json'


def kelvin_duel():
    """N&B, à la toute fin (balance forcée : voir DOM_NB) : la recette cherchée sur A, sans Kelvin, contre la même avec le
    meilleur Kelvin de KELVINS_DUEL choisi sur A, notées sur B ; et l'inverse. Kelvin retenu (choisi alors sur les 16) seulement
    s'il gagne au moins SEUIL_KELVIN au critère en moyenne des deux sens. Au plus 4 × 8 + 8 + 4 × 8 + 8 + 4 × 16 = 144
    conversions par look."""
    global BALANCE_PERMISE
    cibles()
    bil = json.loads(SORTIE.read_text())
    etats = {o['id']: o for f in V2.glob('etat-nb.json') for o in json.loads(f.read_text())}
    choix = json.loads(KELVIN_CHOIX.read_text()) if KELVIN_CHOIX.exists() else {}
    out = {}
    R = RendusV2()
    BALANCE_PERMISE = True
    try:
        for l in NB:
            if l not in bil:
                continue
            res = {}
            for sens, (m, sur, autre) in {'A→B': ('A', A, B), 'B→A': ('B', B, A)}.items():
                o = etats[f'{l}@{m}']
                recs = {k: avec(o['rec'], 'k', k) for k in KELVINS_DUEL}
                R.lot_par_raf({n: list(recs.values()) for n in sur})
                kb = min(recs, key=lambda k: note(R, l, o['e3'], recs[k], sur)['score'])
                R.lot_par_raf({n: [recs[kb], o['rec']] for n in autre})
                sans, avec_k = note(R, l, o['e3'], o['rec'], autre), note(R, l, o['e3'], recs[kb], autre)
                res[sens] = {'kelvin_choisi': kb, 'sans': sans, 'avec': avec_k, 'gain': round(sans['score'] - avec_k['score'], 3)}
            gain = float(np.mean([x['gain'] for x in res.values()]))
            garde = gain >= SEUIL_KELVIN
            x = {'sens': res, 'gain_moyen': round(gain, 3), 'seuil': SEUIL_KELVIN, 'garde': garde}
            if garde:
                r16, e3 = bil[l]['nouvelle']['rec'], bil[l]['nouvelle']['e3']
                recs = {k: avec(r16, 'k', k) for k in KELVINS_DUEL}
                R.lot_par_raf({n: list(recs.values()) for n in TOUS})
                kb = min(recs, key=lambda k: note(R, l, e3, recs[k], TOUS)['score'])
                x['kelvin_16'] = {'kelvin': kb, 'note_16': note(R, l, e3, recs[kb], TOUS), 'sans_16': bil[l]['nouvelle']['tous']}
                choix[l] = kb
            else:
                choix.pop(l, None)
            out[l] = x
            journal(f"Kelvin {l} : {res} → gain moyen {gain:.3f} : {'gardé' if garde else 'non'}")
    finally:
        BALANCE_PERMISE = False
        R.fermer()
    ecrire_atomique(KELVIN_CHOIX, json.dumps(choix, indent=1))
    (xm.DONNEES / f'xt4-kelvin-duel-{DATE}.json').write_text(json.dumps(out, indent=1, ensure_ascii=False, default=float))


def manifeste():
    """Complète donnees/xt4-mesure-raf.tsv (nom, origine, sha256, taille, que lit xt4_mesure.copier_rafs) : moitié de la
    validation croisée, ISO, balance et simulation de la prise de vue (EXIF), blocs mesurés."""
    import subprocess
    lignes = xm.RAF_TSV.read_text().splitlines()
    ex = json.loads(subprocess.run(['exiftool', '-j', '-ISO', '-WhiteBalance', '-FilmMode', '-Saturation', '-ExposureCompensation',
                                    *map(str, xm.rafs())], capture_output=True, text=True, check=True).stdout)
    ex = {pathlib.Path(x['SourceFile']).stem: x for x in ex}
    blocs = charger_blocs_v2()
    out = ['\t'.join(lignes[0].split('\t')[:4] + ['moitie', 'iso', 'balance_pdv', 'simulation_pdv', 'correction_expo_pdv', 'blocs'])]
    for l in lignes[1:]:
        c = l.split('\t')[:4]
        x = ex[c[0]]
        out.append('\t'.join(c + ['A' if c[0] in A else 'B', str(x.get('ISO', '')), str(x.get('WhiteBalance', '')),
                                  str(x['FilmMode'] if x.get('FilmMode', '-') != '-' else x.get('Saturation', '')), str(x.get('ExposureCompensation', '')),
                                  str(len(blocs[c[0]]['idx']))]))
    xm.RAF_TSV.write_text('\n'.join(out) + '\n')
    journal(f'manifeste : {len(out) - 1} RAF')


if __name__ == '__main__':
    a = sys.argv[1:]
    if not a:
        print(__doc__)
        sys.exit(2)
    if a[0] == 'chercher':
        chercher(a[1])
    else:
        globals()[a[0]]()
