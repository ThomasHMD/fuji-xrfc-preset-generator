#!/usr/bin/env python3
# SPDX-License-Identifier: CC-BY-NC-4.0
# Copyright (c) 2026 Thomas Hammoudi
"""Profil de conversion RAW du X-T4 (propriété 0xD185, 621 octets) : lire et modifier ses paramètres.

Le profil se lit après l'envoi d'un RAF (« xt4_recettes convertir » le garde : d185-du-raf.bin). Les paramètres sont
N entiers 32 bits signés à la fin du profil (N = premier uint16). Index d'après FilmKit (src/profile/d185.ts).

  python3 -I xt4_d185.py lire d185.bin
  python3 -I xt4_d185.py modifier d185.bin sortie.bin FilmSimulation=12 HighlightTone=10 GrainEffect=1

Index 11 = WBShootCond (FilmKit le nomme SmoothSkin) : 1 dans le profil d'un RAF = garder la balance de la prise de vue ; 0 = appliquer
WhiteBalance / WBColorTemp du profil (mesuré sur le boîtier le 29/10/2026 : Incandescent et 2 500 à 10 000 K s'appliquent, l'EXIF le dit).
Ordre des champs (mesuré sur le boîtier) : ... ColorChromeEffect, WBShootCond, WhiteBalance, WBShiftR,
WBShiftB, WBColorTemp ...

Valeurs comme sur le fil : tons, couleur, netteté, clarté × 10 ; grain 1 off, 2 faible/petit, 3 fort/petit,
4 faible/grand, 5 fort/grand ; Color Chrome et FX Blue 1 off, 2 faible, 3 fort ; plage dynamique 100/200/400.
"""
import struct
import sys

INDEX = {"ExposureBias": 4, "DynamicRange": 6, "WideDRange": 7, "FilmSimulation": 8, "GrainEffect": 9,
         "ColorChrome": 10, "WBShootCond": 11, "WhiteBalance": 12, "WBShiftR": 13, "WBShiftB": 14, "WBColorTemp": 15,
         "HighlightTone": 16, "ShadowTone": 17, "Color": 18, "Sharpness": 19, "NoiseReduction": 20, "CCFxBlue": 25,
         "Clarity": 27}
NOMS = {v: k for k, v in INDEX.items()}


def params(d):
    n = struct.unpack_from("<H", d, 0)[0]
    off = len(d) - 4 * n
    return off, list(struct.unpack_from(f"<{n}i", d, off))


def modifier(d, changements):
    d = bytearray(d)
    off, _ = params(d)
    for nom, val in changements.items():
        i = INDEX[nom] if nom in INDEX else int(nom)
        struct.pack_into("<i", d, off + 4 * i, val)
    return bytes(d)


if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "lire":
        d = open(sys.argv[2], "rb").read()
        off, p = params(d)
        print(f"{len(d)} octets, {len(p)} paramètres à partir de {off}")
        for i, v in enumerate(p):
            print(f"  {i:2d} {NOMS.get(i, '?'):<16} {v}")
    elif len(sys.argv) >= 4 and sys.argv[1] == "modifier":
        d = open(sys.argv[2], "rb").read()
        ch = {k: int(v, 0) for k, v in (a.split("=", 1) for a in sys.argv[4:])}
        open(sys.argv[3], "wb").write(modifier(d, ch))
        print(f"{sys.argv[3]} : {ch}")
    else:
        print(__doc__)
        sys.exit(2)
