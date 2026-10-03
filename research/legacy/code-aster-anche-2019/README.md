# Calcul aux éléments finis d'une anche (Code_Aster, novembre 2019)

## D'où ça vient

`E:\Archives\Ingénierie et recherche\studies\anche\` (étude Salome-Meca `reedtest`,
cas `RunCase_8`). Géométrie : `reed grande masse 1.IGS` (même dossier) et
`reed grande masse 1.DXF` (`D:\GoogleDrive\Ingénierie et recherche\Projets\Thèse anche libre\acoustique\anches libres\acco\anches\`).
`cantilever_test.comm` : `E:\...\studies\cantiliver\` (février 2019, poutre d'essai).

Non copiés (trop gros, régénérables) : le maillage `reedtest_SMESH_Mesh.med` (3 Mo),
les résultats `reed_modes.rmed` (9,6 Mo), `trans.rmed` (240 Mo), `glob.1` (800 Mo).

## Ce que c'est

Une lame d'acier vue de dessus : 45,85 mm × 8,0 mm (cotes du DXF). Acier :
E = 210 GPa, ν = 0,3, ρ = 7 800 kg/m³. Encastrement sur le groupe `clamp`.
Maillage 3D : 19 408 nœuds, 104 208 mailles. Le calcul a convergé.

Les dix premières fréquences propres sont dans `frequences_propres.csv` :

| mode | f (Hz) | f / f1 |
|---|---|---|
| 1 | 144,4 | 1,00 |
| 2 | 910,5 | 6,30 |
| 3 | 1 546 | 10,7 |
| 4 | 2 149 | 14,9 |

Lecture : le rapport f2/f1 = 6,30 est très proche de 6,27, le rapport d'une poutre
encastrée-libre uniforme (Euler-Bernoulli). Le mode 2 est donc sans doute la 2e flexion.
Le mode 3 est sans doute la 1re torsion (à vérifier sur les déformées du `.rmed`).

Ordre de grandeur : pour une lame d'acier uniforme de 45,85 mm, f1 = 144 Hz demande une
épaisseur d'environ 0,36 mm. Le nom « grande masse » dit qu'il y a sans doute une masse en
bout : à vérifier sur la CAO.

Le même maillage (`Mesh_1.stl`, 5 346 425 octets) sert au cas Elmer `bass_reed` de 2020,
qui n'a jamais donné de résultat. Ce calcul Code_Aster est donc **la référence** pour
recaler le cas Elmer et `banc_recherche.modal`.

La suite du fichier `.comm` (projection sur la base modale, `DYNA_VIBRA` transitoire sur
5 s) n'a pas d'effort imposé : c'était un essai de chaîne de calcul.

## Comment relancer

Salome-Meca (Code_Aster 14 ou plus) : importer l'IGS, mailler, nommer `clamp` la face
encastrée, puis lancer `reedtest_modes_transitoire.comm`. Pour juste lire les fréquences :
`reedtest_message.txt`, chercher « fréquence (HZ) ».
