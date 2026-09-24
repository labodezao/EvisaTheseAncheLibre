"""Deux anches d'une même note, leurs chambres, la table d'harmonie et le
clapet — un **réseau acoustique à constantes localisées**.

Ce que `reed_oscillator.FreeReedModel` ne sait pas faire : une note
d'accordéon en MM, ce sont **deux** anches qui prennent leur air au même
soufflet et le rendent au même trou de clapet. Elles se partagent l'air, et
elles se parlent par lui.

Le chemin de l'air (poussé) ::

    soufflet ──anche 1── chambre 1 ──trou 1──┐
    (P_s)                                     ├─ canal du clapet ── clapet ── dehors
             ──anche 2── chambre 2 ──trou 2──┘   (V_n)             (m_p)

et en tiré, le même chemin parcouru dans l'autre sens : dehors → clapet →
canal → trou → chambre → anche → soufflet (en dépression). Dans les deux cas
l'anche est entre deux nœuds de pression et c'est leur **différence** qui la
pousse hors de sa fente et qui la traverse (Bernoulli, dans un seul sens :
la soupape de cuir).

Chaque élément est une grandeur que l'on peut mesurer au pied à coulisse :

- **chambre** : un volume (compliance `V/(γ·P_atm)`) ;
- **trou de la table d'harmonie** et **ouverture du clapet** : une masse
  d'air `ρ·ℓ_eff/S` (inertance) et une perte de charge d'orifice
  `ρ·q|q|/(2·(C_d·S)²)` — c'est là que l'air se dissipe, et c'est ce qui
  borne l'amplitude, sans résistance de source ajustée à la main ;
- **canal sous le clapet** : un volume, **commun aux deux anches** — c'est
  le couplage. Option `shared_chamber=True` : les deux anches dans la même
  chambre (couplage maximal).

Le **son** sort par le clapet : en champ lointain, une petite ouverture
rayonne comme un monopôle, `p(r, t) = ρ/(4π r) · dq_p/dt`. La puissance
rayonnée se calcule sur le spectre de `q_p` (résistance de rayonnement d'une
ouverture bafflée, `ρω²/(2πc)`), et le rendement acoustique est
`P_rayonnée / (P_s · débit moyen)` — la part du souffle qui devient du son.

Choix et limites, honnêtement :

- **un mode par anche** (le premier, qui fait la note) : c'est ce qui rend le
  modèle assez rapide pour des secondes de son — il en faut plusieurs pour
  voir un battement à 1 Hz ;
- constantes localisées : valables tant que les dimensions restent petites
  devant la longueur d'onde (≈ 78 cm à 440 Hz ; une chambre fait 3 cm). Les
  résonances de Helmholtz chambre/trou tombent vers 2 kHz, canal/clapet
  vers 5 kHz : au-dessus des fondamentales, elles colorent les aigus ;
- **le démarrage vient de CHAQUE anche.** Une anche d'accordéon est
  **fermée par le souffle** ((−,+) de Fletcher ; Ricot, Caussé, Misdariis,
  JASA 117, 2005 ; Millot & Baumann, Acta Acustica 93, 2007) : la pression
  pousse d'abord la languette DANS sa fente — le passage se referme — puis
  à travers. Quand elle avance, le débit baisse ; la masse d'air du chemin
  (trou, canal, clapet) freine cette baisse et fait monter la pression
  derrière elle, en phase avec sa vitesse : elle est relancée. C'est
  l'inertance qui entretient, et un trou de table la fournit — exactement
  le régime (sous la résonance de Helmholtz) où une chambre bien ventilée
  est inertielle. Aucune résistance calée : `ReedSetting` (levée, épaisseur
  de plaque, jeu), des cotes qui se mesurent.

  L'ancien modèle traitait l'anche comme **ouverte** par le souffle
  (`setting=None` ici, `FreeReedModel`) : dans le même réseau, rien ne
  démarre, et il avait fallu une résistance de source ajustée (5·10⁶) pour
  le faire chanter — d'où ses seuils étalés sur trois décades ;
- **ce que ça donne** (lames d'acier uniformes, `steel_reed`) : de La2 à
  La5 toutes démarrent entre 200 et 1000 Pa (une décade, contre trois),
  quelques cents SOUS leur lame (−4 à −24 ¢), et la note baisse quand on
  pousse. Deux anches d'une note, couplées par le canal et le clapet
  communs, se verrouillent jusqu'à ~2 ¢ de désaccord (La4, 1000 Pa :
  ±0,6 Hz) — « les voix se collent » — et battent au-delà (5 ¢ : −12 %,
  20 ¢ : l'écart des lames). L'air double presque (−4 %) ;
- **ce qui reste faux** : courses (4–5 mm pour un La4) et débits
  (0,4 L/s) trop grands, rendement probablement surestimé — rien encore ne
  freine la languette hors de la plaque sinon l'étranglement par la fente.
  Candidat suivant : la traînée aérodynamique sur la languette. À confronter
  au banc avant d'y toucher ;
- les **valeurs par défaut sont des ordres de grandeur**, pas des mesures
  (dimensions typiques d'un sommier). Chacune est à relever sur ton
  instrument ; une simulation par éléments finis (Elmer, par exemple) sert
  à *calculer* ces masses et volumes effectifs sur la vraie géométrie, pas
  à remplacer ce réseau.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from .reed_oscillator import FreeReedModel, Slot


@dataclass
class Orifice:
    """Un passage d'air : masse acoustique + perte de charge d'orifice.

    `length_m` est la longueur **effective** : épaisseur de la paroi plus les
    corrections d'extrémité (≈ 0,8·rayon équivalent de chaque côté).
    """
    area_m2: float
    length_m: float
    cd: float = 0.6

    def inertance(self, rho):
        return rho * self.length_m / self.area_m2

    def loss(self, q, rho):
        """Perte de charge (Pa) pour un débit `q` (m³/s), de signe de `q`."""
        s = self.cd * self.area_m2
        return rho * q * abs(q) / (2.0 * s * s)


@dataclass
class ReedSetting:
    """Réglage d'une anche **fermée par le souffle** (« blown-closed »,
    (−,+) dans la notation de Fletcher) — l'anche d'accordéon.

    Au repos, la languette est levée de `lift_m` au-dessus de la plaque, du
    côté d'où vient l'air. Le souffle la pousse d'abord DANS la fente : le
    passage se referme (il ne reste que le jeu `clearance_m` tant qu'elle
    traverse l'épaisseur `plate_m` de la plaque), puis elle ressort de
    l'autre côté et le passage se rouvre. C'est la section utile de Millot &
    Baumann (Acta Acustica 93, 2007) — symétrique autour de la traversée —
    réduite à la hauteur au bout, les côtés comptant pour `side_fraction` de
    la longueur (moyenne de la déformée du premier mode : 0,39).

    Toutes ces cotes se mesurent (pied à coulisse, cale d'épaisseur, loupe).
    Les défauts sont des ordres de grandeur d'une anche de grave.
    """
    lift_m: float = 0.5e-3          # levée de la pointe au repos (côté amont)
    plate_m: float = 1.2e-3         # épaisseur de la plaque
    tongue_m: float = 0.4e-3        # épaisseur de la languette au bout
    clearance_m: float = 30e-6      # jeu latéral languette/fente
    side_fraction: float = 0.39     # part des côtés dans le périmètre utile
    alpha: float = 0.61             # vena contracta

    def gap(self, y):
        """Hauteur de passage au bout pour un déplacement `y` (m, vers
        l'aval) : au-dessus de la plaque, dedans (0), ou ressortie."""
        z_d = y - self.lift_m               # face aval / face amont de la plaque
        z_u = z_d - self.tongue_m           # face amont de la languette
        if z_d < 0.0:
            return -z_d
        if z_u > self.plate_m:
            return z_u - self.plate_m
        return 0.0


@dataclass
class Voicing:
    """La géométrie d'une note : chambres, trous, canal, clapet.

    Ordres de grandeur d'un sommier d'accordéon (médium) — **à mesurer**.
    """
    chamber_m3: float = 7.9e-6                  # 35 x 15 x 15 mm
    hole: Orifice = field(default_factory=lambda: Orifice(2.0e-4, 0.020))   # 8 x 25 mm, table 8 mm
    channel_m3: float = 4.0e-6                  # canal sous le clapet
    pallet: Orifice = field(default_factory=lambda: Orifice(3.0e-4, 0.010))  # clapet levé de ~4 mm
    shared_chamber: bool = False                # True : deux anches, une chambre
    # Résistance EFFECTIVE du passage commun (clapet), linéaire, en Pa·s/m³ —
    # le paramètre calé du modèle à une anche, pour comparer. 0 par défaut.
    supply_resistance: float = 0.0
    # Résistance EFFECTIVE propre à chaque chambre (dans son trou de table).
    # Héritée du premier jet (anche « ouverte par le souffle ») : partagée au
    # clapet, elle soudait les anches jusqu'à 80 ¢ ; propre à chaque anche,
    # elles battaient. Avec l'anche fermée par le souffle (défaut), aucune
    # des deux n'est nécessaire : 0.
    hole_resistance: float = 0.0
    patm: float = 1e5
    gamma: float = 1.4
    rho: float = 1.2
    c: float = 343.0


@dataclass
class CoupledResult:
    t: np.ndarray
    tips: np.ndarray               # (2, n) déplacement du bout de chaque anche (m)
    reed_flows: np.ndarray         # (2, n) débit à travers chaque anche (m³/s)
    pallet_flow: np.ndarray        # débit sortant par le clapet (m³/s)
    channel_pressure: np.ndarray   # pression dans le canal (Pa, relative)
    fs: float
    supply_pa: float
    rho: float = 1.2
    c: float = 343.0

    @property
    def radiated(self):
        """Son en champ lointain (à 1/(4πr) près) : `ρ·dq_p/dt`."""
        return self.rho * np.gradient(self.pallet_flow) * self.fs

    def steady(self, t0=None):
        """Masque de la partie établie (par défaut : la seconde moitié)."""
        t0 = self.t[-1] / 2 if t0 is None else t0
        return self.t >= t0

    def consumption(self, t0=None):
        """Débit moyen de chaque anche et du clapet (m³/s), régime établi."""
        m = self.steady(t0)
        return dict(reed=[float(self.reed_flows[i][m].mean()) for i in range(2)],
                    pallet=float(self.pallet_flow[m].mean()))

    def frequencies(self, t0=None):
        """Fréquence de jeu de chaque anche, lue sur SON déplacement (Hz).

        C'est ce que le modèle offre et que le micro n'offre pas : on voit
        chaque languette séparément, donc on voit si elles se sont
        **synchronisées** (même fréquence) ou si elles battent.
        """
        m = self.steady(t0)
        return [dominant_frequency(self.tips[i][m], self.fs) for i in range(2)]

    def beat_hz(self, t0=None):
        """Battement entre les deux anches (Hz) : vitesse moyenne de dérive
        de leur **différence de phase** (signaux analytiques des deux
        languettes). Précis même pour un battement plus lent que la durée
        simulée, et nul si elles se sont synchronisées (verrouillage
        d'Adler) — la différence de phase reste alors bornée.
        """
        m = self.steady(t0)
        ph = [np.unwrap(np.angle(_analytic(self.tips[i][m]))) for i in range(2)]
        d = ph[1] - ph[0]
        n = d.size
        cut = slice(n // 10, n - n // 10)       # bords de la transformée de Hilbert
        tt = self.t[m][cut]
        slope = np.polyfit(tt, d[cut], 1)[0]
        return float(slope / (2 * np.pi))

    def radiated_power(self, t0=None):
        """Puissance acoustique rayonnée par le clapet (W), ouverture bafflée."""
        m = self.steady(t0)
        q = self.pallet_flow[m] - self.pallet_flow[m].mean()
        n = q.size
        Q = np.fft.rfft(q * np.hanning(n)) * 2.0 / (0.5 * n)   # amplitudes crête
        f = np.fft.rfftfreq(n, 1.0 / self.fs)
        w = 2 * np.pi * f
        # |q|² moyen = A²/2 ; R_rad = ρω²/(2πc) (piston bafflé, ka ≪ 1)
        return float(np.sum(self.rho * w ** 2 / (2 * np.pi * self.c) * np.abs(Q) ** 2 / 2) / 1.5)

    def efficiency(self, t0=None):
        """Rendement acoustique : puissance rayonnée / puissance pneumatique."""
        q = self.consumption(t0)['pallet']
        p_pneu = abs(self.supply_pa) * abs(q)
        return self.radiated_power(t0) / p_pneu if p_pneu > 0 else float('nan')


def _analytic(x):
    """Signal analytique (transformée de Hilbert par FFT, numpy seul)."""
    x = np.asarray(x, float) - np.mean(x)
    n = x.size
    X = np.fft.fft(x)
    h = np.zeros(n)
    h[0] = 1.0
    if n % 2 == 0:
        h[n // 2] = 1.0
        h[1:n // 2] = 2.0
    else:
        h[1:(n + 1) // 2] = 2.0
    return np.fft.ifft(X * h)


def dominant_frequency(x, fs):
    """Fréquence du pic principal, interpolation parabolique (log) + zéros."""
    x = np.asarray(x, float) - np.mean(x)
    n = x.size
    N = 1 << int(np.ceil(np.log2(n)) + 3)
    S = np.abs(np.fft.rfft(x * np.hanning(n), N))
    i = int(np.argmax(S[1:]) + 1)
    if 1 <= i < S.size - 1:
        a, b, c = np.log(S[i - 1:i + 2] + 1e-300)
        d = 0.5 * (a - c) / (a - 2 * b + c) if (a - 2 * b + c) != 0 else 0.0
    else:
        d = 0.0
    return (i + d) * fs / N


class CoupledReedsModel:
    """Deux anches libres, un soufflet, un clapet (un mode par anche).

    `reeds` : deux `FreeReedModel` (géométrie de lame et de fente) — leur
    chambre et leur source ne servent pas ici, c'est `voicing` qui les
    remplace. `detune_cents` désaccorde la 2ᵉ anche en raidissant sa lame
    (fréquence ∝ √k) : c'est le geste de l'accordeur qui gratte.
    `direction` : 'pousser' ou 'tirer'.
    """

    def __init__(self, reeds=None, voicing: Voicing | None = None,
                 detune_cents: float = 0.0, direction: str = 'pousser',
                 zeta: float = 0.004, slot_length_m: float | None = None,
                 sweep: float = 1.0, muted=(False, False),
                 setting: ReedSetting | None = ReedSetting(), settings=None):
        if reeds is None:
            reeds = [FreeReedModel(n_modes=1, zeta=zeta), FreeReedModel(n_modes=1, zeta=zeta)]
        if len(reeds) != 2:
            raise ValueError("il faut deux anches")
        self.v = voicing or Voicing()
        if direction not in ('pousser', 'tirer'):
            raise ValueError("direction : 'pousser' ou 'tirer'")
        self.direction = direction
        self.reeds = reeds
        # Réduction à un mode : masse, raideur, amortissement, projection.
        self.m = [float(r.M[0, 0]) for r in reeds]
        self.k = [float(r.K[0, 0]) for r in reeds]
        self.k[1] *= 2.0 ** (2.0 * detune_cents / 1200.0)
        self.c_damp = [2.0 * r.zeta * math.sqrt(k * m) for r, k, m in zip(reeds, self.k, self.m)]
        self.g = [float(r.gamma[0]) for r in reeds]
        self.phi = [float(r.phi_tip[0]) for r in reeds]
        self.slot: list[Slot] = [r.slot for r in reeds]
        v = self.v
        self.n_ch = 1 if v.shared_chamber else 2
        self.L_hole = v.hole.inertance(v.rho)
        self.L_pal = v.pallet.inertance(v.rho)
        # Inertie de l'air DANS la fente (épaisseur de plaque) : le débit
        # suit l'ouverture avec retard. `None` : débit quasi statique
        # (Bernoulli instantané), comme `FreeReedModel`.
        self.slot_length_m = slot_length_m
        # Volume balayé par la languette (Γ·ẋ) compté dans le bilan de la
        # chambre : 0 = comme `FreeReedModel` (anche libre), 1 = entièrement.
        self.sweep = float(sweep)
        # Anche « bloquée » (sourdine, bande adhésive, cale) : languette
        # immobile, fente fermée — c'est ce qu'on fait à l'atelier pour
        # mesurer une anche seule, et ce que l'accordeur évite désormais.
        self.muted = tuple(bool(m) for m in muted)
        # Géométrie d'écoulement : anche fermée par le souffle (accordéon,
        # défaut) ou, avec `setting=None`, l'ancienne loi « ouverte par le
        # souffle » de `FreeReedModel` (gardée pour comparer).
        # Un réglage par anche (`settings`), ou le même pour les deux.
        self.settings = list(settings) if settings is not None else [setting, setting]
        self.setting = self.settings[0]
        if self.setting is not None:
            self.w_eff = [s_.width_m + 2 * st.side_fraction * r.L
                          for s_, r, st in zip(self.slot, reeds, self.settings)]
            # La fente elle-même (empreinte de la languette + jeu) : quand la
            # languette en est loin, c'est ELLE qui étrangle l'air.
            self.a_slot = [(s_.width_m + 2 * st.clearance_m) * (r.L + st.clearance_m)
                           for s_, r, st in zip(self.slot, reeds, self.settings)]

    @property
    def f_reeds(self):
        """Fréquences propres des deux lames (Hz), désaccord compris."""
        return [math.sqrt(k / m) / (2 * math.pi) for k, m in zip(self.k, self.m)]

    # État : [ẋ1, x1, ẋ2, x2, p_ch1, (p_ch2), q_h1, (q_h2), p_n, q_p, q_r1, q_r2]
    def _layout(self):
        n = self.n_ch
        return dict(p_ch=4, q_h=4 + n, p_n=4 + 2 * n, q_p=5 + 2 * n,
                    q_r=6 + 2 * n, size=8 + 2 * n)

    def _slot_open(self, i, x):
        if self.setting is not None:
            return self._area(i, x) / self.slot[i].width_m
        s = self.slot[i]
        return min(max(self.phi[i] * x + s.rest_offset_m, s.leak_m), s.max_open_m)

    def _area(self, i, x):
        """Section utile (m²) — anche fermée par le souffle."""
        st = self.settings[i]
        h = st.gap(self.phi[i] * x)
        return self.w_eff[i] * math.sqrt(h * h + st.clearance_m ** 2)

    def _series(self, i, x):
        """Section équivalente (m²) de l'écart autour de la languette en
        série avec la fente, et part de la chute de pression prise par
        l'écart — c'est-à-dire celle qui pousse la languette.

        Tant que l'écart est étroit, toute la chute s'y fait : la languette
        prend `Δp` en plein. Quand elle est loin de la plaque, l'écart devient
        plus grand que la fente, la chute passe dans la fente, et la force
        sur la languette s'effondre — elle est dans le jet. C'est ce qui borne
        l'amplitude et le débit.
        """
        su = self._area(i, x)
        inv = 1.0 / (su * su) + 1.0 / (self.a_slot[i] ** 2)
        a_eff = 1.0 / math.sqrt(inv)
        return a_eff, (a_eff / su) ** 2

    def _reed_flow(self, i, dp, x):
        if self.setting is not None:
            a, _ = self._series(i, x)
            if dp <= 0.0:
                return 0.0, a
            return self.settings[i].alpha * a * math.sqrt(2.0 * dp / self.v.rho), a
        s = self.slot[i]
        h = min(max(self.phi[i] * x + s.rest_offset_m, s.leak_m), s.max_open_m)
        if dp <= 0.0:
            return 0.0, h
        return self.reeds[i].ch.cd * s.width_m * h * math.sqrt(2.0 * dp / self.v.rho), h

    def deriv(self, s, P):
        """Dérivée de l'état pour une pression de soufflet `P` (Pa, > 0).

        Pressions relatives : en poussé, au dehors (clapet → 0) ; en tiré,
        au soufflet (0) avec le dehors à +P. Même réseau, parcouru à
        l'envers : l'anche est au bout amont (poussé) ou aval (tiré).
        """
        v = self.v
        lay = self._layout()
        n = self.n_ch
        out = [0.0] * lay['size']
        K = v.gamma * v.patm
        p_n = s[lay['p_n']]
        q_p = s[lay['q_p']]
        q_in_ch = [0.0] * n
        for i in range(2):
            xd, x = s[2 * i], s[2 * i + 1]
            ch = 0 if n == 1 else i
            p_c = s[lay['p_ch'] + ch]
            if self.direction == 'pousser':
                dp = P - p_c                    # soufflet → anche → chambre
            else:
                dp = p_c - 0.0                  # chambre → anche → soufflet (réf. 0)
            if self.muted[i]:
                out[2 * i] = out[2 * i + 1] = 0.0
                if self.slot_length_m is not None:
                    out[lay['q_r'] + i] = 0.0
                continue
            if self.slot_length_m is None:
                q_r, _ = self._reed_flow(i, dp, x)
            else:
                # ρ·ℓ/(w·h) · dq/dt = Δp − ρ q|q| / (2 (C_d w h)²), sens unique
                q_r = max(0.0, s[lay['q_r'] + i])
                h = self._slot_open(i, x)
                w = self.slot[i].width_m
                cd = self.settings[i].alpha if self.setting is not None else self.reeds[i].ch.cd
                cdw = cd * w * max(h, 1e-9)
                L = v.rho * (self.slot_length_m + 0.5 * h) / (w * h)
                dq = (dp - v.rho * q_r * q_r / (2.0 * cdw * cdw)) / L
                if s[lay['q_r'] + i] <= 0.0 and dq < 0.0:
                    dq = 0.0                    # la soupape bloque le retour
                out[lay['q_r'] + i] = dq
            load = dp if self.setting is None else dp * self._series(i, x)[1]
            out[2 * i] = (load * self.g[i] - self.k[i] * x - self.c_damp[i] * xd) / self.m[i]
            out[2 * i + 1] = xd
            q_in_ch[ch] += q_r
            # Balayage : en poussé la languette avance dans la chambre (aval)
            # et la remplit ; en tiré elle s'en éloigne (chambre en amont) et
            # la vide — dans les deux cas le même signe vu du bilan de chambre.
            q_in_ch[ch] += self.sweep * self.g[i] * xd
        q_hole_total = 0.0
        for ch in range(n):
            p_c = s[lay['p_ch'] + ch]
            q_h = s[lay['q_h'] + ch]
            if self.direction == 'pousser':
                # chambre → trou → canal ; l'anche remplit la chambre
                out[lay['p_ch'] + ch] = K / v.chamber_m3 * (q_in_ch[ch] - q_h)
                out[lay['q_h'] + ch] = (p_c - p_n - v.hole_resistance * q_h
                                        - v.hole.loss(q_h, v.rho)) / self.L_hole
            else:
                # canal → trou → chambre ; l'anche vide la chambre
                out[lay['p_ch'] + ch] = K / v.chamber_m3 * (q_h - q_in_ch[ch])
                out[lay['q_h'] + ch] = (p_n - p_c - v.hole_resistance * q_h
                                        - v.hole.loss(q_h, v.rho)) / self.L_hole
            q_hole_total += q_h
        R = v.supply_resistance * q_p
        if self.direction == 'pousser':
            out[lay['p_n']] = K / v.channel_m3 * (q_hole_total - q_p)
            out[lay['q_p']] = (p_n - 0.0 - R - v.pallet.loss(q_p, v.rho)) / self.L_pal
        else:
            out[lay['p_n']] = K / v.channel_m3 * (q_p - q_hole_total)
            out[lay['q_p']] = (P - p_n - R - v.pallet.loss(q_p, v.rho)) / self.L_pal
        return out

    def simulate(self, dur, supply_pa=1000.0, fs=22050.0, oversample=8,
                 attack_s=0.02, seed=0):
        """RK4 suréchantillonné. Le soufflet monte en `attack_s` (attaque).

        Une infime asymétrie initiale (`seed`) évite que deux anches
        identiques partent exactement en phase par accident numérique.
        """
        lay = self._layout()
        n = int(dur * fs)
        sub = max(1, int(oversample))
        dt = 1.0 / (fs * sub)
        s = [0.0] * lay['size']
        rng = np.random.default_rng(seed)
        s[0], s[2] = rng.normal(0, 1e-4, 2)
        for i in range(2):
            if self.muted[i]:
                s[2 * i] = 0.0
        if self.direction == 'tirer':
            # au repos, le canal et les chambres sont à la pression du dehors
            pass
        tips = np.zeros((2, n)); rq = np.zeros((2, n)); qp = np.zeros(n); pn = np.zeros(n)

        def add(a, b, h):
            return [x + h * y for x, y in zip(a, b)]

        t = 0.0
        for j in range(n):
            for _ in range(sub):
                P = supply_pa * min(1.0, t / attack_s) if attack_s > 0 else supply_pa
                k1 = self.deriv(s, P)
                k2 = self.deriv(add(s, k1, 0.5 * dt), P)
                k3 = self.deriv(add(s, k2, 0.5 * dt), P)
                k4 = self.deriv(add(s, k3, dt), P)
                s = [x + dt / 6.0 * (a + 2 * b + 2 * c + d)
                     for x, a, b, c, d in zip(s, k1, k2, k3, k4)]
                t += dt
            if not all(math.isfinite(x) for x in s):
                raise FloatingPointError("divergence numérique : augmente `oversample`")
            ch = lambda i: 0 if self.n_ch == 1 else i
            for i in range(2):
                x = s[2 * i + 1]
                tips[i, j] = self.phi[i] * x
                p_c = s[lay['p_ch'] + ch(i)]
                dp = (supply_pa - p_c) if self.direction == 'pousser' else p_c
                rq[i, j] = (0.0 if self.muted[i]
                            else self._reed_flow(i, dp, x)[0] if self.slot_length_m is None
                            else max(0.0, s[lay['q_r'] + i]))
            qp[j] = s[lay['q_p']]
            pn[j] = s[lay['p_n']]
        return CoupledResult(np.arange(n) / fs, tips, rq, qp, pn, fs, supply_pa,
                             self.v.rho, self.v.c)


def steel_reed(f_hz, thickness_m=0.3e-3, width_m=3.5e-3, zeta=0.004):
    """Une vraie lame d'acier, uniforme, accordée par sa longueur.

    `f₁ = (1,875²/2π)·(e/L²)·√(E/12ρ)` : on choisit l'épaisseur et la largeur
    (mesurables au palmer), la longueur en découle. Renvoie `(lame,
    réglage)` : la lame (un mode) et un réglage d'anche fermée par le
    souffle proportionné (levée 1,5·e, plaque 3·e, au moins 0,8 mm).

    Pourquoi pas la lame de référence (`SECTIONS_DEFAULT`) : son tronçon
    central de 45 µm la rend si souple qu'à 1000 Pa la pression la traverse
    statiquement — elle reste coincée dans sa fente.
    """
    from .reed_oscillator import Slot
    E, rho = 2.1e11, 7800.0
    L = math.sqrt(0.5596 * thickness_m * math.sqrt(E / (12 * rho)) / f_hz)
    sec = np.array([[L, rho, width_m, thickness_m, E]])
    reed = FreeReedModel(sections=sec, n_modes=1, zeta=zeta, slot=Slot(width_m=width_m))
    setting = ReedSetting(lift_m=1.5 * thickness_m, tongue_m=thickness_m,
                          plate_m=max(0.8e-3, 3 * thickness_m))
    return reed, setting


def pair(f_hz, detune_cents=0.0, thickness_m=0.3e-3, width_m=3.5e-3, **kw):
    """Une note MM : deux lames d'acier identiques, la 2ᵉ désaccordée."""
    r1, s1 = steel_reed(f_hz, thickness_m, width_m)
    r2, s2 = steel_reed(f_hz, thickness_m, width_m)
    return CoupledReedsModel(reeds=[r1, r2], settings=[s1, s2],
                             detune_cents=detune_cents, **kw)


def lock_scan(detunes_cents, f_hz=440.0, voicing: Voicing | None = None,
              supply_pa=1000.0, dur=2.0, direction='pousser', fs=11025.0,
              oversample=24, t0=0.6):
    """Battement mesuré en fonction du désaccord imposé entre les lames.

    Renvoie une liste de dicts : désaccord (¢), écart des lames (Hz),
    battement joué (Hz). Loin du verrouillage, battement ≈ écart des lames ;
    près de lui, il se creuse en √(Δ² − Δ_L²) (Adler) ; dedans, il est nul.
    C'est la mesure qui dit à quel point deux anches d'une note se tirent
    l'une l'autre — et à partir de quel désaccord une musette cesse de battre.
    """
    out = []
    for c in detunes_cents:
        m = pair(f_hz, detune_cents=c, voicing=voicing, direction=direction)
        r = m.simulate(dur, supply_pa=supply_pa, fs=fs, oversample=oversample)
        fl = m.f_reeds
        out.append(dict(cents=float(c), blade_gap_hz=fl[1] - fl[0], beat_hz=r.beat_hz(t0)))
    return out
