// SPDX-License-Identifier: CC-BY-NC-4.0
// Copyright (c) 2026 Thomas Hammoudi
// Écrire une recette Fujifilm (profil .FP1 de X RAW Studio) dans un emplacement C1 à C7 du X-T4 par USB (PTP, ImageCaptureCore).
// Même transport que d750/outils/d750_ptp.swift : commandes PTP brutes par ImageCaptureCore, phase de données sortante sans
// l'entête de 12 octets. Protocole, sources, ce qui reste à vérifier : voir le README du dépôt (La méthode en clair, Rejouer la mesure).
//
//   swiftc -O -swift-version 5 xt4/outils/xt4_recettes.swift -o <dossier hors du dépôt>/xt4_recettes
//   xt4_recettes sonde                                         lecture seule : session, mode USB, la famille 0xD18C est-elle là ?
//   xt4_recettes traduire <fichier.FP1 | dossier> [--court] [--emplacement N] [--dr-auto-zero]
//                                                              sans boîtier : affiche les écritures PTP qui seraient faites
//   xt4_recettes ecrire <1-7> <fichier.FP1>                    SIMULATION (par défaut) : comme traduire, rien n'est envoyé
//   xt4_recettes ecrire <1-7> <fichier.FP1> --vraiment --sauvegarde <fichier> [--sortie <dossier>]
//                                                              écrit un seul emplacement, puis relit et compare
//   xt4_recettes sauvegarder <fichier>                         lecture seule : copie la sauvegarde des réglages (objet 0)
//   xt4_recettes relire <1-7> <fichier.FP1> [<1-7> <fichier.FP1> …]
//                                                              après extinction : chaque emplacement relu contre son .FP1 ; seul le
//                                                              sélecteur 0xD18C est écrit, puis remis
//   xt4_recettes autotest                                      sans boîtier : contrôle des encodages sur des vecteurs connus
//
// Garde-fous (voir aussi le README du dépôt) :
//  - sonde et sauvegarder ne PEUVENT PAS écrire : la fonction ptp() refuse tout code d'opération hors lecture (liste blanche) ;
//  - l'écriture (SetDevicePropValue 0x1016) n'est ouverte que par ecrire --vraiment, et seulement sur 0xD18C, 0xD18D et
//    0xD190 à 0xD1A4 : jamais 0xD1A5 (état de prise de vue courant), jamais 0xD18E/0xD18F (taille et qualité d'image : les
//    projets publics ne les modifient pas non plus), jamais de firmware, jamais de restauration de sauvegarde (0x100C/0x100D) ;
//  - ecrire --vraiment refuse si le modèle n'est pas un X-T4, si le mode USB (0xD16E) n'est pas 6 (USB RAW CONV./BACKUP
//    RESTORE), si 0xD18C ne se lit pas (le X-T4 2.12 refuse sa description, 0x200A, mais lit et écrit sa valeur : mesuré le 29/10/2026), si le FP1
//    n'est pas pour un X-T4 (sauf --autre-appareil), et sans --sauvegarde <fichier> (copie complète faite avant par
//    « sauvegarder ») ou --sans-sauvegarde ;
//  - l'ancien contenu de l'emplacement (nom + 22 réglages) est relu et gardé dans le dossier de sortie avant d'écrire.
// Le dossier de sortie (journal, copies) est HORS du dépôt : une sauvegarde contient le numéro de série en clair.
//
// Statut : essayé sur un X-T4 (firmware 2.12) le 29/10/2026 : C7 écrit, relu, retrouvé dans la sauvegarde après extinction,
// puis remis. Ce qui est encodé vient de FilmKit, de fujifilm-ptp-recipes, de fujifilm-ptp-reference (zgrimz) et d'essais
// sur le boîtier ; chaque point incertain porte l'étiquette « hypothèse » (voir le README du dépôt, La méthode en clair).
import Foundation
import ImageCaptureCore
import CryptoKit

// ============================================================================================================
// 1. Arguments
// ============================================================================================================
struct Arguments {
    var commande = ""
    var positionnels: [String] = []
    var drapeaux = Set<String>()
    var valeurs: [String: String] = [:]
}
let optionsAvecValeur: Set<String> = ["--sortie", "--sauvegarde", "--emplacement", "--profil"]
func lireArguments() -> Arguments {
    var a = Arguments(); let t = CommandLine.arguments; var i = 1
    while i < t.count {
        let s = t[i]
        if optionsAvecValeur.contains(s), i + 1 < t.count { a.valeurs[s] = t[i + 1]; i += 2; continue }
        if s.hasPrefix("--") { a.drapeaux.insert(s) }
        else if a.commande.isEmpty { a.commande = s }
        else { a.positionnels.append(s) }
        i += 1
    }
    return a
}
let arg = lireArguments()

func usage() -> Never {
    print("""
    xt4_recettes sonde
    xt4_recettes traduire <fichier.FP1 | dossier> [--court] [--emplacement N] [--dr-auto-zero] [--autre-appareil]
    xt4_recettes ecrire <1-7> <fichier.FP1> [--vraiment --sauvegarde <fichier> | --sans-sauvegarde] [--sortie <dossier>]
    xt4_recettes sauvegarder <fichier>
    xt4_recettes lire <code> [<code>…]                  lecture seule (GetDevicePropValue)
    xt4_recettes balayer [D000 D3FF]                     lecture seule : réglages qui répondent à GetDevicePropDesc
    xt4_recettes remettre <1-7> <emplacement-N-avant.json> [--vraiment]   réécrit le contenu gardé par « ecrire »
    xt4_recettes relire <1-7> <fichier.FP1> [<1-7> <fichier.FP1> …]      relit chaque emplacement contre son .FP1 (sélecteur remis)
    xt4_recettes autotest
    Sans --vraiment, ecrire n'envoie rien (simulation).
    """)
    exit(2)
}

// ============================================================================================================
// 2. Tables : réponses PTP, noms des réglages, vocabulaire du profil
// ============================================================================================================
let reponses: [UInt16: String] = [
    0x2001: "OK", 0x2002: "erreur générale", 0x2003: "session fermée", 0x2005: "opération non prise en charge",
    0x2006: "paramètre non pris en charge", 0x2009: "objet invalide", 0x200A: "réglage non pris en charge (famille absente ?)",
    0x200F: "accès refusé", 0x2019: "boîtier occupé", 0x201C: "valeur refusée (hors plage ou état du boîtier)",
    0x201D: "paramètre invalide", 0x201E: "session déjà ouverte", 0xFFFF: "erreur du transport"]
func rc(_ c: UInt16) -> String { String(format: "0x%04X", c) + " " + (reponses[c] ?? "?") }

let nomsProprietes: [UInt16: String] = [
    0xD16E: "mode USB", 0xD18C: "emplacement (sélecteur)", 0xD18D: "nom", 0xD18E: "taille d'image", 0xD18F: "qualité d'image",
    0xD190: "plage dynamique", 0xD191: "priorité plage dynamique", 0xD192: "simulation de film", 0xD193: "mono chaud/froid",
    0xD194: "mono magenta/vert", 0xD195: "grain", 0xD196: "Color Chrome", 0xD197: "Color Chrome FX Blue", 0xD198: "Smooth Skin",
    0xD199: "balance des blancs", 0xD19A: "décalage BB rouge", 0xD19B: "décalage BB bleu", 0xD19C: "température de couleur",
    0xD19D: "hautes lumières", 0xD19E: "ombres", 0xD19F: "couleur", 0xD1A0: "netteté", 0xD1A1: "réduction du bruit ISO",
    0xD1A2: "clarté", 0xD1A3: "optimiseur de modulation (LMO)", 0xD1A4: "espace colorimétrique", 0xD1A5: "taille (état courant)"]
func nomProp(_ c: UInt16) -> String { nomsProprietes[c] ?? "?" }

// Simulations de film : noms des simulations tels qu'ils figurent dans les .FP1, code d'après FilmKit /
// fujifilm-ptp-recipes (properties.md). Le X-T4 accepte les codes 1 à 18 (vérifié sur le boîtier).
let simulations: [String: Int] = [
    "Provia": 1, "Velvia": 2, "Astia": 3, "NEGAhi": 4, "NEGAStd": 5, "BW": 6, "BYe": 7, "BR": 8, "BG": 9, "Sepia": 10,
    "Classic": 11, "Acros": 12, "AcrosYe": 13, "AcrosR": 14, "AcrosG": 15, "Eterna": 16, "ClassicNEGA": 17, "BleachBypass": 18,
    "NostalgicNEGA": 19, "Reala": 20]
// Jetons présents dans les FP1 de 2022 mais que X RAW Studio 1.28 n'écrit pas (hypothèse : le générateur de
// profils les a nommés autrement) : 16 fichiers « NEGA » (= Pro Neg. Std), 3 fichiers « AcrosY » (= Acros + Ye).
let simulationsAlias: [String: String] = ["NEGA": "NEGAStd", "AcrosY": "AcrosYe"]
let simulationsMono: Set<Int> = [6, 7, 8, 9, 10, 12, 13, 14, 15]   // Sepia (10) comprise : refuse le toning mono
let simulationMax = 18                                              // X-T4 : pas de Nostalgic Neg. ni Reala Ace

let balances: [String: Int] = [
    "Auto": 0x0002, "Auto_White": 0x8020, "Auto_Ambience": 0x8021, "Daylight": 0x0004, "Incand": 0x0006, "UWater": 0x0008,
    "FLight1": 0x8001, "FLight2": 0x8002, "FLight3": 0x8003, "Shade": 0x8006, "Temperature": 0x8007,
    "Custom1": 0x8008, "Custom2": 0x8009, "Custom3": 0x800A]
// Les 31 positions de température de couleur des .FP1 (WBColorTemp, de 2500K à 10000K).
let kelvins: Set<Int> = [10000, 9100, 8300, 7700, 7100, 6700, 6300, 5900, 5600, 5300, 5000, 4800, 4500, 4300, 4200, 4000,
                         3800, 3700, 3600, 3400, 3300, 3200, 3100, 3000, 2950, 2850, 2800, 2700, 2650, 2550, 2500]
// Réduction du bruit ISO : table non linéaire (FilmKit NR_ENCODE, fujifilm-ptp-recipes properties.md).
let bruit: [Int: Int] = [-4: 0x8000, -3: 0x7000, -2: 0x4000, -1: 0x3000, 0: 0x2000, 1: 0x1000, 2: 0x0000, 3: 0x6000, 4: 0x5000]
let niveaux: [String: Int] = ["OFF": 1, "WEAK": 2, "STRONG": 3]     // Color Chrome, FX Blue, Smooth Skin

// ============================================================================================================
// 3. Binaire PTP
// ============================================================================================================
struct Lecteur {
    let d: Data; var i = 0
    init(_ d: Data) { self.d = d }
    var reste: Int { d.count - i }
    mutating func u8() -> UInt8 { defer { i += 1 }; return i < d.count ? d[d.startIndex + i] : 0 }
    mutating func u16() -> UInt16 { UInt16(u8()) | UInt16(u8()) << 8 }
    mutating func u32() -> UInt32 { UInt32(u16()) | UInt32(u16()) << 16 }
    mutating func tableau16() -> [UInt16] { let n = Int(u32()); return n > 4000 ? [] : (0..<n).map { _ in u16() } }
    mutating func chaine() -> String {
        let n = Int(u8()); var c: [UInt16] = []
        for _ in 0..<n { c.append(u16()) }
        return String(decoding: c.filter { $0 != 0 }, as: UTF16.self)
    }
    // valeur d'un réglage entier selon son type PTP (1 à 6) ; nil pour les autres types
    mutating func entier(type: UInt16) -> Int? {
        switch type {
        case 1: return Int(Int8(bitPattern: u8()))
        case 2: return Int(u8())
        case 3: return Int(Int16(bitPattern: u16()))
        case 4: return Int(u16())
        case 5: return Int(Int32(bitPattern: u32()))
        case 6: return Int(u32())
        default: return nil
        }
    }
}
func commande(_ code: UInt16, transaction: UInt32, parametres: [UInt32] = []) -> Data {
    var d = Data()
    func ajoute<T: FixedWidthInteger>(_ v: T) { withUnsafeBytes(of: v.littleEndian) { d.append(contentsOf: $0) } }
    ajoute(UInt32(12 + 4 * parametres.count)); ajoute(UInt16(1)); ajoute(code); ajoute(transaction)
    parametres.forEach { ajoute($0) }
    return d
}
// selon la version de macOS, la phase de données peut garder l'entête PTP de 12 octets
func sansEntete(_ p: Data) -> Data {
    if p.count >= 12, p[p.startIndex + 4] == 2, Int(p[p.startIndex]) | Int(p[p.startIndex + 1]) << 8 | Int(p[p.startIndex + 2]) << 16 == p.count {
        return p.subdata(in: (p.startIndex + 12)..<p.endIndex)
    }
    return p
}
func codeReponse(_ r: Data) -> UInt16 { r.count >= 8 ? UInt16(r[r.startIndex + 6]) | UInt16(r[r.startIndex + 7]) << 8 : 0 }
func hexa(_ d: Data, _ n: Int = 48) -> String { d.prefix(n).map { String(format: "%02x", $0) }.joined(separator: " ") + (d.count > n ? " …" : "") }
func octets16(_ v: Int) -> Data { var x = UInt16(truncatingIfNeeded: v).littleEndian; return Data(bytes: &x, count: 2) }
// chaîne PTP : un octet = nombre de caractères zéro final compris, puis UTF-16LE ; chaîne vide = un seul octet 0
func chainePTP(_ s: String) -> Data {
    if s.isEmpty { return Data([0]) }
    let u = Array(s.utf16) + [0]
    var d = Data([UInt8(u.count)])
    for c in u { d.append(UInt8(c & 0xFF)); d.append(UInt8(c >> 8)) }
    return d
}

struct Descripteur {
    var code: UInt16 = 0, type: UInt16 = 0, acces: UInt8 = 0
    var defaut: Int?, courant: Int?
    var forme = "aucune"       // aucune, plage, liste
    var valeurs: [Int] = []
    var mini = 0, maxi = 0, pas = 0
    var brut = Data()
    var resume: String {
        let a = acces == 1 ? "lecture/écriture" : (acces == 0 ? "lecture seule" : "accès \(acces)")
        var s = "type \(type) | \(a)"
        if let c = courant { s += " | courant \(c)" }
        if forme == "plage" { s += " | plage \(mini)…\(maxi) pas \(pas)" }
        if forme == "liste" { s += " | liste \(valeurs.prefix(24).map(String.init).joined(separator: ","))\(valeurs.count > 24 ? "…" : "")" }
        return s
    }
}
func lireDescripteur(_ d: Data) -> Descripteur? {
    guard d.count >= 5 else { return nil }
    var l = Lecteur(d); var r = Descripteur(); r.brut = d
    r.code = l.u16(); r.type = l.u16(); r.acces = l.u8()
    guard (1...6).contains(r.type) else { return r }          // chaîne ou autre type : on garde l'essentiel
    r.defaut = l.entier(type: r.type); r.courant = l.entier(type: r.type)
    let forme = l.u8()
    if forme == 1 {
        r.forme = "plage"; r.mini = l.entier(type: r.type) ?? 0; r.maxi = l.entier(type: r.type) ?? 0; r.pas = l.entier(type: r.type) ?? 0
    } else if forme == 2 {
        r.forme = "liste"; let n = Int(l.u16())
        r.valeurs = (0..<min(n, 2000)).compactMap { _ in l.entier(type: r.type) }
    }
    return r
}

// ============================================================================================================
// 4. Profil FP1 : lecture tolérante (deux FP1 de 2022 ont un « & » non échappé dans l'étiquette : un vrai lecteur XML échoue)
// ============================================================================================================
struct Profil {
    var chemin = ""
    var appareil = "", version = "", etiquette = ""
    var champs: [String: String] = [:]
}
func entites(_ s: String) -> String {
    s.replacingOccurrences(of: "&lt;", with: "<").replacingOccurrences(of: "&gt;", with: ">")
     .replacingOccurrences(of: "&quot;", with: "\"").replacingOccurrences(of: "&apos;", with: "'")
     .replacingOccurrences(of: "&amp;", with: "&")
}
func lireFP1(_ chemin: String) throws -> Profil {
    guard let data = FileManager.default.contents(atPath: chemin) else { throw NSError(domain: "fp1", code: 1, userInfo: [NSLocalizedDescriptionKey: "fichier illisible"]) }
    let texte = String(decoding: data, as: UTF8.self)
    var p = Profil(); p.chemin = chemin
    func motif(_ m: String, _ t: String) -> [NSTextCheckingResult] {
        guard let re = try? NSRegularExpression(pattern: m, options: [.dotMatchesLineSeparators]) else { return [] }
        return re.matches(in: t, range: NSRange(t.startIndex..., in: t))
    }
    func sous(_ r: NSTextCheckingResult, _ i: Int, _ t: String) -> String {
        guard let rg = Range(r.range(at: i), in: t) else { return "" }
        return String(t[rg])
    }
    guard !motif("<ConversionProfile\\b", texte).isEmpty else { throw NSError(domain: "fp1", code: 2, userInfo: [NSLocalizedDescriptionKey: "pas un profil FP1 (balise ConversionProfile absente)"]) }
    guard let groupe = motif("<PropertyGroup\\s+([^>]*)>", texte).first else { throw NSError(domain: "fp1", code: 3, userInfo: [NSLocalizedDescriptionKey: "balise PropertyGroup absente"]) }
    let attributs = sous(groupe, 1, texte)
    for a in motif("(\\w+)=\"([^\"]*)\"", attributs) {
        let k = sous(a, 1, attributs), v = entites(sous(a, 2, attributs))
        if k == "device" { p.appareil = v } else if k == "version" { p.version = v } else if k == "label" { p.etiquette = v }
    }
    for c in motif("<([A-Za-z_][A-Za-z0-9_]*)>([^<]*)</\\1>", texte) {
        p.champs[sous(c, 1, texte)] = entites(sous(c, 2, texte)).trimmingCharacters(in: .whitespacesAndNewlines)
    }
    return p
}

// Nom de l'emplacement : ASCII, 25 caractères au plus (fujifilm-ptp-recipes, name-rules.md)
func nomPropre(_ brut: String, repli: String) -> String {
    let autorises = Set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789 !\"#$%&'()*+,-./:;<=>?@[]\\^_{}|~")
    var s = ""
    for u in brut.decomposedStringWithCanonicalMapping.unicodeScalars {
        if u.properties.generalCategory == .nonspacingMark { continue }          // accents repliés
        switch u {
        case "\u{2018}", "\u{2019}": s.append("'")
        case "\u{201C}", "\u{201D}": s.append("\"")
        case "\u{2013}", "\u{2014}", "\u{2212}": s.append("-")
        default: let c = Character(u); s.append(autorises.contains(c) ? c : " ")
        }
    }
    s = s.split(separator: " ", omittingEmptySubsequences: true).joined(separator: " ")
    if s.count > 25 { s = String(s.prefix(25)).trimmingCharacters(in: .whitespaces) }
    return s.isEmpty ? repli : s
}

// ============================================================================================================
// 5. Traduction FP1 -> écritures PTP (ordre d'écriture : 0xD18C, 0xD18D, puis 0xD190 à 0xD1A4 en montant, 0xD19C
//    juste après 0xD199, vérifié sur le boîtier ; 0xD191 est écrit avant 0xD190, pour pouvoir couper la priorité avant de fixer la plage)
// ============================================================================================================
enum Genre { case u16, i16, chaine }
struct Ecriture {
    let code: UInt16, champ: String, source: String, valeur: Int, genre: Genre
    let texte: String?, octets: Data, note: String
}
struct Plan {
    var ecritures: [Ecriture] = []
    var ignores: [(String, String)] = []     // champ du profil, raison
    var avertissements: [String] = []
    var erreurs: [String] = []
    var simulation = 0
}

func traduireProfil(_ p: Profil, emplacement: Int, drAutoZero: Bool, autreAppareil: Bool) -> Plan {
    var plan = Plan()
    func champ(_ k: String) -> String? { p.champs[k] }
    func ajoute(_ code: UInt16, _ nomChamp: String, _ source: String, _ valeur: Int, _ genre: Genre, _ note: String = "") {
        let o = octets16(valeur)    // int16 et uint16 ont les mêmes octets (complément à deux)
        plan.ecritures.append(Ecriture(code: code, champ: nomChamp, source: source, valeur: valeur, genre: genre, texte: nil, octets: o, note: note))
    }
    // réglage en « cadran » : valeur FP1 en unités de l'écran du boîtier, envoyée × 10 (entier relatif)
    func cadran(_ k: String, _ mini: Double, _ maxi: Double, demi: Bool) -> Int? {
        guard let s = champ(k) else { plan.ignores.append((k, "absent du profil : l'emplacement garde sa valeur")); return nil }
        guard let v = Double(s) else { plan.erreurs.append("\(k) : « \(s) » n'est pas un nombre"); return nil }
        guard v >= mini, v <= maxi else { plan.erreurs.append("\(k) : \(s) hors de la plage \(mini)…\(maxi) du X-T4"); return nil }
        if demi { if (v * 2).rounded() != v * 2 { plan.erreurs.append("\(k) : \(s) n'est pas un multiple de 0,5"); return nil } }
        else if v.rounded() != v { plan.erreurs.append("\(k) : \(s) n'est pas entier"); return nil }
        return Int((v * 10).rounded())
    }

    if !autreAppareil && p.appareil != "X-T4" { plan.erreurs.append("le profil est fait pour « \(p.appareil) », pas pour un X-T4 (ajouter --autre-appareil pour passer outre)") }

    // 5.1 simulation de film
    var jetonSim = champ("FilmSimulation") ?? ""
    var codeSim = 0
    if jetonSim.isEmpty { plan.erreurs.append("FilmSimulation absent") }
    else {
        var note = ""
        if let canon = simulationsAlias[jetonSim] {
            plan.avertissements.append("FilmSimulation « \(jetonSim) » est une valeur que X RAW Studio 1.28 n'écrit pas : lu comme « \(canon) » (hypothèse)")
            note = "alias de \(canon) (hypothèse)"; jetonSim = canon
        }
        if let c = simulations[jetonSim] {
            if c > simulationMax { plan.erreurs.append("FilmSimulation « \(jetonSim) » (code \(c)) : absente du X-T4 (simulations 1 à \(simulationMax))") }
            else { codeSim = c }
        } else { plan.erreurs.append("FilmSimulation : jeton « \(jetonSim) » inconnu") }
        plan.simulation = codeSim
        _ = note
    }
    let mono = simulationsMono.contains(codeSim)

    // 5.2 plage dynamique et priorité (0xD191 avant 0xD190)
    var priorite = 0, plage: Int? = nil
    if let dr = champ("DynamicRange") {
        switch dr {
        case "100", "200", "400": plage = Int(dr)
        case "AUTO":
            plage = drAutoZero ? 0 : -1
            plan.avertissements.append("DynamicRange AUTO : écrit \(drAutoZero ? "0 (fujifilm-ptp-recipes)" : "0xFFFF = -1 (zgrimz, mesuré X-T50)") en 0xD190 (hypothèse sur le X-T4)")
        case "WEAK": priorite = 1; plan.avertissements.append("DynamicRange WEAK lu comme priorité D-Range « Faible » (0xD191 = 1), valeur que X RAW Studio 1.28 n'écrit pas (hypothèse)")
        case "STRONG": priorite = 2; plan.avertissements.append("DynamicRange STRONG lu comme priorité D-Range « Forte » (0xD191 = 2), valeur que X RAW Studio 1.28 n'écrit pas (hypothèse)")
        default: plan.erreurs.append("DynamicRange : jeton « \(dr) » inconnu")
        }
    }
    if let large = champ("WideDRange"), large != "0" {
        plan.avertissements.append("WideDRange « \(large) » : sens non établi pour le bloc de l'emplacement, non écrit")
    }

    // 5.3 balance des blancs
    var wb: Int? = nil, kelvin: Int? = nil
    if let t = champ("WhiteBalance") {
        if let c = balances[t] { wb = c }
        else if t.hasSuffix("K"), let n = Int(t.dropLast()), kelvins.contains(n) {
            // ancien format (dossier V1 de presets-fuji) : le Kelvin est écrit à la place du mode de balance des blancs
            wb = 0x8007; kelvin = n
            plan.avertissements.append("WhiteBalance « \(t) » (ancien format V1) lu comme Temperature + \(n) K (hypothèse)")
        } else { plan.erreurs.append("WhiteBalance : jeton « \(t) » inconnu") }
    }
    if wb == 0x8007 && kelvin == nil {
        if let k = champ("WBColorTemp"), k.hasSuffix("K"), let n = Int(k.dropLast()), kelvins.contains(n) { kelvin = n }
        else { plan.erreurs.append("WBColorTemp « \(champ("WBColorTemp") ?? "absent") » : pas une des 31 positions du X-T4 alors que WhiteBalance = Temperature") }
    }
    var decalR: Int? = nil, decalB: Int? = nil
    for (k, estR) in [("WBShiftR", true), ("WBShiftB", false)] {
        guard let s = champ(k) else { plan.ignores.append((k, "absent du profil")); continue }
        guard let v = Int(s), (-9...9).contains(v) else { plan.erreurs.append("\(k) : « \(s) » hors de -9…+9"); continue }
        if estR { decalR = v } else { decalB = v }
    }

    // 5.4 cadrans
    let hauts = cadran("HighlightTone", -2, 4, demi: true), ombres = cadran("ShadowTone", -2, 4, demi: true)
    let couleur = cadran("Color", -4, 4, demi: false), nettete = cadran("Sharpness", -4, 4, demi: false)
    let clarte = cadran("Clarity", -5, 5, demi: false)
    var codeBruit: Int? = nil
    if let s = champ("NoisReduction") {
        if let v = Int(s), let c = bruit[v] { codeBruit = c } else { plan.erreurs.append("NoisReduction : « \(s) » hors de -4…+4") }
    }

    // 5.5 grain composite (1 à 5)
    var grain: Int? = nil
    if let g = champ("GrainEffect") {
        let grand = champ("GrainEffectSize") == "LARGE"
        switch g { case "OFF": grain = 1; case "WEAK": grain = grand ? 4 : 2; case "STRONG": grain = grand ? 5 : 3
        default: plan.erreurs.append("GrainEffect : jeton « \(g) » inconnu") }
    }
    func niveau(_ k: String) -> Int? {
        guard let s = champ(k) else { plan.ignores.append((k, "absent du profil")); return nil }
        guard let v = niveaux[s] else { plan.erreurs.append("\(k) : jeton « \(s) » inconnu"); return nil }
        return v
    }
    let chrome = niveau("ChromeEffect"), bleu = niveau("ColorChromeBlue")
    if let s = champ("SmoothSkinEffect"), s != "OFF" { plan.avertissements.append("SmoothSkinEffect « \(s) » : le X-T4 n'a pas cette fonction (vérifié sur le boîtier), non écrit") }

    // 5.6 monochrome (unités du profil non vérifiées : les 161 FP1 portent 0)
    func mono10(_ k: String) -> Int? {
        guard let s = champ(k), let v = Int(s) else { return nil }
        if v != 0 { plan.avertissements.append("\(k) = \(v) : unité du profil non vérifiée, envoyé × 10 (hypothèse)") }
        return v * 10
    }
    let toningWC = mono10("BlackImageTone"), toningMG = mono10("MonochromaticColor_RG")

    // 5.7 divers
    var lmo: Int? = nil, espace: Int? = nil
    if let s = champ("LensModulationOpt") { if s == "ON" { lmo = 1 } else if s == "OFF" { lmo = 2 } else { plan.erreurs.append("LensModulationOpt : jeton « \(s) » inconnu") } }
    if let s = champ("ColorSpace") { if s == "sRGB" { espace = 1 } else if s == "AdobeRGB" { espace = 2 } else { plan.erreurs.append("ColorSpace : jeton « \(s) » inconnu") } }

    // ---- émission dans l'ordre ----
    ajoute(0xD18C, "(emplacement)", "\(emplacement)", emplacement, .u16, "sélecteur : rappelle l'emplacement dans le boîtier")
    let nom = nomPropre(p.etiquette, repli: "Recette \(emplacement)")
    plan.ecritures.append(Ecriture(code: 0xD18D, champ: "label", source: p.etiquette, valeur: 0, genre: .chaine, texte: nom, octets: chainePTP(nom),
                                   note: nom == p.etiquette ? "chaîne PTP, \(nom.count) caractères" : "nom normalisé en « \(nom) »"))
    ajoute(0xD191, "DynamicRange", champ("DynamicRange") ?? "-", priorite, .u16, priorite == 0 ? "priorité coupée d'abord" : "priorité active : le boîtier refuse 0xD190, 0xD19D, 0xD19E")
    if priorite == 0, let v = plage { ajoute(0xD190, "DynamicRange", champ("DynamicRange") ?? "", v, .i16, v == -1 ? "Auto = 0xFFFF" : "") }
    else if priorite != 0 { plan.ignores.append(("DynamicRange", "0xD190 non écrit : refusé tant que la priorité D-Range est active")) }
    if codeSim > 0 { ajoute(0xD192, "FilmSimulation", champ("FilmSimulation") ?? "", codeSim, .u16, mono ? "monochrome : couleur non écrite" : "") }
    if mono && codeSim != 10 {
        if let v = toningWC { ajoute(0xD193, "BlackImageTone", champ("BlackImageTone") ?? "", v, .i16, "multiple de 10 seulement") }
        if let v = toningMG { ajoute(0xD194, "MonochromaticColor_RG", champ("MonochromaticColor_RG") ?? "", v, .i16, "multiple de 10 seulement") }
    } else if toningWC != nil || toningMG != nil {
        plan.ignores.append(("BlackImageTone, MonochromaticColor_RG", codeSim == 10 ? "refusés sous Sepia" : "refusés par le boîtier hors monochrome"))
    }
    if let v = grain { ajoute(0xD195, "GrainEffect+Size", "\(champ("GrainEffect") ?? "")/\(champ("GrainEffectSize") ?? "")", v, .u16, "1 off, 2 faible/petit, 3 fort/petit, 4 faible/grand, 5 fort/grand") }
    if let v = chrome { ajoute(0xD196, "ChromeEffect", champ("ChromeEffect") ?? "", v, .u16, "1 off, 2 faible, 3 fort") }
    if let v = bleu { ajoute(0xD197, "ColorChromeBlue", champ("ColorChromeBlue") ?? "", v, .u16, "1 off, 2 faible, 3 fort") }
    if let v = wb { ajoute(0xD199, "WhiteBalance", champ("WhiteBalance") ?? "", v, .u16, "") }
    if let v = kelvin {
        let ancien = (champ("WhiteBalance") ?? "").hasSuffix("K")
        ajoute(0xD19C, ancien ? "WhiteBalance (V1)" : "WBColorTemp", ancien ? (champ("WhiteBalance") ?? "") : (champ("WBColorTemp") ?? ""), v, .u16, "Kelvin, seulement avec Température")
    }
    else if let k = champ("WBColorTemp"), wb != nil { plan.ignores.append(("WBColorTemp", "\(k) ignoré : le Kelvin n'est écrit que si WhiteBalance = Temperature")) }
    if let v = decalR { ajoute(0xD19A, "WBShiftR", champ("WBShiftR") ?? "", v, .i16, "direct, sans ×10") }
    if let v = decalB { ajoute(0xD19B, "WBShiftB", champ("WBShiftB") ?? "", v, .i16, "direct, sans ×10") }
    if priorite == 0 {
        if let v = hauts { ajoute(0xD19D, "HighlightTone", champ("HighlightTone") ?? "", v, .i16, "× 10") }
        if let v = ombres { ajoute(0xD19E, "ShadowTone", champ("ShadowTone") ?? "", v, .i16, "× 10") }
    } else {
        if hauts != nil { plan.ignores.append(("HighlightTone", "non écrit : priorité D-Range active")) }
        if ombres != nil { plan.ignores.append(("ShadowTone", "non écrit : priorité D-Range active")) }
    }
    if !mono, let v = couleur { ajoute(0xD19F, "Color", champ("Color") ?? "", v, .i16, "× 10") }
    else if mono, couleur != nil { plan.ignores.append(("Color", "refusée par le boîtier sous monochrome")) }
    if let v = nettete { ajoute(0xD1A0, "Sharpness", champ("Sharpness") ?? "", v, .i16, "× 10") }
    if let v = codeBruit { ajoute(0xD1A1, "NoisReduction", champ("NoisReduction") ?? "", v, .u16, "table non linéaire") }
    if let v = clarte { ajoute(0xD1A2, "Clarity", champ("Clarity") ?? "", v, .i16, "× 10") }
    if let v = lmo { ajoute(0xD1A3, "LensModulationOpt", champ("LensModulationOpt") ?? "", v, .u16, "1 = ON, 2 = OFF") }
    if let v = espace { ajoute(0xD1A4, "ColorSpace", champ("ColorSpace") ?? "", v, .u16, "1 = sRGB, 2 = AdobeRGB") }

    // champs du profil sans écriture dans le bloc
    let sansEquivalent: [(String, String)] = [
        ("ImageSize", "0xD18E : non écrit (espaces de valeurs propres à chaque boîtier, les projets publics ne le modifient pas) ; l'emplacement garde sa valeur"),
        ("ImageQuality", "0xD18F : non écrit (idem)"), ("FileType", "sans équivalent dans le bloc de l'emplacement"),
        ("ExposureBias", "pas dans le bloc de l'emplacement"), ("WBShootCond", "sans équivalent"), ("ShootingCondition", "sans équivalent"),
        ("HDR", "sans équivalent"), ("DigitalTeleConv", "sans équivalent"), ("PreviewImage", "sans équivalent")]
    for (k, raison) in sansEquivalent where champ(k) != nil { plan.ignores.append((k, raison)) }
    return plan
}

func afficher(_ plan: Plan, _ p: Profil, court: Bool) {
    let nomFichier = (p.chemin as NSString).lastPathComponent
    if court {
        let sim = plan.simulation > 0 ? "sim \(plan.simulation)" : "sim ?"
        let etat = plan.erreurs.isEmpty ? "OK " : "ÉCHEC"
        print("\(etat) | \(nomFichier) | « \(p.etiquette) » | \(sim) | \(plan.ecritures.count) écritures | \(plan.avertissements.count) avertissement(s)" +
              (plan.erreurs.isEmpty ? "" : " | " + plan.erreurs.joined(separator: " ; ")))
        return
    }
    print("Profil : \(nomFichier) | appareil « \(p.appareil) » | version « \(p.version) » | étiquette « \(p.etiquette) »")
    print(" #  propriété                                  champ FP1 = valeur                valeur             type    octets        note")
    for (i, e) in plan.ecritures.enumerated() {
        let nomP = String(format: "0x%04X %@", e.code, nomProp(e.code) as NSString)
        let src = e.genre == .chaine ? "label = \(e.source)" : "\(e.champ) = \(e.source)"
        let val = e.genre == .chaine ? "« \(e.texte ?? "") »" : "\(e.valeur)"
        let type = e.genre == .chaine ? "chaîne" : (e.genre == .i16 ? "int16" : "uint16")
        print(String(format: "%2d  %@ %@ %@ %@ %@ %@", i + 1, nomP.padding(toLength: 42, withPad: " ", startingAt: 0) as NSString,
                     src.padding(toLength: 34, withPad: " ", startingAt: 0) as NSString, val.padding(toLength: 18, withPad: " ", startingAt: 0) as NSString,
                     type.padding(toLength: 7, withPad: " ", startingAt: 0) as NSString, hexa(e.octets, 12).padding(toLength: 12, withPad: " ", startingAt: 0) as NSString,
                     e.note as NSString))
    }
    for (k, raison) in plan.ignores { print("  non écrit : \(k) : \(raison)") }
    for a in plan.avertissements { print("  AVERTISSEMENT : \(a)") }
    for e in plan.erreurs { print("  ERREUR : \(e)") }
}

// ============================================================================================================
// 6. Transport ImageCaptureCore (même schéma que d750_ptp.swift), appels synchrones par la boucle d'exécution
// ============================================================================================================
let lectureSeule: Set<UInt16> = [0x1001, 0x1014, 0x1015, 0x1008, 0x1009, 0x1007]
let ecrituresPermises: Set<UInt16> = Set([0xD18C, 0xD18D] + Array(0xD190...0xD1A4))
var ecritureOuverte = false                       // passe à vrai dans ecrire --vraiment, nulle part ailleurs
var deleteOuvert = false                          // DeleteObject 0x100B : seulement le JPEG temporaire d'une conversion
var conversionOuverte = false                     // passe à vrai dans convertir : envoi d'un RAF, profil 0xD185, départ 0xD183
var journal: [String] = []
func note(_ s: String) { print(s); journal.append(s) }

final class Boitier: NSObject, ICDeviceBrowserDelegate, ICCameraDeviceDelegate {
    let navigateur = ICDeviceBrowser()
    var camera: ICCameraDevice?
    var sessionOuverte = false
    var erreurSession: String?
    var retire = false
    var transaction: UInt32 = 1
    var derniereErreur = ""

    func trouver(delai: TimeInterval = 20) -> Bool {
        navigateur.delegate = self
        navigateur.browsedDeviceTypeMask = ICDeviceTypeMask(rawValue: ICDeviceTypeMask.camera.rawValue | ICDeviceLocationTypeMask.local.rawValue)!
        navigateur.start()
        let limite = Date().addingTimeInterval(delai)
        while camera == nil && Date() < limite { RunLoop.main.run(until: Date().addingTimeInterval(0.2)) }
        return camera != nil
    }
    func ouvrir(delai: TimeInterval = 15) -> Bool {
        camera?.requestOpenSession()
        let limite = Date().addingTimeInterval(delai)
        while !sessionOuverte && erreurSession == nil && Date() < limite { RunLoop.main.run(until: Date().addingTimeInterval(0.1)) }
        return sessionOuverte
    }
    func fermer() {
        camera?.requestCloseSession()
        let limite = Date().addingTimeInterval(1.0)
        while Date() < limite { RunLoop.main.run(until: Date().addingTimeInterval(0.1)) }
    }
    func pause(_ s: TimeInterval) { let l = Date().addingTimeInterval(s); while Date() < l { RunLoop.main.run(until: Date().addingTimeInterval(0.01)) } }

    // Une commande PTP. Liste blanche : une lecture, ou SetDevicePropValue sur un réglage permis une fois l'écriture ouverte.
    func ptp(_ code: UInt16, _ params: [UInt32] = [], sortant: Data? = nil, delai: TimeInterval = 20) -> (Data, UInt16)? {
        if code == 0x1016 {
            let c = UInt16(truncatingIfNeeded: params.first ?? 0)
            guard (ecritureOuverte && ecrituresPermises.contains(c)) || (conversionOuverte && (c == 0xD185 || c == 0xD183)) else {
                print("REFUS INTERNE : écriture non autorisée (\(params))"); exit(70)
            }
        } else if code == 0x100B {
            guard deleteOuvert else { print("REFUS INTERNE : DeleteObject hors conversion"); exit(70) }
        } else if code == 0x900C || code == 0x900D {
            guard conversionOuverte else { print(String(format: "REFUS INTERNE : 0x%04X hors conversion", code)); exit(70) }
        } else if !lectureSeule.contains(code) {
            print(String(format: "REFUS INTERNE : opération 0x%04X hors liste blanche", code)); exit(70)
        }
        guard let b = camera, !retire else { return nil }
        for essai in 0..<6 {
            transaction += 1
            var resultat: (Data, UInt16)? = nil; var fini = false
            b.requestSendPTPCommand(commande(code, transaction: transaction, parametres: params), outData: sortant) { donnees, reponse, erreur in
                if let erreur { self.derniereErreur = "\(erreur)" }
                resultat = erreur == nil ? (sansEntete(donnees), codeReponse(reponse)) : (Data(), 0xFFFF)
                fini = true
            }
            let limite = Date().addingTimeInterval(delai)
            while !fini && Date() < limite { RunLoop.main.run(until: Date().addingTimeInterval(0.005)) }
            guard fini, let r = resultat else { journal.append(String(format: "0x%04X %@ : pas de réponse", code, params as NSArray)); return nil }
            journal.append(String(format: "0x%04X %@ out=%@ -> %@ in=%@", code, params.map { String(format: "0x%X", $0) }.joined(separator: ",") as NSString,
                                  (sortant.map { hexa($0, 40) } ?? "-") as NSString, rc(r.1) as NSString, hexa(r.0, 40) as NSString))
            if r.1 == 0x2019 && essai < 5 { pause(0.2); continue }       // boîtier occupé : on réessaie (X RAW Studio a une reprise sur occupé)
            return r
        }
        return nil
    }
    func valeur(_ prop: UInt16) -> (Data, UInt16)? { ptp(0x1015, [UInt32(prop)]) }
    func descripteur(_ prop: UInt16) -> (Descripteur?, UInt16)? {
        guard let r = ptp(0x1014, [UInt32(prop)]) else { return nil }
        return (r.1 == 0x2001 ? lireDescripteur(r.0) : nil, r.1)
    }

    func deviceBrowser(_ browser: ICDeviceBrowser, didAdd device: ICDevice, moreComing: Bool) {
        guard camera == nil, let b = device as? ICCameraDevice, (b.name ?? "").contains("X-T4") else { return }   // d'autres boîtiers peuvent être branchés
        print("Boîtier trouvé : \(b.name ?? "?")")
        camera = b; b.delegate = self
    }
    func deviceBrowser(_ browser: ICDeviceBrowser, didRemove device: ICDevice, moreGoing: Bool) {}
    func device(_ device: ICDevice, didOpenSessionWithError error: Error?) {
        if let error { erreurSession = error.localizedDescription } else { sessionOuverte = true }
    }
    func device(_ device: ICDevice, didCloseSessionWithError error: Error?) {}
    func didRemove(_ device: ICDevice) { retire = true }
    // le reste du protocole : rien à faire ici
    func cameraDevice(_ camera: ICCameraDevice, didAdd items: [ICCameraItem]) {}
    func cameraDevice(_ camera: ICCameraDevice, didRemove items: [ICCameraItem]) {}
    func cameraDevice(_ camera: ICCameraDevice, didReceiveThumbnail thumbnail: CGImage?, for item: ICCameraItem, error: Error?) {}
    func cameraDevice(_ camera: ICCameraDevice, didReceiveMetadata metadata: [AnyHashable: Any]?, for item: ICCameraItem, error: Error?) {}
    func cameraDevice(_ camera: ICCameraDevice, didRenameItems items: [ICCameraItem]) {}
    func cameraDeviceDidChangeCapability(_ camera: ICCameraDevice) {}
    func cameraDevice(_ camera: ICCameraDevice, didReceivePTPEvent eventData: Data) {}
    func deviceDidBecomeReady(withCompleteContentCatalog device: ICCameraDevice) {}
    func cameraDeviceDidRemoveAccessRestriction(_ device: ICDevice) {}
    func cameraDeviceDidEnableAccessRestriction(_ device: ICDevice) {}
}

func connecter() -> Boitier {
    let b = Boitier()
    guard b.trouver() else {
        print("Aucun X-T4 trouvé : allumé, câble USB branché, mode USB RAW CONV./BACKUP RESTORE, Photos / Transfert d'images / ptpcamerad fermés ?")
        exit(1)
    }
    guard b.ouvrir() else { print("Session refusée : \(b.erreurSession ?? "pas de réponse")"); exit(1) }
    return b
}

// dossier de sortie : hors du dépôt (une sauvegarde contient le numéro de série en clair)
func dossierSortie() -> URL {
    let f = DateFormatter(); f.dateFormat = "yyyyMMdd-HHmmss"; let h = f.string(from: Date())
    if let s = arg.valeurs["--sortie"] { return URL(fileURLWithPath: s) }
    return URL(fileURLWithPath: NSTemporaryDirectory()).appendingPathComponent("xt4-recettes/\(h)")
}
// vrai si le chemin est dans un dépôt git (un dossier .git dans l'un de ses parents)
func dansUnDepot(_ chemin: String) -> Bool {
    var dossier = URL(fileURLWithPath: chemin).standardizedFileURL.deletingLastPathComponent()
    var profondeur = 0
    while dossier.path != "/" && profondeur < 64 {
        if FileManager.default.fileExists(atPath: dossier.appendingPathComponent(".git").path) { return true }
        dossier = dossier.deletingLastPathComponent(); profondeur += 1
    }
    return false
}
func ecrireJournal(_ dossier: URL) {
    try? FileManager.default.createDirectory(at: dossier, withIntermediateDirectories: true)
    try? journal.joined(separator: "\n").write(to: dossier.appendingPathComponent("journal.txt"), atomically: true, encoding: .utf8)
}

// ---- lecture de DeviceInfo (le numéro de série n'est jamais affiché) ----
struct InfoBoitier { var fabricant = "", modele = "", version = "", operations: [UInt16] = [], reglages: [UInt16] = [] }
func lireDeviceInfo(_ d: Data) -> InfoBoitier {
    var l = Lecteur(d); var r = InfoBoitier()
    _ = l.u16(); _ = l.u32(); _ = l.u16(); _ = l.chaine(); _ = l.u16()
    r.operations = l.tableau16(); _ = l.tableau16(); r.reglages = l.tableau16(); _ = l.tableau16(); _ = l.tableau16()
    r.fabricant = l.chaine(); r.modele = l.chaine(); r.version = l.chaine()
    return r
}

// ============================================================================================================
// 7. Prérequis communs à sonde et ecrire (lecture seule)
// ============================================================================================================
struct Constat { var modeleOK = false, modeUSB: Int? = nil, famillePresente = false, ecritureAnnoncee = false, famille0x200A = false }
func constater(_ b: Boitier, bavard: Bool) -> Constat {
    var c = Constat()
    guard let (di, r1) = b.ptp(0x1001), r1 == 0x2001 else { note("GetDeviceInfo : échec"); return c }
    let info = lireDeviceInfo(di)
    c.modeleOK = info.modele.contains("X-T4")
    note("Fabricant : \(info.fabricant) | modèle : \(info.modele) | firmware : \(info.version) (la 2.12 est la dernière)")
    note("Opérations annoncées : \(info.operations.count) | réglages annoncés : \(info.reglages.count) | 0xD18C annoncé : \(info.reglages.contains(0xD18C) ? "OUI" : "non (attendu : le X-T4 ne l'annonce pas)")")
    if bavard {
        let utiles: [UInt16: String] = [0x1014: "GetDevicePropDesc", 0x1015: "GetDevicePropValue", 0x1016: "SetDevicePropValue", 0x1008: "GetObjectInfo",
                                        0x1009: "GetObject", 0x100C: "SendObjectInfo", 0x100D: "SendObject", 0x902B: "GetDeviceInfo Fuji (liste étendue)"]
        for k in utiles.keys.sorted() { note(String(format: "  0x%04X %@ : %@", k, utiles[k]! as NSString, info.operations.contains(k) ? "annoncée" : "non annoncée")) }
    }
    if let (v, r) = b.valeur(0xD16E), r == 0x2001, v.count >= 2 {
        var l = Lecteur(v); let m = Int(l.u16()); c.modeUSB = m
        let sens = [5: "tethering", 6: "USB RAW CONV./BACKUP RESTORE (le bon)", 8: "webcam"][m] ?? "inconnu"
        note("Mode USB 0xD16E : \(m) = \(sens)")
    } else { note("Mode USB 0xD16E : illisible (carte mémoire / stockage de masse ?)") }
    if let (d, r) = b.descripteur(0xD18C) {
        if r == 0x2001, let d {
            c.famillePresente = true; c.ecritureAnnoncee = d.acces == 1
            note("GetDevicePropDesc(0xD18C) : \(rc(r)) | \(d.resume)")
        } else {
            c.famille0x200A = r == 0x200A
            note("GetDevicePropDesc(0xD18C) : \(rc(r))")
            // Mesuré le 29/10/2026 sur le X-T4 2.12 : la description est refusée (0x200A) mais la valeur se lit, et les réglages
            // s'écrivent sans qu'on ait demandé leur description. La valeur lue suffit donc à dire que la famille est là.
            if let (v, r2) = b.valeur(0xD18C), r2 == 0x2001, v.count >= 2 {
                var l = Lecteur(v)
                c.famillePresente = true; c.ecritureAnnoncee = true
                note("GetDevicePropValue(0xD18C) : \(rc(r2)) | emplacement courant \(l.u16()) : la famille est là (description refusée, écriture supposée possible)")
            }
        }
    } else { note("GetDevicePropDesc(0xD18C) : pas de réponse") }
    return c
}

// ============================================================================================================
// 8. sonde : lecture seule, jamais d'écriture de 0xD18C
// ============================================================================================================
func commandeSonde() -> Never {
    let b = connecter()
    note("--- SONDE (lecture seule) ---")
    let c = constater(b, bavard: true)
    if c.famillePresente {
        note("Lecture du bloc COURANT (l'emplacement que 0xD18C indique ; ce n'est pas forcément celui du boîtier, rien n'est sélectionné) :")
        for code in [UInt16(0xD18C), 0xD18D] + Array(0xD18E...0xD1A4) {
            guard let (v, r) = b.valeur(code) else { note("  0x\(String(code, radix: 16, uppercase: true)) : pas de réponse"); continue }
            if r != 0x2001 { note(String(format: "  0x%04X %@ : %@", code, nomProp(code) as NSString, rc(r) as NSString)); continue }
            if code == 0xD18D { var l = Lecteur(v); note(String(format: "  0x%04X %@ : « %@ »", code, nomProp(code) as NSString, l.chaine() as NSString)) }
            else {
                var l = Lecteur(v); let u = Int(l.u16()); let s = Int(Int16(bitPattern: UInt16(u)))
                note(String(format: "  0x%04X %@ : %d (signé %d) [%@]", code, nomProp(code) as NSString, u, s, hexa(v, 8) as NSString))
            }
        }
        if let (d, r) = b.descripteur(0xD192), let d { note("Descripteur 0xD192 (simulation) : \(rc(r)) | \(d.resume)") }
    }
    if c.modeUSB == 6, let (oi, r) = b.ptp(0x1008, [0]) {
        if r == 0x2001 { var l = Lecteur(oi); _ = l.u32(); let fmt = l.u16(); _ = l.u16(); let taille = l.u32()
            note(String(format: "Sauvegarde des réglages (objet 0) : format 0x%04X, %u octets (à copier avec « sauvegarder », jamais à partager : numéro de série en clair)", fmt, taille)) }
        else { note("GetObjectInfo(0) : \(rc(r))") }
    }
    note("--- VERDICT ---")
    if !c.modeleOK { note("Ce n'est pas un X-T4 : l'outil refusera d'écrire.") }
    if c.modeUSB != 6 { note("Mode USB différent de 6 : choisir USB RAW CONV./BACKUP RESTORE dans le menu CONNEXION du boîtier, rebrancher, relancer.") }
    if c.famillePresente && c.ecritureAnnoncee {
        note(c.modeUSB == 6 && c.modeleOK ? "FAMILLE 0xD18C PRÉSENTE ET MODIFIABLE : « ecrire » est possible (une recette, sauvegarde faite avant)."
                                          : "Famille 0xD18C présente et modifiable, mais les autres prérequis ne sont pas réunis (voir plus haut).")
    } else if c.famillePresente { note("Famille 0xD18C présente mais en lecture seule : ne pas écrire, voir le README du dépôt.") }
    else if c.famille0x200A { note("FAMILLE 0xD18C ABSENTE (0x200A) : « ecrire » refusera. Vérifier le mode USB ; sinon plan B = fichier de sauvegarde (disposition du X-T4 non publiée, voir le README du dépôt).") }
    else { note("Verdict impossible : le boîtier n'a pas répondu à la question sur 0xD18C.") }
    ecrireJournal(dossierSortie())
    b.fermer()
    exit(c.famillePresente && c.ecritureAnnoncee && c.modeUSB == 6 && c.modeleOK ? 0 : 4)
}

// ============================================================================================================
// 9. sauvegarder : copie de l'objet 0 (lecture seule)
// ============================================================================================================
func commandeSauvegarder() -> Never {
    guard let sortie = arg.positionnels.first else { usage() }
    guard !FileManager.default.fileExists(atPath: sortie) else { print("« \(sortie) » existe déjà : on n'écrase jamais une sauvegarde."); exit(2) }
    if dansUnDepot(sortie) { print("Rappel : la sauvegarde contient le numéro de série du boîtier en clair ; elle est dans un dépôt git : la ranger ailleurs et ne jamais la publier.") }
    let b = connecter()
    note("--- SAUVEGARDE (lecture seule) ---")
    let c = constater(b, bavard: false)
    guard c.modeUSB == 6 else { note("Mode USB différent de 6 : la sauvegarde n'est servie qu'en USB RAW CONV./BACKUP RESTORE."); b.fermer(); exit(5) }
    guard let (oi, r1) = b.ptp(0x1008, [0]), r1 == 0x2001 else { note("GetObjectInfo(0) : refusé ou muet"); b.fermer(); exit(4) }
    var l = Lecteur(oi); _ = l.u32(); let fmt = l.u16(); _ = l.u16(); let taille = Int(l.u32())
    note(String(format: "Objet 0 : format 0x%04X, %d octets annoncés", fmt, taille))
    guard let (obj, r2) = b.ptp(0x1009, [0], delai: 60) else { note("GetObject(0) : pas de réponse en 60 s"); b.fermer(); exit(4) }
    guard r2 == 0x2001 else { note("GetObject(0) : \(rc(r2)), \(obj.count) octets reçus \(b.derniereErreur)"); ecrireJournal(dossierSortie()); b.fermer(); exit(4) }
    guard obj.count == taille, taille > 64 else { note("Taille reçue \(obj.count) ≠ annoncée \(taille) : rien n'est enregistré."); b.fermer(); exit(4) }
    guard obj.prefix(8) == Data("FUJIFILM".utf8) else { note("L'objet ne commence pas par FUJIFILM : rien n'est enregistré."); b.fermer(); exit(4) }
    do {
        try obj.write(to: URL(fileURLWithPath: sortie), options: .withoutOverwriting)
        try FileManager.default.setAttributes([.posixPermissions: 0o600], ofItemAtPath: sortie)
    } catch { note("Écriture du fichier impossible : \(error.localizedDescription)"); b.fermer(); exit(4) }
    let sha = SHA256.hash(data: obj).map { String(format: "%02x", $0) }.joined()
    note("Sauvegarde enregistrée : \(sortie) | \(obj.count) octets | sha256 \(sha.prefix(16))… | droits 0600")
    note("Modèle à l'octet 0x14 : « \(String(decoding: obj.subdata(in: 0x14..<min(0x14 + 16, obj.count)).prefix { $0 != 0 }, as: UTF8.self)) » (le numéro de série en 0x34 n'est pas affiché).")
    ecrireJournal(dossierSortie())
    b.fermer(); exit(0)
}

// ============================================================================================================
// 10. ecrire
// ============================================================================================================
func commandeEcrire() -> Never {
    guard arg.positionnels.count >= 2, let n = Int(arg.positionnels[0]), (1...7).contains(n) else { print("Emplacement : 1 à 7."); usage() }
    let fichier = arg.positionnels[1]
    let profil: Profil
    do { profil = try lireFP1(fichier) } catch { print("Profil illisible : \(error.localizedDescription)"); exit(2) }
    let plan = traduireProfil(profil, emplacement: n, drAutoZero: arg.drapeaux.contains("--dr-auto-zero"), autreAppareil: arg.drapeaux.contains("--autre-appareil"))
    afficher(plan, profil, court: false)
    guard plan.erreurs.isEmpty else { print("Le profil ne se traduit pas proprement : rien n'est envoyé."); exit(3) }
    guard arg.drapeaux.contains("--vraiment") else {
        print("SIMULATION : rien n'a été envoyé. Ajouter --vraiment --sauvegarde <fichier> pour écrire C\(n) (lancer « sonde » puis « sauvegarder » d'abord).")
        exit(0)
    }
    // sauvegarde complète exigée
    if let s = arg.valeurs["--sauvegarde"] {
        guard let d = FileManager.default.contents(atPath: s), d.count > 64, d.prefix(8) == Data("FUJIFILM".utf8) else {
            print("--sauvegarde « \(s) » n'est pas une sauvegarde de réglages Fujifilm (fichier absent, trop petit ou sans en-tête FUJIFILM) : arrêt."); exit(2)
        }
    } else if !arg.drapeaux.contains("--sans-sauvegarde") {
        print("Refus : pas de sauvegarde complète. Lancer « xt4_recettes sauvegarder <fichier> » puis ajouter --sauvegarde <fichier> (ou --sans-sauvegarde, à vos risques)."); exit(2)
    }
    let b = connecter()
    note("--- ÉCRITURE de C\(n) ← \(profil.etiquette) ---")
    let c = constater(b, bavard: false)
    guard c.modeleOK else { note("Refus : ce n'est pas un X-T4."); b.fermer(); exit(5) }
    guard c.modeUSB == 6 else { note("Refus : mode USB ≠ 6 (USB RAW CONV./BACKUP RESTORE)."); b.fermer(); exit(5) }
    guard c.famillePresente else { note("Refus : la famille 0xD18C est absente (\(c.famille0x200A ? "0x200A" : "pas de réponse")). Rien n'a été écrit."); b.fermer(); exit(4) }
    guard c.ecritureAnnoncee else { note("Refus : 0xD18C est en lecture seule. Rien n'a été écrit."); b.fermer(); exit(4) }
    let dossier = dossierSortie()

    // 1. mémoriser la sélection actuelle, puis l'ancien contenu de l'emplacement visé
    var selectionInitiale: Int? = nil
    if let (v, r) = b.valeur(0xD18C), r == 0x2001, v.count >= 2 { var l = Lecteur(v); selectionInitiale = Int(l.u16()) }
    note("Sélecteur 0xD18C avant : \(selectionInitiale.map(String.init) ?? "illisible")")
    ecritureOuverte = true
    guard let (_, rs) = b.ptp(0x1016, [0xD18C], sortant: octets16(n)), rs == 0x2001 else { note("Sélection de C\(n) refusée : arrêt, rien d'écrit."); ecrireJournal(dossier); b.fermer(); exit(4) }
    b.pause(0.1)
    var ancien: [String: String] = [:]
    for code in [UInt16(0xD18D)] + Array(0xD190...0xD1A4) {
        if let (v, r) = b.valeur(code), r == 0x2001 { ancien[String(format: "0x%04X", code)] = hexa(v, 64) }
    }
    try? FileManager.default.createDirectory(at: dossier, withIntermediateDirectories: true)
    if let json = try? JSONSerialization.data(withJSONObject: ["emplacement": n, "contenu_avant": ancien], options: [.prettyPrinted, .sortedKeys]) {
        try? json.write(to: dossier.appendingPathComponent("emplacement-\(n)-avant.json"))
    }
    note("Ancien contenu de C\(n) gardé dans \(dossier.path)/emplacement-\(n)-avant.json (nom, puis réglages)")

    // 2. écrire dans l'ordre du plan ; un refus 0x201C est consigné et on continue (X RAW Studio fait de même)
    var refus: [String] = [], reussies: [Ecriture] = []
    for e in plan.ecritures {
        // le X-T4 2.12 n'a pas tous les réglages du bloc (0xD198, 0xD1A3, 0xD1A4 : 0x200A en lecture) : on saute ceux qu'il n'a pas
        if e.code != 0xD18C && ancien[String(format: "0x%04X", e.code)] == nil {
            note(String(format: "  0x%04X %@ : absent sur ce boîtier, sauté", e.code, nomProp(e.code) as NSString)); continue
        }
        guard let (_, r) = b.ptp(0x1016, [UInt32(e.code)], sortant: e.octets) else { note("Plus de réponse à 0x\(String(e.code, radix: 16, uppercase: true)) : arrêt."); refus.append("0x\(String(e.code, radix: 16, uppercase: true)) muet"); break }
        if r == 0x2001 { reussies.append(e); note(String(format: "  0x%04X %@ : écrit (%@)", e.code, nomProp(e.code) as NSString, hexa(e.octets, 12) as NSString)) }
        else {
            refus.append(String(format: "0x%04X %@ : %@", e.code, nomProp(e.code) as NSString, rc(r) as NSString)); note("  " + refus.last!)
            if r != 0x201C { note("Réponse inattendue : arrêt de l'écriture (l'ancien contenu est dans le dossier de sortie)."); break }
        }
        if e.code == 0xD18C { b.pause(0.1) }
    }

    // 3. relire (en resélectionnant l'emplacement) et comparer
    var ecarts = 0
    _ = b.ptp(0x1016, [0xD18C], sortant: octets16(n)); b.pause(0.1)
    for e in reussies where e.code != 0xD18C {
        guard let (v, r) = b.valeur(e.code), r == 0x2001 else { note("  relecture 0x\(String(e.code, radix: 16, uppercase: true)) impossible"); ecarts += 1; continue }
        if e.genre == .chaine { var l = Lecteur(v); let relu = l.chaine(); if relu != e.texte { note("  ÉCART nom : écrit « \(e.texte ?? "") », relu « \(relu) »"); ecarts += 1 } }
        else { var l = Lecteur(v); let relu = Int(l.u16()); let attendu = Int(UInt16(truncatingIfNeeded: e.valeur))
            if relu != attendu { note(String(format: "  ÉCART 0x%04X %@ : écrit %d, relu %d", e.code, nomProp(e.code) as NSString, attendu, relu)); ecarts += 1 } }
    }
    // 4. remettre le sélecteur comme avant
    if let s = selectionInitiale, s != n, (1...7).contains(s) { _ = b.ptp(0x1016, [0xD18C], sortant: octets16(s)); note("Sélecteur 0xD18C remis à \(s)") }
    ecritureOuverte = false
    note("--- BILAN : \(reussies.count - 1) réglages écrits, \(refus.count) refus, \(ecarts) écart(s) à la relecture ---")
    note("À vérifier à la main dans le menu : EDIT/SAVE CUSTOM SETTING > C\(n) (nom, simulation, grain, balance des blancs), puis éteindre/rallumer et relire avec « sonde ».")
    ecrireJournal(dossier)
    b.fermer()
    exit(refus.isEmpty && ecarts == 0 ? 0 : 6)
}

// ============================================================================================================
// 11. traduire (sans boîtier)
// ============================================================================================================
func commandeTraduire() -> Never {
    guard !arg.positionnels.isEmpty else { usage() }
    var fichiers: [String] = []
    for p in arg.positionnels {
        var estDossier: ObjCBool = false
        if FileManager.default.fileExists(atPath: p, isDirectory: &estDossier), estDossier.boolValue {
            let liste = (try? FileManager.default.contentsOfDirectory(atPath: p)) ?? []
            fichiers += liste.filter { $0.lowercased().hasSuffix(".fp1") }.sorted().map { (p as NSString).appendingPathComponent($0) }
        } else { fichiers.append(p) }
    }
    let emplacement = Int(arg.valeurs["--emplacement"] ?? "1") ?? 1
    let court = arg.drapeaux.contains("--court")
    var echecs = 0, avertissements: [String: Int] = [:]
    for f in fichiers {
        do {
            let p = try lireFP1(f)
            let plan = traduireProfil(p, emplacement: emplacement, drAutoZero: arg.drapeaux.contains("--dr-auto-zero"), autreAppareil: arg.drapeaux.contains("--autre-appareil"))
            afficher(plan, p, court: court)
            if !plan.erreurs.isEmpty { echecs += 1 }
            for a in plan.avertissements { avertissements[String(a.prefix(60)), default: 0] += 1 }
        } catch {
            echecs += 1; print("ÉCHEC | \((f as NSString).lastPathComponent) | \(error.localizedDescription)")
        }
        if !court { print("") }
    }
    print("\(fichiers.count) profil(s) lus, \(echecs) échec(s).")
    for (k, v) in avertissements.sorted(by: { $0.key < $1.key }) { print("  avertissement × \(v) : \(k)…") }
    exit(echecs == 0 ? 0 : 1)
}

// ============================================================================================================
// 12. autotest (sans boîtier) : encodages contrôlés sur des vecteurs connus
// ============================================================================================================
func commandeAutotest() -> Never {
    var faux = 0
    func verifie(_ nom: String, _ ok: Bool) { if !ok { faux += 1; print("ÉCHEC autotest : \(nom)") } }
    verifie("chaîne PTP « C1 » = 03 43 00 31 00 00 00 (name-rules.md)", chainePTP("C1") == Data([0x03, 0x43, 0x00, 0x31, 0x00, 0x00, 0x00]))
    verifie("chaîne PTP vide", chainePTP("") == Data([0]))
    verifie("int16 -10 = F6 FF", octets16(-10) == Data([0xF6, 0xFF]))
    verifie("DR Auto -1 = FF FF", octets16(-1) == Data([0xFF, 0xFF]))
    verifie("bruit -4 = 0x8000 et 0 = 0x2000", bruit[-4] == 0x8000 && bruit[0] == 0x2000)
    verifie("nom normalisé", nomPropre("Café \u{2013} été «x»", repli: "R") == "Cafe - ete x")
    verifie("nom tronqué à 25", nomPropre(String(repeating: "abcde ", count: 10), repli: "R").count <= 25)
    // GetDevicePropDesc synthétique : 0xD18C, uint16, lecture/écriture, défaut 1, courant 3, liste 1..7
    var d = Data(); d += octets16(0xD18C); d += octets16(4); d.append(1); d += octets16(1); d += octets16(3); d.append(2); d += octets16(7)
    for i in 1...7 { d += octets16(i) }
    let desc = lireDescripteur(d)
    verifie("descripteur 0xD18C", desc?.code == 0xD18C && desc?.courant == 3 && desc?.forme == "liste" && desc?.valeurs == [1, 2, 3, 4, 5, 6, 7] && desc?.acces == 1)
    // profil d'essai
    let fp1 = """
    <ConversionProfile application="XRFC" version="1.12.0.0"><PropertyGroup device="X-T4" version="X-T4_0100" label="R&D test">
    <FilmSimulation>Classic</FilmSimulation><DynamicRange>200</DynamicRange><WideDRange>0</WideDRange><GrainEffect>STRONG</GrainEffect>
    <GrainEffectSize>LARGE</GrainEffectSize><ChromeEffect>WEAK</ChromeEffect><ColorChromeBlue>OFF</ColorChromeBlue><WhiteBalance>Temperature</WhiteBalance>
    <WBColorTemp>5300K</WBColorTemp><WBShiftR>2</WBShiftR><WBShiftB>-3</WBShiftB><HighlightTone>-1</HighlightTone><ShadowTone>2</ShadowTone>
    <Color>3</Color><Sharpness>-2</Sharpness><NoisReduction>-4</NoisReduction><Clarity>0</Clarity><LensModulationOpt>ON</LensModulationOpt>
    <ColorSpace>sRGB</ColorSpace></PropertyGroup></ConversionProfile>
    """
    let tmp = NSTemporaryDirectory() + "xt4_autotest.fp1"
    try? fp1.write(toFile: tmp, atomically: true, encoding: .utf8)
    if let p = try? lireFP1(tmp) {
        verifie("étiquette avec & non échappé", p.etiquette == "R&D test")
        let plan = traduireProfil(p, emplacement: 5, drAutoZero: false, autreAppareil: false)
        verifie("aucune erreur", plan.erreurs.isEmpty)
        func val(_ c: UInt16) -> Int? { plan.ecritures.first { $0.code == c }?.valeur }
        verifie("D18C = 5", val(0xD18C) == 5)
        verifie("D192 Classic = 11", val(0xD192) == 11)
        verifie("D190 = 200 et D191 = 0", val(0xD190) == 200 && val(0xD191) == 0)
        verifie("D195 fort/grand = 5", val(0xD195) == 5)
        verifie("D196 faible = 2, D197 off = 1", val(0xD196) == 2 && val(0xD197) == 1)
        verifie("D199 = 0x8007 et D19C = 5300", val(0xD199) == 0x8007 && val(0xD19C) == 5300)
        verifie("décalages BB 2 / -3 sans ×10", val(0xD19A) == 2 && val(0xD19B) == -3)
        verifie("tons × 10", val(0xD19D) == -10 && val(0xD19E) == 20 && val(0xD19F) == 30 && val(0xD1A0) == -20)
        verifie("bruit -4 = 0x8000", val(0xD1A1) == 0x8000)
        let ordre = plan.ecritures.map { $0.code }
        verifie("D199 < D19C < D19A dans l'ordre", ordre.firstIndex(of: 0xD199)! < ordre.firstIndex(of: 0xD19C)! && ordre.firstIndex(of: 0xD19C)! < ordre.firstIndex(of: 0xD19A)!)
        verifie("D191 avant D190", ordre.firstIndex(of: 0xD191)! < ordre.firstIndex(of: 0xD190)!)
    } else { verifie("lecture du profil d'essai", false) }
    try? FileManager.default.removeItem(atPath: tmp)
    print(faux == 0 ? "autotest OK" : "autotest : \(faux) échec(s)")
    exit(faux == 0 ? 0 : 1)
}

// ============================================================================================================
// balayer : quels réglages répondent à GetDevicePropDesc entre deux codes (lecture seule, ajouté le 29/10/2026 :
// un X-T4 (firmware 2.12) répond 0x200A sur 0xD18C, on cherche où sont les réglages perso)
// ============================================================================================================
func commandeBalayer() -> Never {
    func code(_ i: Int, _ defaut: UInt16) -> UInt16 {
        guard i < arg.positionnels.count else { return defaut }
        return UInt16(arg.positionnels[i].lowercased().replacingOccurrences(of: "0x", with: ""), radix: 16) ?? defaut
    }
    let debut = code(0, 0xD000), fin = max(code(1, 0xD3FF), debut)
    let b = connecter()
    note(String(format: "--- BALAYAGE 0x%04X à 0x%04X (lecture seule) ---", debut, fin))
    var presents = 0
    for c in debut...fin {
        guard let (d, r) = b.descripteur(c) else { note(String(format: "  0x%04X : pas de réponse", c)); continue }
        if r == 0x2001 { presents += 1; note(String(format: "  0x%04X %@ : %@", c, nomProp(c) as NSString, (d?.resume ?? "descripteur illisible") as NSString)) }
        else if r != 0x200A { note(String(format: "  0x%04X : %@", c, rc(r) as NSString)) }
    }
    note(String(format: "%d réglage(s) présents entre 0x%04X et 0x%04X", presents, debut, fin))
    ecrireJournal(dossierSortie())
    b.fermer()
    exit(0)
}

// remettre : réécrit dans un emplacement le contenu gardé par « ecrire » (emplacement-N-avant.json), octets tels que lus
func commandeRemettre() -> Never {
    guard arg.positionnels.count >= 2, let n = Int(arg.positionnels[0]), (1...7).contains(n) else { print("remettre <1-7> <emplacement-N-avant.json> --vraiment"); exit(2) }
    guard let d = FileManager.default.contents(atPath: arg.positionnels[1]),
          let j = try? JSONSerialization.jsonObject(with: d) as? [String: Any], let avant = j["contenu_avant"] as? [String: String] else { print("Fichier illisible."); exit(2) }
    var ecritures: [(UInt16, Data)] = []
    for (k, v) in avant.sorted(by: { $0.key < $1.key }) {
        guard let code = UInt16(k.replacingOccurrences(of: "0x", with: ""), radix: 16), !v.contains("…") else { print("Valeur tronquée pour \(k) : arrêt."); exit(2) }
        ecritures.append((code, Data(v.split(separator: " ").compactMap { UInt8($0, radix: 16) })))
    }
    for (c, o) in ecritures { print(String(format: "  0x%04X %@ <- %@", c, nomProp(c) as NSString, hexa(o, 32) as NSString)) }
    guard arg.drapeaux.contains("--vraiment") else { print("SIMULATION : rien n'a été envoyé (ajouter --vraiment)."); exit(0) }
    let b = connecter()
    note("--- REMISE de C\(n) ---")
    let c = constater(b, bavard: false)
    guard c.modeleOK, c.modeUSB == 6, c.famillePresente else { note("Prérequis absents : rien n'a été écrit."); b.fermer(); exit(4) }
    ecritureOuverte = true
    guard let (_, rs) = b.ptp(0x1016, [0xD18C], sortant: octets16(n)), rs == 0x2001 else { note("Sélection refusée : rien d'écrit."); b.fermer(); exit(4) }
    b.pause(0.1)
    var refus = 0
    for (code, o) in ecritures {
        guard let (_, r) = b.ptp(0x1016, [UInt32(code)], sortant: o) else { note("Plus de réponse : arrêt."); refus += 1; break }
        note(String(format: "  0x%04X %@ : %@", code, nomProp(code) as NSString, rc(r) as NSString)); if r != 0x2001 { refus += 1 }
    }
    ecritureOuverte = false
    note("--- BILAN : \(ecritures.count - refus) remis, \(refus) refus ---")
    ecrireJournal(dossierSortie()); b.fermer(); exit(refus == 0 ? 0 : 6)
}

// relire : après extinction et rallumage, chaque emplacement relu contre son .FP1. Seul le sélecteur 0xD18C est écrit, puis remis.
func commandeRelire() -> Never {
    let p = arg.positionnels
    guard p.count >= 2, p.count % 2 == 0 else { print("relire <1-7> <fichier.FP1> [<1-7> <fichier.FP1> …]"); exit(2) }
    var plans: [(Int, Plan, String)] = []
    for i in stride(from: 0, to: p.count, by: 2) {
        guard let n = Int(p[i]), (1...7).contains(n), let profil = try? lireFP1(p[i + 1]) else { print("Argument illisible : \(p[i]) \(p[i + 1])"); exit(2) }
        plans.append((n, traduireProfil(profil, emplacement: n, drAutoZero: false, autreAppareil: false), profil.etiquette))
    }
    let b = connecter()
    note("--- RELECTURE ---")
    let c = constater(b, bavard: false)
    guard c.modeleOK, c.modeUSB == 6, c.famillePresente else { note("Prérequis absents : rien n'a été relu."); b.fermer(); exit(4) }
    var selection: Int? = nil
    if let (v, r) = b.valeur(0xD18C), r == 0x2001, v.count >= 2 { var l = Lecteur(v); selection = Int(l.u16()) }
    var ecarts = 0
    ecritureOuverte = true
    for (n, plan, etiquette) in plans {
        guard let (_, rs) = b.ptp(0x1016, [0xD18C], sortant: octets16(n)), rs == 0x2001 else { note("Sélection de C\(n) refusée."); ecarts += 1; continue }
        b.pause(0.1)
        var lus = 0, e = 0
        for x in plan.ecritures where x.code != 0xD18C {
            guard let (v, r) = b.valeur(x.code), r == 0x2001 else { continue }      // réglage absent sur ce boîtier
            lus += 1
            var l = Lecteur(v)
            if x.genre == .chaine {
                let relu = l.chaine()
                if relu != x.texte { note("  ÉCART C\(n) nom : attendu « \(x.texte ?? "") », relu « \(relu) »"); e += 1 }
                continue
            }
            let relu = Int(l.u16()), attendu = Int(UInt16(truncatingIfNeeded: x.valeur))
            if relu == attendu || (x.code == 0xD195 && attendu == 1 && relu == 6) { continue }   // grain off : 1 écrit, 6 relu (29/10/2026)
            note(String(format: "  ÉCART C%d 0x%04X %@ : attendu %d, relu %d", n, x.code, nomProp(x.code) as NSString, attendu, relu)); e += 1
        }
        note("C\(n) « \(etiquette) » : \(lus) réglages relus, \(e) écart(s)")
        ecarts += e
    }
    if let s = selection, (1...7).contains(s) { _ = b.ptp(0x1016, [0xD18C], sortant: octets16(s)); note("Sélecteur 0xD18C remis à \(s)") }
    ecritureOuverte = false
    note("--- BILAN RELECTURE : \(plans.count) emplacements, \(ecarts) écart(s) ---")
    ecrireJournal(dossierSortie()); b.fermer(); exit(ecarts == 0 ? 0 : 6)
}

// convertir : le boîtier développe un RAF (du X-T4) et rend un JPEG ; séquence de FilmKit (src/ptp/session.ts) :
// SendObjectInfo 0x900C (format 0xF802), SendObject2 0x900D, profil 0xD185 lu puis renvoyé (ou remplacé par --profil),
// départ 0xD183 = 0, attente d'un nouvel objet, GetObject. Rien n'est jamais effacé (pas de DeleteObject).
func commandeConvertir() -> Never {
    guard arg.positionnels.count >= 2 else { print("convertir <fichier.RAF> <sortie.jpg> [--profil <d185.bin>]"); exit(2) }
    let raf = arg.positionnels[0], sortie = arg.positionnels[1]
    guard let donnees = FileManager.default.contents(atPath: raf), donnees.count > 1_000_000 else { print("RAF illisible : \(raf)"); exit(2) }
    guard !FileManager.default.fileExists(atPath: sortie) else { print("« \(sortie) » existe déjà."); exit(2) }
    let b = connecter()
    note("--- CONVERSION par le boîtier : \((raf as NSString).lastPathComponent) (\(donnees.count / 1_048_576) Mo) ---")
    let c = constater(b, bavard: false)
    guard c.modeleOK, c.modeUSB == 6 else { note("Prérequis absents (X-T4, mode USB RAW CONV.)."); b.fermer(); exit(4) }
    func poignees() -> Set<UInt32> {
        guard let (d, r) = b.ptp(0x1007, [0xFFFFFFFF, 0, 0]), r == 0x2001, d.count >= 4 else { return [] }
        var l = Lecteur(d); let n = Int(l.u32()); var s = Set<UInt32>()
        for _ in 0..<min(n, (d.count - 4) / 4) { s.insert(l.u32()) }
        return s
    }
    // Un JPEG de conversion précédente resté dans le boîtier bloque la suivante (mesuré le 29/10/2026). En mode USB RAW CONV.
    // le boîtier ne montre aucune photo de la carte (0 objet avant la première conversion) : un JPEG visible ici (0x3801,
    // stockage 0x10000001, « DSCF0001.jpg », taille d'un rendu) est un résultat de conversion. On n'efface que ça.
    func infoObjet(_ h: UInt32) -> (stockage: UInt32, format: UInt16, taille: UInt32, nom: String)? {
        guard let (d, r) = b.ptp(0x1008, [h]), r == 0x2001, d.count > 53 else { return nil }
        var l = Lecteur(d); let st = l.u32(); let fmt = l.u16(); _ = l.u16(); let tl = l.u32()
        var l2 = Lecteur(d.subdata(in: d.startIndex + 52..<d.endIndex)); return (st, fmt, tl, l2.chaine())
    }
    var avant = poignees()
    for h in avant.sorted() {
        guard let i = infoObjet(h) else { note(String(format: "Objet 0x%08X : description illisible, laissé", h)); continue }
        note(String(format: "Objet 0x%08X : stockage 0x%08X, format 0x%04X, %u octets, « %@ »", h, i.stockage, i.format, i.taille, i.nom as NSString))
        if c.modeUSB == 6 && i.format == 0x3801 {
            deleteOuvert = true; let r = b.ptp(0x100B, [h]); deleteOuvert = false
            note("  JPEG de conversion resté dans le boîtier : effacé (\(r.map { rc($0.1) } ?? "muet"))")
        }
    }
    avant = poignees()
    note("Objets avant : \(avant.count)")
    conversionOuverte = true
    var info = Data()
    func a16(_ v: UInt16) { var x = v.littleEndian; info.append(Data(bytes: &x, count: 2)) }
    func a32(_ v: UInt32) { var x = v.littleEndian; info.append(Data(bytes: &x, count: 4)) }
    a32(0); a16(0xF802); a16(0); a32(UInt32(donnees.count)); a16(0); a32(0); a32(0); a32(0); a32(0); a32(0); a32(0); a32(0); a16(0); a32(0); a32(0)
    info.append(chainePTP("FUP_FILE.dat")); info.append(contentsOf: [0, 0, 0])
    guard let (_, r1) = b.ptp(0x900C, [0, 0, 0], sortant: info), r1 == 0x2001 else { note("SendObjectInfo 0x900C refusé ou muet."); ecrireJournal(dossierSortie()); b.fermer(); exit(4) }
    let t0 = Date()
    guard let (_, r2) = b.ptp(0x900D, [], sortant: donnees, delai: 180), r2 == 0x2001 else { note("Envoi du RAF 0x900D refusé ou muet."); ecrireJournal(dossierSortie()); b.fermer(); exit(4) }
    note(String(format: "RAF envoyé en %.1f s", Date().timeIntervalSince(t0)))
    guard let (profil, r3) = b.valeur(0xD185), r3 == 0x2001, profil.count > 100 else { note("Profil 0xD185 illisible."); ecrireJournal(dossierSortie()); b.fermer(); exit(4) }
    let dossier = dossierSortie(); try? FileManager.default.createDirectory(at: dossier, withIntermediateDirectories: true)
    try? profil.write(to: dossier.appendingPathComponent("d185-du-raf.bin"))
    note("Profil 0xD185 du RAF : \(profil.count) octets, gardé dans \(dossier.path)/d185-du-raf.bin")
    var envoi = profil
    if let p = arg.valeurs["--profil"] {
        guard let d = FileManager.default.contents(atPath: p), d.count == profil.count else { note("Profil --profil illisible ou de taille différente (\(profil.count) attendus)."); b.fermer(); exit(2) }
        envoi = d; note("Profil remplacé par \(p)")
    }
    guard let (_, r4) = b.ptp(0x1016, [0xD185], sortant: envoi), r4 == 0x2001 else { note("Envoi du profil refusé."); ecrireJournal(dossier); b.fermer(); exit(4) }
    let t1 = Date()
    guard let (_, r5) = b.ptp(0x1016, [0xD183], sortant: octets16(0)), r5 == 0x2001 else { note("Départ de la conversion refusé."); ecrireJournal(dossier); b.fermer(); exit(4) }
    var resultat: UInt32? = nil
    while resultat == nil && Date().timeIntervalSince(t1) < 60 { b.pause(0.5); resultat = poignees().subtracting(avant).first }
    guard let h = resultat else { note("Aucun JPEG apparu en 60 s."); ecrireJournal(dossier); b.fermer(); exit(4) }
    guard let (jpeg, r6) = b.ptp(0x1009, [h], delai: 60), r6 == 0x2001, jpeg.count > 1000 else { note("JPEG illisible."); ecrireJournal(dossier); b.fermer(); exit(4) }
    conversionOuverte = false
    if let i = infoObjet(h), i.format == 0x3801 { deleteOuvert = true; _ = b.ptp(0x100B, [h]); deleteOuvert = false }
    do { try jpeg.write(to: URL(fileURLWithPath: sortie), options: .withoutOverwriting) } catch { note("Écriture impossible : \(error.localizedDescription)"); b.fermer(); exit(4) }
    note(String(format: "JPEG du boîtier : %@ (%d Ko), conversion en %.1f s", sortie, jpeg.count / 1024, Date().timeIntervalSince(t1)))
    ecrireJournal(dossier); b.fermer(); exit(0)
}

// lire : GetDevicePropValue sur des codes donnés (lecture seule) ; le X-T4 refuse GetDevicePropDesc(0xD18C), la valeur
// passe-t-elle quand même ?
func commandeLire() -> Never {
    let codes = arg.positionnels.compactMap { UInt16($0.lowercased().replacingOccurrences(of: "0x", with: ""), radix: 16) }
    guard !codes.isEmpty else { usage() }
    let b = connecter()
    note("--- LECTURE (lecture seule) ---")
    for c in codes {
        guard let (v, r) = b.valeur(c) else { note(String(format: "  0x%04X : pas de réponse", c)); continue }
        note(String(format: "  0x%04X %@ : %@ | %d octets [%@]", c, nomProp(c) as NSString, rc(r) as NSString, v.count, hexa(v, 32) as NSString))
    }
    ecrireJournal(dossierSortie())
    b.fermer()
    exit(0)
}

switch arg.commande {
case "remettre": commandeRemettre()
case "relire": commandeRelire()
case "convertir": commandeConvertir()
case "lire": commandeLire()
case "balayer": commandeBalayer()
case "sonde": commandeSonde()
case "traduire": commandeTraduire()
case "ecrire": commandeEcrire()
case "sauvegarder": commandeSauvegarder()
case "autotest": commandeAutotest()
default: usage()
}
