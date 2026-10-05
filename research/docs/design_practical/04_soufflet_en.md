# Bellows

## The lung of the instrument

Everything upstream of the reed is in the bellows: the pressure, its rise, its fall, its reversal. A framed bellows is folds of card and cloth, leather at the corners, and a wooden frame at each end that takes the two halves of the case. On the instruments of the training courses it is bought ready made, and the trainee glues its frames, drills and fits the pins, and checks it alone before mounting it. This chapter asks three questions a maker meets before any of those gestures: what kind of source of air is a bellows, how large should it be, and where does it leak.

### A source of flow, held by an arm

What does the arm actually set, the pressure or the flow? Every player has the answer in the hands. Keep the bellows moving at a steady speed and open a chord: the pressure drops, because the same flow is now shared by more reeds. A source of pressure, like the large weighted reservoir of an organ, would hold the pressure and send twice the flow through two reeds. A bellows behaves rather like a source of flow, and the truth lies between the two ideals: a real source gives less flow when the pressure rises. The simplest law is a straight line,

$$q = q_0 - p/R$$

where $q_0$ is the flow at zero pressure and $R$ the internal resistance of the source. The thesis shows what $R$ does to the reed: it changes the amplitude of the note and moves its threshold. Here it matters for a simpler reason. A drone, a chord, a second voice, all draw on the same source, and the pressure each note receives depends on what the others are taking.

The arm itself is the other half of the source. A force $F$ on a bellows of effective area $S$ makes a pressure

$$p = F/S$$

and a stroke of length $c$ sweeps a volume $S\,c$. The effective area is not the area of the frame: the folds give a little under pressure, and the force spreads over less than the full section. It is measured, not computed, by the drop test of the leak chapter: a known weight $m$ on the bellows, the pressure read on the U-tube, and $S = mg/p$.

### How large a bellows

Ewen answered the question of the size of the bellows in one sentence: a minimal section by number of voices; too small, not enough air; too large, not enough pressure; an optimum, perhaps to be computed. Here is the computation, and it is short.

Too large first. The arm has a force it can give comfortably for a phrase, $F$. To reach the pressure $p$ that the reeds need for a forte, the area must not exceed

$$S_{\max} = F/p.$$

Too small next. A phrase lasts a time $t$ between two reversals; the reeds that sound during it consume a flow $Q$, plus the leak; one stroke of length $c$ must hold it all:

$$S_{\min} = Q\,t/c.$$

Between the two lies the window, and @fig:bellows-window draws it with round numbers chosen only to make the arithmetic visible: an arm of 40 N, a stroke of 0.4 m, a phrase of 4 s, and a forte chord of nine reeds (three notes of three voices) at 10 L/min each. At 1000 Pa the window runs from 150 to 400 cm². At 2000 Pa it shrinks to 150 to 200 cm². Above about 2700 Pa it closes: a bellows large enough to hold the chord for four seconds can no longer be pushed to that pressure by that arm. The optimum that Ewen guessed is real, and it is the point where the two limits meet.

![The window of the section of a bellows, with round example numbers to be replaced by measurements (outils_atelier.py soufflet). Above $F/p$ the arm no longer makes the pressure; below $Qt/c$ the air runs out before the end of the phrase. For a pianissimo of two reeds (dashed line) the air limit is negligible; it is the forte that closes the window.](figures/pratique_soufflet_en.png){#fig:bellows-window}

Two lessons hold whatever the true numbers. At the pianissimo, two reeds at 2 L/min ask for a section of 7 cm² only: the air side never binds, and the section is set by the forte. And the number of voices enters the minimum directly, which is Ewen's rule in algebra: a third voice is a third more air for the same phrase, and a bellows sized for two voices runs out sooner with three. But none of the inputs of @fig:bellows-window has been measured. The flow of a reed at forte is the least known: the network models of the thesis give 6 to 24 L/min per tongue at 1000 Pa and are known to be too generous.

> To be completed (Ewen): the five numbers of the window, on one of your instruments. The force of your arm for a held forte, with a luggage scale hooked to the strap; the useful stroke of the bellows; the length of a typical phrase between two reversals; the flow of one reed at mezzo-forte and forte, by the descent of the gasometer with the tape removed; and the effective area of the bellows by the drop test. Then outils_atelier.py soufflet draws the true window.

### Where a bellows leaks

The workshop knows where: at the corners and at the frames. The physics adds why the frames are so demanding. A frame is a flat joint, and a long one: about a metre around for a small instrument. By the cube law of the leak chapter, a frame joint 1000 mm long with 10 mm of land and a gap of 0.05 mm, the thickness of a hair, leaks 1.7 L/min at 500 Pa on its own, more than the whole budget of the bellows (under 1 L/min, @tab:leak-budget). At 0.02 mm it leaks 0.11 L/min; at 0.1 mm, 14 L/min. No pair of wooden frames is flat to two hundredths of a millimetre over a metre after a season of humidity, and that is why the frame needs its gasket: the gasket does not close the gap, it fills it.

The corners are the other weak point: leather folded and glued at the place where the card bends most, and where it wears first. A hole there is a hole, not a joint, and @tab:leak-hole gives its weight: one millimetre is almost a litre per minute.

## Making and checking the bellows

**Frames glued, holes drilled, pins fitted.** The bellows must go onto the case without forcing and with no light through. A frame that has to be forced will spring back and open its joint; one with light through it is already a leak of the size of @fig:joint.

**The bellows alone, between two boards.** Close it between two boards with gaskets, hang a known weight, film the descent with a ruler beside it, and pass incense smoke along the corners. The proposed figure is under 1 L/min at 500 Pa. The same measurement gives the effective area of the bellows, $mg/p$, which the window above needs.

> To be completed (Ewen): the bellows is bought, with a lead time of two months. What do you check on arrival, and what makes you send one back?

## At the repair bench

**The instrument tires the player, the drop test is short.** Close the bellows alone between two boards: if the leak stays, it is in the bellows; if it goes, it is in the cases or the frames. Then the smoke, corner by corner.

**Pin-holes in the folds.** A small lamp put inside the bellows in a dark room shows every pin-hole as a point of light; a worn corner shows as a glow.

**Leak at a frame.** Look at the gasket first: crushed, hardened, or torn, it no longer fills the gap, and the cube law says that a few hundredths of a millimetre are enough to lose the budget. Replace it before touching the wood.

**A bellows that has become soft, or stiff.** Card that has lost its spring, or glue that has gone hard at the folds. It changes the feel more than the air, and its measure is the effective area: compare $mg/p$ with that of a bellows the player likes.

> To be completed (Ewen): the repairs of a bellows that you do yourself and those you send away, and how long each takes.
