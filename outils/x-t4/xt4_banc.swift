// SPDX-License-Identifier: CC-BY-NC-4.0
// Copyright (c) 2026 Thomas Hammoudi
// Banc de mesure du X-T4 : le boîtier développe un RAF avec des dizaines de profils de conversion à la suite, dans une seule
// session PTP. Mêmes opérations que « xt4_recettes convertir » (séquence de FilmKit, src/ptp/session.ts, loadRaf puis
// reconvert), mais le RAF n'est envoyé qu'une fois : chaque rendu suivant ne coûte que l'envoi du profil 0xD185, le départ
// 0xD183 et la lecture du JPEG (environ 1 s au lieu de 3).
//
//   swiftc -O -swift-version 5 outils/x-t4/xt4_banc.swift -o <dossier hors du dépôt>/xt4_banc
//   xt4_banc            puis des commandes sur l'entrée standard, une par ligne, champs séparés par une tabulation
//                       (les chemins ont des espaces ; piloté par xt4_mesure.py) :
//     charger <fichier.RAF> <profil-de-base.bin>    envoie le RAF, lit son profil 0xD185 et l'écrit dans le fichier donné
//     rendre <profil.bin> <sortie.jpg>              envoie ce profil, fait développer, écrit le JPEG
//     fin
//   Chaque commande répond une ligne « OK … » ou « ERR … » sur la sortie standard.
//
// Garde-fous : aucun réglage du boîtier n'est écrit. SetDevicePropValue n'est permis que sur 0xD185 (profil de conversion) et
// 0xD183 (départ de la conversion), SendObjectInfo/SendObject2 seulement pour un RAF, DeleteObject seulement sur un JPEG de
// conversion (format 0x3801) ou sur le RAF envoyé par l'outil lui-même (FUP_FILE.dat, avant l'envoi du suivant) ; toute autre
// opération hors lecture arrête le programme. Jamais en parallèle d'un autre outil.
import Foundation
import ImageCaptureCore

func commande(_ code: UInt16, transaction: UInt32, parametres: [UInt32] = []) -> Data {
    var d = Data()
    func ajoute<T: FixedWidthInteger>(_ v: T) { withUnsafeBytes(of: v.littleEndian) { d.append(contentsOf: $0) } }
    ajoute(UInt32(12 + 4 * parametres.count)); ajoute(UInt16(1)); ajoute(code); ajoute(transaction)
    parametres.forEach { ajoute($0) }
    return d
}
func sansEntete(_ p: Data) -> Data {
    if p.count >= 12, p[p.startIndex + 4] == 2, Int(p[p.startIndex]) | Int(p[p.startIndex + 1]) << 8 | Int(p[p.startIndex + 2]) << 16 == p.count {
        return p.subdata(in: (p.startIndex + 12)..<p.endIndex)
    }
    return p
}
func codeReponse(_ r: Data) -> UInt16 { r.count >= 8 ? UInt16(r[r.startIndex + 6]) | UInt16(r[r.startIndex + 7]) << 8 : 0 }
func u32(_ d: Data, _ o: Int) -> UInt32 { (0..<4).reduce(UInt32(0)) { $0 | UInt32(d[d.startIndex + o + $1]) << (8 * UInt32($1)) } }
func u16(_ d: Data, _ o: Int) -> UInt16 { UInt16(d[d.startIndex + o]) | UInt16(d[d.startIndex + o + 1]) << 8 }
func chainePTP(_ s: String) -> Data {
    let u = Array(s.utf16) + [0]; var d = Data([UInt8(u.count)])
    for c in u { d.append(UInt8(c & 0xFF)); d.append(UInt8(c >> 8)) }
    return d
}
func dire(_ s: String) { print(s); fflush(stdout) }

let lectures: Set<UInt16> = [0x1001, 0x1007, 0x1008, 0x1009, 0x1015]
var effacementPermis = false

final class Boitier: NSObject, ICDeviceBrowserDelegate, ICCameraDeviceDelegate {
    let navigateur = ICDeviceBrowser()
    var camera: ICCameraDevice?
    var ouverte = false, erreur: String?, retire = false
    var transaction: UInt32 = 1

    func trouver() -> Bool {
        navigateur.delegate = self
        navigateur.browsedDeviceTypeMask = ICDeviceTypeMask(rawValue: ICDeviceTypeMask.camera.rawValue | ICDeviceLocationTypeMask.local.rawValue)!
        navigateur.start()
        let l = Date().addingTimeInterval(20)
        while camera == nil && Date() < l { RunLoop.main.run(until: Date().addingTimeInterval(0.2)) }
        guard camera != nil else { return false }
        camera?.requestOpenSession()
        let l2 = Date().addingTimeInterval(15)
        while !ouverte && erreur == nil && Date() < l2 { RunLoop.main.run(until: Date().addingTimeInterval(0.1)) }
        return ouverte
    }
    func fermer() {
        camera?.requestCloseSession()
        let l = Date().addingTimeInterval(1.0)
        while Date() < l { RunLoop.main.run(until: Date().addingTimeInterval(0.1)) }
    }
    func pause(_ s: TimeInterval) { let l = Date().addingTimeInterval(s); while Date() < l { RunLoop.main.run(until: Date().addingTimeInterval(0.01)) } }

    func ptp(_ code: UInt16, _ params: [UInt32] = [], sortant: Data? = nil, delai: TimeInterval = 30) -> (Data, UInt16)? {
        switch code {
        case 0x1016:
            let p = UInt16(truncatingIfNeeded: params.first ?? 0)
            guard p == 0xD185 || p == 0xD183 else { dire("ERR refus interne : écriture de 0x\(String(p, radix: 16))"); exit(70) }
        case 0x100B: guard effacementPermis else { dire("ERR refus interne : DeleteObject"); exit(70) }
        case 0x900C, 0x900D: break
        default: guard lectures.contains(code) else { dire("ERR refus interne : opération 0x\(String(code, radix: 16))"); exit(70) }
        }
        guard let b = camera, !retire else { return nil }
        for essai in 0..<6 {
            transaction += 1
            var res: (Data, UInt16)? = nil; var fini = false
            b.requestSendPTPCommand(commande(code, transaction: transaction, parametres: params), outData: sortant) { d, r, e in
                res = e == nil ? (sansEntete(d), codeReponse(r)) : (Data(), 0xFFFF); fini = true
            }
            let l = Date().addingTimeInterval(delai)
            while !fini && Date() < l { RunLoop.main.run(until: Date().addingTimeInterval(0.003)) }
            guard fini, let r = res else { return nil }
            if r.1 == 0x2019 && essai < 5 { pause(0.2); continue }
            return r
        }
        return nil
    }
    func deviceBrowser(_ browser: ICDeviceBrowser, didAdd device: ICDevice, moreComing: Bool) {
        guard camera == nil, let b = device as? ICCameraDevice, (b.name ?? "").contains("X-T4") else { return }
        camera = b; b.delegate = self
    }
    func deviceBrowser(_ browser: ICDeviceBrowser, didRemove device: ICDevice, moreGoing: Bool) {}
    func device(_ device: ICDevice, didOpenSessionWithError error: Error?) { if let error { erreur = "\(error)" } else { ouverte = true } }
    func device(_ device: ICDevice, didCloseSessionWithError error: Error?) {}
    func didRemove(_ device: ICDevice) { retire = true }
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

let b = Boitier()
guard b.trouver() else { dire("ERR aucun X-T4 (allumé, câble branché, USB RAW CONV. ?)"); exit(1) }
// prérequis : un X-T4 en mode USB RAW CONV. (0xD16E = 6)
guard let (mode, rm) = b.ptp(0x1015, [0xD16E]), rm == 0x2001, mode.count >= 2, u16(mode, 0) == 6 else {
    dire("ERR mode USB différent de RAW CONV./BACKUP RESTORE"); b.fermer(); exit(4)
}

func poignees() -> [UInt32] {
    guard let (d, r) = b.ptp(0x1007, [0xFFFFFFFF, 0, 0]), r == 0x2001, d.count >= 4 else { return [] }
    let n = Int(u32(d, 0)); return (0..<min(n, (d.count - 4) / 4)).map { u32(d, 4 + 4 * $0) }
}
func formatObjet(_ h: UInt32) -> UInt16? {
    guard let (d, r) = b.ptp(0x1008, [h]), r == 0x2001, d.count > 8 else { return nil }
    return u16(d, 4)
}
// un JPEG de conversion resté dans le boîtier bloque la suivante : on n'efface que ça (format 0x3801)
func nettoyer() {
    for h in poignees() where formatObjet(h) == 0x3801 { effacementPermis = true; _ = b.ptp(0x100B, [h]); effacementPermis = false }
}
// RAF envoyé (SendObjectInfo « FUP_FILE.dat », format 0xF802) : jamais effacé jusqu'au 29/10/2026. S'il reste visible dans
// le boîtier, il est effacé avant l'envoi du RAF suivant (jamais pendant ses rendus : la conversion en a besoin)
func nomObjet(_ h: UInt32) -> String? {
    guard let (d, r) = b.ptp(0x1008, [h]), r == 0x2001, d.count > 53 else { return nil }
    let n = Int(d[d.startIndex + 52]); guard n > 0, d.count >= 53 + 2 * n else { return "" }
    let u = (0..<n).map { UInt16(d[d.startIndex + 53 + 2 * $0]) | UInt16(d[d.startIndex + 54 + 2 * $0]) << 8 }
    return String(utf16CodeUnits: u.filter { $0 != 0 }, count: u.filter { $0 != 0 }.count)
}
func objetsRAF() -> [UInt32] {
    poignees().filter { h in formatObjet(h) == 0xF802 || (nomObjet(h) ?? "").uppercased().hasPrefix("FUP_FILE") }
}
var envois = 0
nettoyer()
dire("OK prêt")

var charge = false, tailleProfil = 0
while let ligne = readLine() {
    let t = ligne.split(separator: "\t", omittingEmptySubsequences: false).map(String.init)
    guard let cmd = t.first else { continue }
    if b.retire { dire("ERR boîtier débranché"); exit(5) }
    if cmd == "fin" { break }
    if cmd == "charger", t.count == 3 {
        guard let raf = FileManager.default.contents(atPath: t[1]), raf.count > 1_000_000 else { dire("ERR RAF illisible"); continue }
        nettoyer()
        var effaces = 0, codes: [String] = []
        for h in objetsRAF() {
            effacementPermis = true; let c = b.ptp(0x100B, [h])?.1 ?? 0; effacementPermis = false
            codes.append(String(format: "0x%04X", c)); if c == 0x2001 { effaces += 1 }
        }
        var info = Data()
        func a16(_ v: UInt16) { var x = v.littleEndian; info.append(Data(bytes: &x, count: 2)) }
        func a32(_ v: UInt32) { var x = v.littleEndian; info.append(Data(bytes: &x, count: 4)) }
        a32(0); a16(0xF802); a16(0); a32(UInt32(raf.count)); a16(0); a32(0); a32(0); a32(0); a32(0); a32(0); a32(0); a32(0); a16(0); a32(0); a32(0)
        info.append(chainePTP("FUP_FILE.dat")); info.append(contentsOf: [0, 0, 0])
        guard let (_, r1) = b.ptp(0x900C, [0, 0, 0], sortant: info), r1 == 0x2001 else { dire("ERR SendObjectInfo"); continue }
        guard let (_, r2) = b.ptp(0x900D, [], sortant: raf, delai: 180), r2 == 0x2001 else { dire("ERR SendObject2"); continue }
        guard let (p, r3) = b.ptp(0x1015, [0xD185]), r3 == 0x2001, p.count > 100 else { dire("ERR profil 0xD185 illisible"); continue }
        do { try p.write(to: URL(fileURLWithPath: t[2])) } catch { dire("ERR écriture du profil"); continue }
        charge = true; tailleProfil = p.count; envois += 1
        dire("OK chargé \(p.count) objets=\(poignees().count) fup=\(objetsRAF().count) envois=\(envois) fup_effaces=\(effaces) codes=\(codes.joined(separator: ","))")
    } else if cmd == "rendre", t.count == 3 {
        guard charge else { dire("ERR aucun RAF chargé"); continue }
        guard let p = FileManager.default.contents(atPath: t[1]), p.count == tailleProfil else { dire("ERR profil illisible ou de taille différente"); continue }
        let t0 = Date()
        let avant = Set(poignees())
        guard let (_, r4) = b.ptp(0x1016, [0xD185], sortant: p), r4 == 0x2001 else { dire("ERR profil refusé"); continue }
        guard let (_, r5) = b.ptp(0x1016, [0xD183], sortant: Data([0, 0])), r5 == 0x2001 else { dire("ERR départ refusé"); continue }
        var h: UInt32? = nil
        while h == nil && Date().timeIntervalSince(t0) < 60 { b.pause(0.1); h = Set(poignees()).subtracting(avant).first }
        guard let h else { dire("ERR aucun JPEG en 60 s"); continue }
        guard let (jpeg, r6) = b.ptp(0x1009, [h], delai: 60), r6 == 0x2001, jpeg.count > 1000 else { dire("ERR JPEG illisible"); continue }
        // effacement vérifié et objets du boîtier comptés après chaque rendu (29/10/2026 : deux blocages après 1 500 à 2 000
        // rendus d'affilée ; xt4_recherche_v2.BancGarde s'arrête si ce compte monte)
        var effacement: UInt16 = 0
        if formatObjet(h) == 0x3801 { effacementPermis = true; effacement = b.ptp(0x100B, [h])?.1 ?? 0; effacementPermis = false }
        do { try jpeg.write(to: URL(fileURLWithPath: t[2])) } catch { dire("ERR écriture du JPEG"); continue }
        dire(String(format: "OK rendu %.2f %d objets=%d fup=%d effacement=0x%04X", Date().timeIntervalSince(t0), jpeg.count, poignees().count, objetsRAF().count, effacement))
    } else { dire("ERR commande inconnue : \(ligne)") }
}
b.fermer()
dire("OK fin")
exit(0)
