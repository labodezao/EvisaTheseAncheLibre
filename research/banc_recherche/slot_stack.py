"""La fente et ses supports, de part et d'autre de la languette.

Géométrie réelle d'une anche, sans modèle emprunté. L'axe `z` suit l'air
(de l'amont vers l'aval). Une **pile de supports** percée d'une fente
occupe `0 ≤ z ≤ D` ; la languette (épaisseur `e`) a son plan médian en
`z_c = z_repos + y`, `y` étant le déplacement de son bout.

Un seul jeu de cotes décrit tous les montages :

- anche d'accordéon, dans le bon sens : la plaque seule (`D` = épaisseur de
  plaque), languette levée au-dessus (`z_repos = −levée − e/2`) ;
- la même, l'air dans l'autre sens : `z_repos = D + levée + e/2` ;
- sandwich (deux plaques, languette découpée dans la tôle du milieu) :
  `D = h_amont + e + h_aval`, `z_repos = h_amont + e/2` — les hauteurs de
  support de chaque côté peuvent différer ;
- deux plaques d'harmonium tête-à-tête : `D` = somme des deux, chaque
  languette à sa place.

L'air passe par trois tronçons en série :

1. la **colonne amont** : la part de la fente en amont de la languette,
   de longueur `d_a(z)`, de section `A_s` (la fente) ;
2. le **passage autour de la languette** : tant qu'elle est dans la pile,
   le seul jeu `c` sur son pourtour (écoulement visqueux : Reynolds ≈ 80 dans
   30 µm, loi de Poiseuille d'une fente mince) ; une fois sortie d'une face
   de `h`, le rideau entre son bord et le bord de la fente ;
3. la **colonne aval**, de longueur `d_b(z)`.

Les longueurs des colonnes dépendent de la position de la languette, donc
des hauteurs de support : c'est ce qui les fait entrer dans la physique.

Chaque tronçon a une masse d'air (`ρ·longueur/section`) et une perte
d'orifice (Bernoulli, dans les deux sens : pas de soupape ici). La
languette, en bougeant, déplace `g·ẏ` d'air (volume balayé) que les deux
colonnes doivent transporter. La pression sur chaque face est celle de la
colonne qui la touche — pas celle des pièces lointaines.

Statut de chaque hypothèse : voir `docs/audit_deux_anches.md` §7.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

MU_AIR = 1.8e-5          # viscosité dynamique de l'air (Pa·s), 20 °C


@dataclass
class SlotStack:
    """Cotes d'une anche dans sa pile de supports (toutes mesurables)."""
    depth_m: float                 # D : épaisseur totale percée par la fente
    rest_center_m: float           # z_repos : plan médian de la languette au repos
    tongue_m: float = 0.3e-3       # e : épaisseur de la languette
    clearance_m: float = 30e-6     # c : jeu languette / bord de fente
    alpha: float = 0.61            # contraction d'un jet à arête vive (hypothèse)

    # --- montages usuels ---------------------------------------------------
    @classmethod
    def accordion(cls, plate_m, lift_m, tongue_m=0.3e-3, reverse=False, **kw):
        """Plaque d'accordéon/harmonium, languette levée de `lift_m`.
        `reverse` : l'air arrive par l'autre face."""
        z = (plate_m + lift_m + tongue_m / 2) if reverse else (-lift_m - tongue_m / 2)
        return cls(depth_m=plate_m, rest_center_m=z, tongue_m=tongue_m, **kw)

    @classmethod
    def sandwich(cls, h_up_m, h_down_m, tongue_m=0.3e-3, **kw):
        """Languette plate dans la tôle du milieu, supports `h_up` (côté d'où
        vient l'air) et `h_down` (côté où il va)."""
        return cls(depth_m=h_up_m + tongue_m + h_down_m,
                   rest_center_m=h_up_m + tongue_m / 2, tongue_m=tongue_m, **kw)

    def flipped(self):
        """Le même montage, l'air arrivant par l'autre face."""
        return SlotStack(self.depth_m, self.depth_m - self.rest_center_m,
                         self.tongue_m, self.clearance_m, self.alpha)

    # --- géométrie selon la position -----------------------------------------
    def faces(self, y):
        zc = self.rest_center_m + y
        return zc - self.tongue_m / 2, zc + self.tongue_m / 2   # face amont, face aval

    def columns(self, y):
        """Longueurs (m) des colonnes d'air amont et aval dans la fente."""
        zu, zd = self.faces(y)
        D = self.depth_m
        d_a = min(max(zu, 0.0), D)
        d_b = D - min(max(zd, 0.0), D)
        return d_a, d_b

    def passage(self, y):
        """(hauteur de rideau h, longueur de recouvrement dans la pile).

        h > 0 : la languette est sortie d'une face de h ; recouvrement > 0 :
        une partie de son épaisseur est dans la pile (seul le jeu laisse
        passer l'air sur cette longueur).
        """
        zu, zd = self.faces(y)
        D = self.depth_m
        overlap = max(0.0, min(zd, D) - max(zu, 0.0))
        if zd <= 0.0:
            h = -zd
        elif zu >= D:
            h = zu - D
        else:
            h = 0.0
        return h, overlap


class SlotFlow:
    """Écoulement dans la fente d'UNE anche : pertes, masses d'air, force.

    `width_m`, `length_m` : la languette ; `g` : sa projection modale
    (volume balayé par unité de déplacement modal, m²) ; `phi` : déformée au
    bout. Le pourtour utile pour le rideau compte les côtés à hauteur de la
    moyenne de la déformée (0,39·longueur, hypothèse, cf. audit §3.3).
    """

    def __init__(self, stack: SlotStack, width_m, length_m, g, phi,
                 rho=1.2, side_fraction=0.39):
        self.st = stack
        self.rho = rho
        c = stack.clearance_m
        self.a_slot = (width_m + 2 * c) * (length_m + c)
        self.perim_full = width_m + 2 * length_m
        self.perim_curtain = width_m + 2 * side_fraction * length_m
        self.g = g
        self.phi = phi
        # correction d'extrémité d'une ouverture rectangulaire, approchée par
        # le disque de même aire (0,61·rayon, non bafflé) — hypothèse
        self.end = 0.61 * math.sqrt(self.a_slot / math.pi)

    def terms(self, y, q):
        """Masses d'air et pertes pour un déplacement de bout `y` (m) et un
        débit traversant `q` (m³/s, signé).

        Renvoie (L_colonnes, L_passage, perte_colonnes(q), perte_passage(q)).
        """
        st, rho = self.st, self.rho
        d_a, d_b = st.columns(y)
        L_ab = rho * (d_a + d_b + 2 * self.end) / self.a_slot
        h, overlap = st.passage(y)
        c = st.clearance_m
        if h > 0.0:
            a_pass = self.perim_curtain * math.sqrt(h * h + c * c)
            ell = max(h, c)
            visc = 0.0
        else:
            a_pass = self.perim_full * c
            ell = max(overlap, c)
            # Poiseuille dans une fente mince : Δp = 12 μ ℓ q / (P c³)
            visc = 12.0 * MU_AIR * overlap / (self.perim_full * c ** 3)
        L_p = rho * ell / a_pass
        # pertes d'orifice (Bernoulli) : rideau/jeu, et entrée + sortie de fente
        k_p = rho / (2.0 * (st.alpha * a_pass) ** 2)
        k_s = 2.0 * rho / (2.0 * (st.alpha * self.a_slot) ** 2)
        loss_p = k_p * q * abs(q) + visc * q
        loss_s = k_s * q * abs(q)
        return L_ab, L_p, loss_s, loss_p

    def accelerations(self, y, xd, q, dP, m, k, c_damp, x):
        """Accélération modale de la languette et dérivée du débit traversant.

        Équations (dérivées ici, cf. docstring du module) :

            p_a − p_b = ΔP − R_s(q) − L_ab·(q̇ + g·ẍ)      (colonnes)
            p_a − p_b = L_p·q̇ + R_p(q)                   (passage)
            m·ẍ = g·(p_a − p_b) − k·x − c·ẋ               (languette)

        Les deux premières donnent q̇ en fonction de ẍ ; la troisième ferme.
        La masse d'air ajoutée à la languette est g²·L_p·L_ab/(L_p+L_ab).
        """
        L_ab, L_p, loss_s, loss_p = self.terms(y, q)
        Ltot = L_p + L_ab
        g = self.g
        drive = dP - loss_s - loss_p            # pression disponible pour accélérer
        m_add = g * g * L_p * L_ab / Ltot
        # p_a − p_b = L_p·q̇ + R_p ; q̇ = (drive − L_ab·g·ẍ)/Ltot
        f_static = g * (L_p * drive / Ltot + loss_p)
        xdd = (f_static - k * x - c_damp * xd) / (m + m_add)
        qd = (drive - L_ab * g * xdd) / Ltot
        dp_tongue = L_p * qd + loss_p
        return xdd, qd, dp_tongue

    def quasi_static(self, y, xd, dP, m, k, c_damp, x):
        """Même physique, écoulement dans la fente pris INSTANTANÉ.

        Justification, mesurable sur les chiffres : la masse d'air de la
        fente (quelques centaines de kg/m⁴) face à la pente des pertes
        (∼10⁸ Pa·s/m³) donne un temps de réponse de l'ordre de la
        microseconde, deux mille fois plus court qu'une période d'anche.
        Le seul effet d'inertie qui compte à l'échelle de la languette est
        celui de l'air qu'elle entraîne elle-même : une masse ajoutée
        `g²·L_colonnes`, gardée.

            R_s(q) + R_p(q) = ΔP − L_ab·g·ẍ          (débit)
            (m + g²·L_ab)·ẍ = g·(ΔP − R_s(q)) − k·x − c·ẋ

        La languette voit ΔP amputé des pertes des colonnes (entrée et
        sortie de fente) : quand elle est loin, c'est la fente qui étrangle
        l'air, et la force baisse.
        """
        L_ab, _, _, _ = self.terms(y, 0.0)
        g = self.g
        m_eff = m + g * g * L_ab
        xdd = 0.0
        for _ in range(2):                       # l'inertie entre dans le débit : deux passes
            D = dP - L_ab * g * xdd
            q = self._flow(y, D)
            _, _, loss_s, _ = self.terms(y, q)
            xdd = (g * (dP - loss_s) - k * x - c_damp * xd) / m_eff
        return xdd, q

    def _flow(self, y, D):
        """Débit q (signé) tel que R_s(q) + R_p(q) = D : K·q|q| + v·q = D."""
        _, _, _, _ = self.terms(y, 0.0)
        st = self.st
        h, overlap = st.passage(y)
        c = st.clearance_m
        if h > 0.0:
            a_pass = self.perim_curtain * math.sqrt(h * h + c * c)
            v = 0.0
        else:
            a_pass = self.perim_full * c
            v = 12.0 * MU_AIR * overlap / (self.perim_full * c ** 3)
        K = self.rho / (2.0 * (st.alpha * a_pass) ** 2) + 2.0 * self.rho / (2.0 * (st.alpha * self.a_slot) ** 2)
        a = abs(D)
        q = (-v + math.sqrt(v * v + 4.0 * K * a)) / (2.0 * K)
        return q if D >= 0 else -q
