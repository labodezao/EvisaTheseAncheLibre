# Valves and leaks

## The air that does not sing

A leak is air that escapes without making music. It is invisible and almost silent, and yet a player knows it at once without being able to name it: the instrument is tiring, the soft notes start badly, the attack is woolly, and sometimes a note sounds faintly that nobody played. This chapter asks what a leak is, physically, why it does exactly these things and not others, how big it must be before it matters, and how to find it with almost nothing.

### Why a leak spoils the playing

Three things are certain, and two are probable.

Every leak eats air. The bellows must move more for the same sound, so it reverses more often and the arm tires sooner. That much is plain arithmetic.

A tight instrument can be put under pressure before the note. The player squeezes the bellows, nothing moves, and the pressure waits behind the closed pallets; when a pallet opens, the reed receives the whole pressure at once and the attack is clean. With a leak, the pressure falls as soon as the arm stops pushing, and at the attack it starts again from almost nothing: the transient is soft.

The physics of the reed adds the third certainty. A reed starts at a pressure $p_{\mathrm{on}}$ but, once sounding, holds down to a lower pressure $p_{\mathrm{off}}$: the hysteresis studied in the thesis. The softest pianissimo is obtained by attacking just above $p_{\mathrm{on}}$. If the pressure at the attack is uncertain, because air leaks away, the reed either does not start or starts too loud. A leak is felt first at the threshold, which is where the musician asks for the most precision.

Two more things are probable. A leak close to a reed, in the wax around its plate or under a valve that does not close, is in parallel with the reed, behind the pallet and the channel: it lowers the pressure that the reed actually sees. And a pallet or a valve that leaks feeds a chamber that should be silent; if a reed of that chamber is close to its threshold, it sounds faintly. That is the ghost note.

### Two laws for one leak

How does air go through a gap? It depends on the shape of the gap, and there are only two shapes worth knowing.

The first is the hole: a short opening in a thin wall, a crack in a corner, a pin-hole in a leather. The air rushes through it as a jet, and its flow follows the law of an orifice,

$$q = C_d\,S\,\sqrt{2\Delta p/\rho}$$

where $S$ is the area of the hole, $\Delta p$ the pressure difference, $\rho$ the density of air and $C_d \approx 0.6$ the contraction of the jet. The flow grows with the area, so with the square of the diameter, and only with the square root of the pressure. @tab:leak-hole gives a few values, and gives the habit of this book: a leak is said in litres per minute at 500 Pa, about 5 cm of water, a mezzo-forte, and pictured as the round hole that would leak as much.

Table: Leak of a round hole, orifice law with $C_d$ = 0.6 (outils_atelier.py trou). {#tab:leak-hole}
| hole diameter (mm) | at 100 Pa (L/min) | at 500 Pa (L/min) | at 1500 Pa (L/min) |
|---|---|---|---|
| 0.3 | 0.03 | 0.07 | 0.13 |
| 0.5 | 0.09 | 0.20 | 0.35 |
| 1 | 0.37 | 0.82 | 1.4 |
| 2 | 1.5 | 3.3 | 5.7 |

A hole of one millimetre already lets almost a litre per minute through.

The second shape is the flat joint: two surfaces that should touch and do not quite, a plate on its wax, a reed block on its gasket, a frame on a frame, a register slide on its bed. Here the air does not jet; it creeps through a gap far thinner than it is long, and viscosity rules. Between two plane faces a distance $h$ apart, over a length $w$ of joint and across a land of width $L$, the flow follows the law of Poiseuille,

$$q = \frac{w\,h^{3}\,\Delta p}{12\,\mu\,L}$$

with $\mu$ the viscosity of air. Two features make this law the most useful one of the whole book. The flow is proportional to the pressure, not to its square root, so a joint and a hole can be told apart by measuring at two pressures: a leak that doubles when the pressure doubles is a joint; one that grows by only 1.4 times is a hole. And the flow grows as the cube of the gap. Halve the gap, divide the leak by eight. A joint is not a little worse when it is a little open; it is enormously worse.

![Leak of a flat joint of 100 mm around and 5 mm of land, at 500 Pa, against its gap (Poiseuille law). The points mark the gap that gives each proposed workshop figure. Doubling the gap multiplies the leak by eight.](figures/pratique_joint_en.png){#fig:joint}

@fig:joint puts numbers on it for a joint the size of a plate or a small block: 100 mm around, 5 mm of wood to cross. To stay under 0.05 L/min, the gap must be under 0.026 mm, the thickness of a thin sheet of paper. At 0.05 mm, the thickness of a hair, the same joint leaks 0.35 L/min, seven times the target. This is why a block must be flat and a plate must be bedded, and why wax works: it fills a gap that no plane could close. The law holds while the flow in the gap stays slow and orderly, which outils_atelier.py checks by the Reynolds number: under 4 up to a gap of 0.05 mm, about 30 at 0.1 mm. The flow is laminar over the whole figure; only at the largest gaps do the losses at the entrance of the gap, which the law ignores, start to count, and there the law slightly overestimates the leak.

> To be completed (Ewen): two or three real joints measured at 250 and 500 Pa (a plate, a block, a frame), to see whether they behave as joints (flow doubled) or as holes (flow times 1.4). The protocol of the next chapter does it with the same gasometer.

### How big is too big

The workshop figures, from the booklet of the training course, are proposals, not yet measured on Ewen's instruments. They are given with that status in @tab:leak-budget, step by step, in the order the instrument is built.

Table: Proposed leak figures at 500 Pa, by step of construction (booklet of the training course; to be calibrated). {#tab:leak-budget}
| step | piece under test | proposed figure |
|---|---|---|
| soundboard | each pallet, by the bell | under 0.02 L/min; no pallet lifts below 1.5 times the highest playing pressure |
| bellows | the bellows alone, between two boards | under 1 L/min |
| reed block | glued, bare, then with its plates (slots taped) | under 0.05 L/min |
| case | closed case with mechanism and register slides | under 0.5 L/min |
| whole instrument | drop test, push and draw | time to be set by Ewen |

Where do these figures come from, and what should the last one be? Here a little arithmetic is worth more than a tradition. A high reed played pianissimo probably consumes of the order of 1 to 2 L/min (an effective opening of 1 to 3 mm² under 100 Pa; to be measured, the next chapter says how). The drop test that the workshop calls good, a bellows of 10 litres that takes a minute to fall, is a leak of 10 L/min: more than the reed itself. Such an instrument plays, but its pianissimo is spent on the leak. Two levels follow, to be confirmed on two or three instruments Ewen knows, one he finds excellent and one mediocre: a workshop level, under about 10 L/min (the 10 litres fall in more than a minute), and a pianissimo level, under 2 to 3 L/min (the fall takes three to five minutes).

> To be completed (Ewen): the drop time and the softest pianissimo of a high note, on an instrument you find excellent and one you find mediocre. The threshold of the whole instrument lies between the two.

## Measuring a leak with almost nothing

### The tools of the bench

Four tools do nearly everything, and three of them cost nothing.

**The U-tube.** A transparent hose bent in a U, half filled with water with a drop of washing-up liquid, on a board with a ruler. The difference of the two levels, in millimetres, times 9.81, is the pressure in pascals; roughly, 1 mm is 10 Pa. It is the reference against which every other gauge is checked.

**The kitchen gasometer.** A plastic box turned upside down, floating in a bucket of water, guided by two rods and weighted. Its weight sets the pressure, $p = mg/S$: for a box of 150 cm² and 500 Pa, about 0.77 kg, box included. A hose passes under the water and joins the air of the box to the piece under test. If the piece leaks, the box sinks, and the flow is the area times the speed of descent: with 150 cm², 1 L/min is 6.7 cm per minute, and 0.1 L/min is 6.7 mm per minute. It gives a constant pressure and an absolute flow, without any electronics.

**The bell.** A small pot of about 0.4 L with a foam rim, placed on the outside of one closed pallet while the instrument is under pressure inside. The leak fills the bell and its pressure rises; a hose takes it to the U-tube. For a leak of the orifice type, the time to reach half the pressure is about $0.59\,V\,P/(p_{\mathrm{atm}}\,Q)$: with 0.4 L and 500 Pa, 3.5 s for 0.02 L/min and 35 s for 0.002 L/min. A pallet that brings the bell to half pressure in less than 3 s leaks more than the target. One pallet at a time, without taking anything apart.

**The pressure decay.** The piece is closed with a known buffer volume, a 1.5 L bottle for instance, inflated to about 600 Pa, closed, and the pressure is recorded as it falls (command LEAKTEST of the bench, analysis by banc_recherche/leak.py). The buffer is needed because air in a small volume is a very stiff spring: a small piece empties in a fraction of a second. A rule of thumb: with a 1.5 L bottle, if the pressure takes more than 2 s to fall from 500 to 400 Pa, the piece leaks less than 0.05 L/min, to within 30 per cent; check it on a reference leak. For a whole instrument the decay is far too fast, and the gasometer, or the bellows itself, takes over.

Before believing any of them, test the bench itself: a blanking plate on a sheet of glass must not leak; then the bench must read correctly the reference leaks of a plate drilled with holes of 0.3, 0.5 and 1 mm, whose flows are in @tab:leak-hole.

Two rules of safety go with every leak test: never a flame to look for a leak (celluloid, wood, glue and leather burn), and no soapy water on wood, leather or card; soap only on metal, plastic and rubber.

### The order of the checks

A leak is found far more easily on a piece alone than in the finished instrument. The checks therefore follow the construction, each one on a piece that is still open to the eye: bench first, then the bare glued block, the block with its plates and their slots taped (in both directions, pressure and suction), then the flow of each reed with its tape removed (a measurement, not an examination: the air consumed by that reed at 100, 300 and 500 Pa), then the soundboard with its pallets under the bell, raising the pressure until a pallet lifts, then the closed case, the bellows alone, and the whole instrument by the drop test. @tab:leak-budget gives the proposed figure of each.

### The drop test, in figures

The drop test is already done in every workshop; it only needs to be counted. The instrument hangs, a known weight pulls the bellows open, the air valve is shut and no key is pressed. The pressure is read on the U-tube through the air valve, and the opening of the bellows against time with a ruler and the video of a phone. Two numbers come out. The effective area of the bellows, $S = mg/p$. And the leak, $Q = S \times$ speed. Two different weights give two pressures, and so tell a joint from a hole.

Table: Drop test of a bellows that sweeps about 10 litres under 600 Pa: leak and equivalent hole (outils_atelier.py chute). {#tab:drop}
| full drop in | leak (L/min) | equivalent hole (mm) |
|---|---|---|
| 30 s | 20 | 4.7 |
| 1 min | 10 | 3.3 |
| 2 min | 5 | 2.4 |
| 5 min | 2 | 1.5 |

What practitioners say, in repair guides and forums rather than in studies, fits @tab:drop: under 20 to 30 seconds there is a frank leak to find; a good instrument holds at least 30 seconds; a very good one a minute or more. The arithmetic of the previous chapter says that a minute is still a leak larger than a pianissimo reed.

## Finding a leak

Once a piece is known to leak, where? The gestures go from the cheapest to the cleverest.

**Smoke.** A stick of incense moved slowly along the joints, piece under pressure: the smoke is blown away where the air leaves. Or piece under suction: the smoke is drawn in. **A tube to the ear**, a mechanic's stethoscope made from a hose, moved at 5 mm from the joints with the piece at 1500 Pa or more: the noise of a turbulent jet grows very fast with its speed, so tripling the pressure makes the hiss 14 to 19 dB louder.

**Making a leak sing.** A jet through a small hole is turbulent and hisses, with a noise that rises high, up to the ultrasound, where the voice of the reeds and the noise of the room are weak. The hiss is still lost in the room. The method proposed in this work makes it stand out by giving it a rhythm: the bellows modulates the pressure slowly, as a sine at a known frequency of 2 to 10 Hz, and every leak then hisses louder and softer at that frequency. A cheap microphone moved over the surface records; the program keeps the band of the hiss, about 4 to 20 kHz, takes its envelope, and keeps only what beats exactly at the frequency of the bellows, with the right phase. This is synchronous detection, the lock-in amplifier of the physics laboratory: everything that does not beat at our rhythm is rejected, and the leak appears on a map (banc_recherche/leak.py: lockin, acoustic_leak_strength, leak_map). Two fixed microphones can also locate a leak without moving: its hiss reaches them with a small delay that depends on its position, and the cross-correlation of the two signals gives that delay.

**Making a leak visible.** Two further methods are proposed and not built. Background-oriented schlieren films a printed speckled background through the jet: air of a different density bends the light a little, and a program comparing the images reveals the invisible jet, all the more if the air is warm and moist like a breath. Or the bellows is filled with carbon dioxide and the surface scanned with a small gas sensor of a few euros: the concentration rises at the leaks.

**Letting each reed sign its leak.** A leak near a reed steals part of its air: the reed starts later, sounds softer, and goes out of tune in its own way. The tuner of this work already measures the deviation, the level and the response time of each reed; a local leak leaves its trace there, without any scanning microphone.

> To be completed (Ewen): which of these you already use, and the two you would like to try first. And the area of the box of your gasometer.

## At the repair bench

**Every note soft at the attack, the instrument tiring.** A global leak. Count the drop test, push and draw; if it is under a minute, close the instrument piece by piece (bellows between boards, then each half-case) and find where the air goes before looking for the spot.

**A ghost note at the fortissimo.** Either a pallet that lifts (the right-hand part gives the force its spring needs) or a valve of the silent tongue that does not close. The bell on the suspect pallet answers the first; the second is found by the reed itself: a reed that sounds faintly in the wrong direction has a valve to replace.

**One note late and soft, the others fine.** A leak near that reed: the wax around its plate, its valve, its chamber. Tape the slot of its tongue and test the block on the gasometer; flow that disappears when the plate is pressed down is a plate to rewax.

**Wax and gaskets.** A joint that leaks is not cured by more pressure on it but by a smaller gap: rewax the plate with a continuous bead, flatten the face of a block on abrasive paper laid on glass, replace a crushed gasket. The cube law says why a gap halved is a leak divided by eight.

> To be completed (Ewen): the gestures you use to repair a leaking valve, a leaking pallet and a leaking plate, with their materials, so that this list is the one of your bench.
