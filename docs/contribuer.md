# Contribuer
## Pistes d'évolution

* **Écriture C1-C7 sur d'autres boîtiers** : l'outil ne vise que le X-T4. Les rapports publics sur X-H2, X-T5, X100VI, X-E5, X-S20 et X100V laissent penser que c'est faisable ailleurs ; il faudrait l'essayer boîtier par boîtier.
* **Hors macOS** : l'outil passe par ImageCaptureCore, propre au Mac. Un portage par libusb (Linux, Windows) reste à faire.
* **Multi-boîtier natif dans le tableur** : ajouter des colonnes `Device`, `Firmware`, `SerialNumber` pour générer tous les packs en une passe.
* **Exposer les champs figés** (Clarity, ColorSpace, BlackImageTone…) pour couvrir les presets B&W virés et les presets AdobeRGB.
* **Validateur `.FP1`** : pour le X-T4, `xt4_recettes traduire` et `autotest` en tiennent lieu ; un validateur pour tous les boîtiers (JSON Schema, Pydantic) reste à faire.
* **UI web** (Streamlit / SvelteKit) pour saisir un preset via formulaire avec preview.
* **Boîtiers récents** : X-H2, X-S20, X-T50 et X100VI manquent aux packs, faute d'un vrai fichier `.FP1` pour ces modèles. Un fichier généré par X RAW Studio suffit pour les ajouter.
* **Simulations hors X RAW Studio** : [abpy/FujifilmCameraProfiles](https://github.com/abpy/FujifilmCameraProfiles) publie les simulations Fuji en profils `.dcp` et LUT `.cube` pour Lightroom / Camera Raw. Base possible pour décliner les recettes du tableur en presets Lightroom, sans boîtier branché.

Un membre du Discord a aussi publié [`FujiSimuRecipesGen`](https://github.com/mmoqui/FujiSimuRecipesGen), un générateur en Go (MIT).

Contributions bienvenues : ouvrir une issue ou une PR.

## Les auteurs des presets

Les presets sont nommés par **préfixe auteur** (convention FujiXWeekly / Team Fuji) :

| Préfixe | Auteur |
|---|---|
| `BLP` | Blaise Pauly |
| `BT` | Benjamin Turner |
| `DC` | Daniel Craig |
| `EM` | Eric Mercurio |
| `ER` | *(inconnu, ER)* |
| `GB` | *(inconnu, GB)* |
| `HF` | *(inconnu, HF)* |
| `HH` | *(inconnu, HH)* |
| `JC` | Jerome Courtial |
| `JP` | *(inconnu, JP)* |
| `KM` | Kevin Mullins |
| `LC` | *(inconnu, LC)* |
| `MT` | Michael Turner |
| `NZD` | *(NZD)* |
| `PE` | *(PE)* |
| `PLR` | *(inconnu, PLR)* |
| `PS` | *(PS)* |
| `RR` | Ritchie Roesch ([FujiXWeekly](https://fujixweekly.com/)) |
| `RS` | *(inconnu, RS)* |
| `SS` | *(inconnu, SS)* |
| `TH` | Thomas Hammoudi (recettes mesurées sur X-T4, 2026) |
| `VM` | *(VM)* |

Pour partager **vos propres presets**, nommez-les `Prénom_Nom - Nom du preset.FP1` et passez par une pull request ou par le Discord.
