## The left-hand mechanism: what a finger pays for a pallet

Press a bass button of an accordion while the bellows is being drawn, and the finger meets something before it meets the spring: a small resistance at the very start, a step, and then a softer travel down to the bottom. Press the same button on the push and the step is gone. Nothing in the mechanism has changed between the two gestures. What has changed is the air, and the finger is reading it. This chapter follows that small step back to its cause, and from there to every gram a player pays at the button of the left hand: the pallet, the spring that holds it, the lever that lifts it, the way the parts slide or turn, and the plastic or metal they are made of.

The occasion was practical. Ewen is building the left-hand mechanism of the Lib RT, a free-bass instrument with grave basses, for a jazz player whose present instrument asks too much of his fingers; the aim he was given is 80 to 100 grams at the button. Four printed versions were made, the fifth (v5) plays but grinds, and the question became: is the force in the mechanism, or somewhere else? The answer of this chapter is that most of it is somewhere else, and that it can be computed before anything is built. The figures come from a small calculator written for the purpose (calcul_mecanique.py, kept with the engineering report of the Lib RT); every number below can be recomputed with the true dimensions once they are measured.

### A door against the wind

A pallet is a door. It covers a hole in the soundboard, on the side of the mechanism, and behind the hole is the air of the bellows. When the door is shut, the air pushes on it, and it pushes only where the hole is: around the hole, on the seat, the leather sees the same pressure on both faces. The force is therefore the plainest one in physics, a pressure times an area,

$$F = \Delta p \, A_{\mathrm{hole}}$$

and for the large basses of the Lib RT, a hole of 20 by 15 mm (300 mm²), it is 0.60 N at a playing pressure of 2 kPa and 0.90 N at a peak of 3 kPa. In grams, since that is what a finger knows, 61 and 92 g. Table @tab:pallet-force gives it for the other holes considered.

Table: Force of the bellows pressure on a closed pallet, Δp × A (1 N = 102 g). The critical lift A/P is the lift at which the curtain around the pallet equals the hole. {#tab:pallet-force}
| hole (mm) | area (mm²) | critical lift A/P (mm) | 1 kPa | 2 kPa | 3 kPa | 5 kPa |
|---|---|---|---|---|---|---|
| 20 × 15 | 300 | 4.3 | 0.30 N (31 g) | 0.60 N (61 g) | 0.90 N (92 g) | 1.50 N (153 g) |
| 18 × 15 | 270 | 4.1 | 0.27 N | 0.54 N | 0.81 N | 1.35 N |
| 15 × 15 | 225 | 3.8 | 0.23 N | 0.45 N | 0.68 N | 1.12 N |
| 11 × 27 | 297 | 3.9 | 0.30 N | 0.59 N | 0.89 N | 1.49 N |
| 12 × 12 | 144 | 3.0 | 0.14 N (15 g) | 0.29 N (29 g) | 0.43 N (44 g) | 0.72 N |

Which way does it push? It depends on which side of the board the door is. On an accordion the pallet sits on the outer face, the side of the atmosphere: on the push the air of the bellows lifts it, on the draw the outside air clamps it down. An organ puts its pallet on the other side, inside the wind chest, and the signs swap. There is no free side. Where the pressure helps to open, a spring must be strong enough to keep the door shut against the strongest push of the player; where the pressure resists, the finger pays it at the opening. The sum of the two burdens is the same either way. Only a door that is pushed equally in both senses escapes the bargain, and we shall meet it below.

On the Lib RT the burden falls on the spring. It must hold the pallet shut against the peak of the push, with a margin for the jolts of the bellows, and it must also press the leather hard enough to seal:

$$F_{0} = 1.2 \, \Delta p_{\mathrm{peak}} \, A + F_{\mathrm{seal}}$$

With a peak of 3 kPa and a sealing force of 0.3 N, this is 1.38 N (141 g) at the pallet. A weaker spring leaks at the forte push: the note speaks without being pressed, the old fault of accordions with tired springs.

What does the finger feel while the door opens? Three things are added: the preload, the stiffness of the spring, and the pressure. The last one does not stay. As soon as the pallet lifts, the air runs through two orifices in series, the curtain between pallet and seat (perimeter times lift) and the tongue itself, and the pressure left on the pallet falls as $1/(1+(P x / A_{\mathrm{reed}})^{2})$. For a grave tongue with an effective section of about 20 mm², a quarter of the pressure force is left at 0.5 mm of lift, 8 % at 1 mm, almost nothing at 2 mm. Here is the step of the first paragraph: on the draw the finger first pays 1.38 + 0.60 = 1.98 N at the lift-off, then 1.50 N at one millimetre, then only the spring, 1.56 N at mid-stroke. Organ builders call it the pluck. On the push the pressure helps at the start (0.78 N) and the two directions meet again after a millimetre. The inequality between push and draw lives in the first millimetre and nowhere else.

### The price of lift

Why should the lift of the pallet matter to the finger? Because energy has nowhere to hide. If the button goes down by a travel $c$ and the pallet goes up by a lift $x$, then without losses $F_{b} c = F_{s} x$, and

$$F_{b} = F_{s} \, \frac{x}{c} \, \frac{1}{\eta} = F_{s} \, \frac{r}{\eta}$$

with $\eta$ the efficiency of the chain, about 0.9 with steel pivots. The ratio $r$ of lift to travel is not a detail of the drawing: it multiplies everything. A lift of 10 mm for a travel of 5 mm doubles the force at the button.

And how much lift does the air need? The pallet stops limiting the flow when the curtain around it, perimeter $P$ times lift $x$, equals the area of the hole. For 20 by 15 mm, $A/P$ = 300 / 70 = 4.3 mm; with a margin of 20 %, 5.1 mm. Above that, a pallet that opens further gives no more air, and the pressure on it has already vanished after the first millimetre. A centimetre of lift buys nothing for the sound and costs 60 to 100 % more at the finger. Whether the sound of the tongue is more open beyond $A/P$ is a question for the ear, and the bench can answer it (experiment E-hole below); nothing in the physics expects it.

Table @tab:button-force puts the two together for the large hole: the best that any mechanism can do, $r$ close to 1, gives 160 to 180 g at mid-stroke and 200 to 225 g at the lift-off on the draw. The aim of 80 to 100 g is out of reach with this hole and this peak, whatever the mechanism.

Table: Force at the button for the 20 × 15 mm hole (play 2 kPa, peak 3 kPa, η = 0.9). The last column is the force that brings the button back at the worst moment, a 3 kPa push with the pallet closed. {#tab:button-force}
| travel (mm) | lift (mm) | r | lift-off (draw) | mid-stroke | end of stroke | return at 3 kPa push |
|---|---|---|---|---|---|---|
| 5 | 4.5 | 0.90 | 202 g | 159 g | 176 g | 40 g |
| 5 | 5.0 | 1.00 | 224 g | 177 g | 196 g | 44 g |
| 5 | 6.0 | 1.20 | 269 g | 212 g | 235 g | 53 g |
| 5 | 8.0 | 1.60 | 359 g | 282 g | 313 g | 70 g |
| 5 | 10.0 | 2.00 | 449 g | 352 g | 391 g | 88 g |
| 4 | 5.0 | 1.25 | 280 g | 221 g | 245 g | 55 g |

The last column deserves a moment. At the forte push, the pressure lifts the closed pallet and eats the preload of the spring; what is left to raise the button is the margin, 44 g. Below 35 to 40 g, a key that rubs a little stays down. It is very probably the fault of the player's present instrument: springs that are just strong enough, and some friction.

Where, then, is the force? Table @tab:levers ranks the levers, and the first two are not in the mechanism at all.

Table: Force at mid-stroke on the draw (lift-off in brackets), for r = 1.2. {#tab:levers}
| hole | area (mm²) | play 1 kPa, peak 1.5 kPa | play 2 kPa, peak 3 kPa | play 3 kPa, peak 5 kPa |
|---|---|---|---|---|
| 20 × 15 | 300 | 129 g (155 g) | 212 g (269 g) | 322 g (408 g) |
| 15 × 15 | 225 | 108 g (126 g) | 170 g (212 g) | 253 g (316 g) |
| 12 × 12 | 144 | 86 g (96 g) | 126 g (150 g) | 179 g (217 g) |
| d 10 | 79 | 68 g (71 g) | 90 g (101 g) | 119 g (137 g) |

1. **The hole.** A tongue needs three to five times its effective section to breathe, 60 to 100 mm². The rest of the hole serves the acoustics of the chamber and the way out of the sound. A hole of 12 by 12 mm halves the pressure force; with $r$ = 1 and a peak of 1.5 kPa it gives 72 g at mid-stroke and 80 g at the lift-off.
2. **The real peak pressure.** Between 1.5 and 3 kPa the preload goes from 0.84 to 1.38 N. A jazz player who plays softly may never pass 1.5 kPa; a U-tube manometer says so in an afternoon.
3. **r at most 1.** Travel 5 mm, lift 5 to 5.5 mm.
4. **A long, soft spring**, rising by 15 to 25 % over the lift, not 100 %.
5. **The efficiency**: turning, not sliding (below).
6. **The seat**: a flat seat and a supple leather seal with 0.3 N; a warped seat asks for 0.6 N, which the finger pays.

### Four ways to cheat the wind, and why three of them fail

Can the pressure force be compensated, the way a sash window is balanced by its counterweight? Four ideas come naturally. Figure @fig:compensations draws them in section beside the plain pallet, and its last panel compares what each one leaves at the button, computed with the same assumptions as table @tab:button-force.

![The compensations, in section and in grams at the button (hole 20 × 15 mm, r = 1). Reference: on the draw, pressure clamps the pallet. (a) A small pilot pallet opened first. (b) Two pallets side by side. (c) A balanced pallet: two seats on one stem. (d) A helper spring at the button. (e) Lift-off, mid-stroke and return at the button.](figures/mecanique_compensations_en.png){#fig:compensations}

**The pilot (a).** A small pallet of 6 by 6 mm sits on a hole cut through the large one. The lever lifts it first, through a hook with a little free play; air rushes through the small hole, the chamber behind comes to the outside pressure, and only then does the hook take the large pallet. The pluck of the draw is gone: the lift-off falls from 224 to 165 g, a gain of about a quarter. But look at the mid-stroke: 176 g in both cases. The pilot removes the pressure, which only lived in the first millimetre, and leaves the spring, which must still hold the peak of the push. It costs two pallets per note.

**Two pallets side by side (b).** Two holes of 150 mm² have the same area as one of 300; the pressure force is the same and so is the total spring. Nothing is gained, and the parts are doubled. It is worth drawing only because it is the first idea everyone has.

**The balanced pallet (c).** Here the bargain of the first section is broken. Two discs of equal area are fixed on one stem, and the air of the bellows lies between two plates: the upper disc rests on the upper plate, outside, and the pressure under it pushes it open; the lower disc rests on the lower plate, inside, and the same pressure pushes it shut. Both open by moving the same way. The two thrusts cancel, whatever the sign of the pressure, push or draw, and the spring no longer has to hold the peak: only to seal, 0.3 to 0.5 N. At the button this is 45 g at the lift-off and 51 g at mid-stroke. It is the only solution that reaches 80 g on a hole of 300 mm². The engineers of steam knew it as the double-beat valve. Its price is real: a seat on the side of the bellows or a sealed passage for the stem, two holes per note, and a design that has never been tried on an accordion and must be proved on the bench. It is kept here as a research path, not as the base of the Lib RT.

**The helper spring (d).** A spring that pulls the button down with a constant force subtracts from the effort, and subtracts just as much from the return. With 44 g of return at the forte push, it can be given 5 to 10 g at most; the panel shows 168 g at mid-stroke and 36 g of return, at the edge of a key that stays down. It does nothing useful here.

The lesson of the figure is the lesson of the whole chapter. The force is in the hole and in the pressure, the two quantities the mechanism does not touch; the balanced pallet is the one idea that reaches into them, and it does so by changing the door, not the lever.

> To be completed (Ewen): the lift-off of one pallet on the draw, measured with a spring balance hooked to the pallet and pulled slowly, then the force at 1, 2, 3 and 5 mm of lift (shims under its edge). Does the step of the first millimetre have the size the curve predicts?

### Returns, one spring, and the space before the force

On a chromatic accordion the same note appears on several rows, and the second button, the return, drives the same pallet through a longer chain. Two buttons, one door: will the finger feel the same force on both? It will, if the two chains have the same ratio $r$ and if a single spring, the spring of the pallet, brings everything back. Each extra steel pivot of the return costs 0.2 to 1 % of the force; three of them, 1 to 3 %, 2 to 5 g on 180 g. The finger does not notice differences below 7 to 10 %. A second spring on the return, on the other hand, would add all of its force to that button alone; it is the one thing to avoid.

Lost motion is subtler. A chain that a spring keeps loaded, the spring at one end and the button at the other, every joint attached, has no dead travel from its clearances: on the way down and on the way up each joint stays pressed against the same side. The clearances show up instead as sideways float and noise. A button merely resting on a lever with a gap between them has a dead travel equal to the gap. At the button, 0.1 to 0.2 mm is tolerable, 2 to 4 % of the travel; above it the finger feels a void before the resistance. And the lift has its own budget: the lift beyond the useful $1.2\,A/P$ must cover the bending of the lever under the playing force and the crushing of leather and felt. For a lift of 6 mm on the large hole the budget is 0.9 mm, for 5.5 mm it is 0.4 mm, for 5 mm nothing at all.

### Sliding against turning

The v5 grinds. Why does a steel rod sliding in a printed hole grind, when the same rod turning in the same hole does not?

Friction, first. Steel on printed PLA has a coefficient of 0.35 to 0.45 at rest and 0.25 to 0.35 in motion. That difference is enough for stick-slip: the rod sticks, the elastic chain that pushes it loads up, the rod jumps, and the cycle repeats in the kilohertz. That is the grinding. PTFE (0.08 at rest, 0.05 moving) or oiled sintered bronze have almost no difference between the two, and do not grind. Then the layers: a hole printed vertically has steps of 0.18 to 0.24 mm across the motion, and the rod climbs one at every layer.

But the largest effect is geometric, and it is shown in figure @fig:drawer. When the force on the rod is offset from its axis by $e$, through a pin for instance, the rod tilts in its guide of length $L$ and bears at both ends with a force $N = F e / L$. Friction acts at both ends, $2 \mu N$, against the motion, so that

$$F_{\mathrm{push}} = \frac{F_{\mathrm{useful}}}{1 - 2 \mu e / L}$$

and the rod jams when $2 \mu e / L$ reaches 1. The v5 has its pin 5 mm off a guide 8 mm long, in PLA: the factor is 2.0, the finger pays double. If the real bearing of the guide is only 4 mm, with chamfers and layer steps, the rod jams now and then. The rule that follows is short: guide length at least $10 \mu e$, 20 mm for PLA and 5 mm for PTFE, or better, push along the axis.

![The drawer effect. A force offset by e makes the rod bear at both ends of its guide; the force needed rises as 1/(1 − 2µe/L) and the rod jams at 2µe/L = 1. The dotted line is the v5.](figures/mecanique_tiroir_en.png){#fig:drawer}

Now turn the rod into a pivot. In a pivot, friction acts only at the radius of the axle, so the loss is $\mu (d/2) / \ell$ for an arm $\ell$. With a steel axle of 2 mm in raw PLA ($\mu$ = 0.4) and an arm of 60 mm, the loss is 0.7 %. A pivot loses 30 to 100 times less than a slide (table @tab:remedies). This is the whole argument for a mechanism where each key is one rotation, and against a guided rod.

Table: Remedies for a sliding rod (useful force 1, offset 5 mm), against a rotation. {#tab:remedies}
| guide | µ | L (mm) | force factor |
|---|---|---|---|
| PLA as printed | 0.40 | 8 | × 2.0, stick-slip |
| PLA, lengthened | 0.40 | 20 | × 1.25 |
| PA printed, drilled and reamed | 0.30 | 12 | × 1.33 |
| brass tube 3 × 2, oiled | 0.19 | 10 | × 1.23 |
| PTFE sleeve (Bowden liner 2 × 4) | 0.08 | 8 | × 1.11, no stick-slip |
| **rotation on a 2 mm steel axle, arm 60 mm** | 0.40 | - | × 1.007 |

The v5 also has thin steel rods running at an angle between a printed bracket and the aluminium lever. Ewen's correction is worth recording here, because it corrected the analysis: in practice these rods do not buckle, and the computation agrees (the Euler load stays above the force carried). Their real cost is the angle. A rod at 30° to the useful motion carries 15 % more force and pushes the pivot sideways with 58 % of the useful force; if a guide takes that sideways load, a quarter of the effort goes into friction. A rod in tension does not suffer from any of this: it cannot buckle, it aligns itself on its two attachments, it can be a thin cable that passes between the others, and the chain loaded by the spring stays taut, with no dead travel. Attaching the rod on the other side of the bracket's pivot is enough to make the finger pull it instead of pushing it.

### Pivots that do not wobble

A printed hole is never what was drawn: 0.1 to 0.3 mm too small, round if printed vertically, oval by as much if printed lying down. The contact pressure is not the problem, 0.5 MPa for 3 N on an axle of 2 mm over 3 mm, against 10 MPa admissible. The problem is tilt. A lever on a short hub swings on its own clearance: the end moves by the clearance divided by the hub length, times the lever length (table @tab:tilt). 0.05 mm of clearance on a 3 mm hub moves the end of a 100 mm lever by 1.7 mm, and with 5 mm between levers, neighbours touch.

Table: Sideways movement of the end of a 100 mm lever (mm), from the clearance of its hub. {#tab:tilt}
| diametral clearance (mm) | hub 2 mm | hub 3 mm | hub 6 mm | hub 9 mm |
|---|---|---|---|---|
| 0.02 | 1.00 | 0.67 | 0.33 | 0.22 |
| 0.05 | 2.50 | 1.67 | 0.83 | 0.56 |
| 0.10 | 5.00 | 3.33 | 2.50 | 1.11 |

No realistic hub holds the end of a long lever within half a millimetre. The accordion solved this long ago with a comb at the end of the levers, slots lined with felt: the clearance of the hub then matters only for noise. Two staggered axles, even levers on one and odd on the other, let each hub be twice as long. And a reamed hole or a pressed brass tube brings the clearance itself to 0.02 to 0.05 mm.

There is a pivot with no clearance and no friction at all: a thin blade of spring steel, clamped on both sides, that bends instead of turning. A lever turns by about 0.1 rad (6 mm of lift on a 60 mm arm); a blade 0.15 mm thick and 5 mm long then carries 309 MPa, below the 600 to 700 MPa of fatigue of spring steel, and lives forever. Its own return torque is small, 0.1 N at the 60 mm arm, a help but not the spring. The printed living hinge is its plastic cousin: only polyamide, 0.4 to 0.6 mm over 3 to 5 mm, survives a million bends (a heavily played key sees 100 000 a year); PLA cracks after a few hundred. And a hinge creeps under the permanent load of the spring, so its rest position drifts: good for small brackets, not for the main pivot.

### Stiffness, not strength

What should a lever be made of? Not what one would first think. The stresses in a lever are everywhere small, below 15 MPa; nothing breaks. What matters is how much it bends, because every tenth of a millimetre of bending is taken from the lift or added to the dead travel. The admissible bending at the button is 0.2 to 0.3 mm. A rocking lever, button on one side of the axle and pallet on the other, bends as a cantilever from the axle:

$$\delta = \frac{F L_{b}^{2} (L_{b} + L_{s})}{3 E I}, \qquad I = \frac{b h^{3}}{12}$$

and the width $b$ is fixed by the spacing of the keys: 3.5 mm when three rows share a 15 mm band, 6 mm with two rows. Under the playing force of the large hole, 1.5 N, PLA 3 by 7 mm bends 0.93 mm on 60 + 60 mm arms: four times too much, and it creeps, so the buttons sink with the months. ASA 3 by 12 mm holds to 60 + 60 mm (0.23 mm); carbon-filled polyamide 2.5 times better; beyond 80 mm only metal on edge holds: aluminium alloy 2 by 8 mm bends 0.16 mm on 100 + 100 mm.

On edge is the important phrase. The stiffness goes with the cube of the height. The same strip of aluminium, 8 by 2 mm, is 16 times softer laid flat than standing on its edge: 2.6 mm against 0.16 mm under 1.5 N on 100 + 100 mm. The photographs of the v5 suggest flat levers; if the button pushes vertically, that is the soft way, and it is the first thing to check (100 g at the end, a dial gauge).

### Springs: steel or nothing

Why not print the springs too? Because a plastic under a permanent stress forgets its shape. At 23 °C PLA is only 35 K below its glass transition; under a few megapascals its chains slide slowly, and the imposed deformation becomes permanent. A printed spring loses 20 to 40 % of its force in a few weeks, and almost all of it in an afternoon at 50 °C, in a car in summer. Spring steel works at a fraction of a percent of strain with no flow at all, and stores 20 to 80 times more energy per volume. One steel spring per pallet, none at the button. For a preload of 1.38 N at a 60 mm arm and a rise of at most 25 % over the lift, a torsion spring on the axle of wire 1.0 to 1.2 mm, 7 to 10 mm in diameter, 8 to 12 coils, preloaded by 45 to 100°; or a tension spring of wire 0.5 mm, 5 mm in diameter, 15 coils, hooked 25 mm from the axle. The springs Ewen already has are usable once their stiffness is measured with a few coins: the rule is that a stiff spring hooks near the axle and a soft one further out.

### What the models leave out

The pressure on the opening pallet is a quasi-static model of two orifices in series; the transient at the lift-off, where the air running under the seat may briefly push on the whole pallet (up to 1.09 N instead of 0.60 at 2 kPa), is bounded, not computed. The effective section of the tongue, 20 mm², is estimated from the flow of a grave bass and should be measured by timing the emptying of the bellows on one note. The efficiency of 0.9 is for steel pivots; 0.95 with a PTFE comb, 0.8 with raw PLA pivots. The levers are beams of constant section with a point load; a lightened lever is softer. The data of printed materials are good to 20 %, and their fatigue is an order of magnitude: one endurance test is worth more than the table.

Underneath these limits there is something worth saying plainly. The first question was where the force goes, and the answer came before any part was cut: in the hole and in the breath of the player, not in the cleverness of the levers. The mechanism can only add to that floor, a little (2 to 4 % for one rotation per key) or a lot (10 to 100 % for a guided rod). A good mechanism is one that adds almost nothing, and lets the finger feel the air.

> To be completed (Ewen): the peak pressure of the jazz player, on a U-tube connected to the bellows, pianissimo to sforzando, push and draw. It is the number that weighs most on everything above. And, if you wish, the sensation itself: what the step of the first millimetre feels like under the finger, before and after you know what it is.
