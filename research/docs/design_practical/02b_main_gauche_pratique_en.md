## Building the mechanism

The previous chapter said where the force at the button comes from, and why the hole and the pressure weigh more than the levers. The next three chapters are the workshop side of it: what to make each piece of, how to print it, how to place the pallets when the buttons are closer together than the pallets can be, how to spring and adjust seventy keys, what to measure with almost nothing, and how to decide whether the fifth version is worth repairing. The figures come from the calculator of the Lib RT engineering report (calcul_mecanique.py).

### The geometry to start from

A rocking lever with equal arms, button side and pallet side ($r$ = 1), for instance 60 + 60 mm or 80 + 80 mm, its axle halfway between the button plate and the soundboard. Travel 5 mm, lift 5 to 5.5 mm. The upper stop is the pallet on its seat: the button rests on the lever, the lever on the pallet, and there is no dead travel. One steel spring per lever, none at the button. This is "idea 1": one rotation per key, against the four to six joints of the v5.

### Materials from the stock, and what a purchase would change

The rule with what is already in the workshop is short: **ASA for everything printed and loaded, PETG for buttons and hinges, PLA for nothing mechanical.** The purchase that changes most is carbon-filled polyamide (PA-CF): short levers and brackets 2.5 times stiffer and little creep.

Table: Choice of material for each piece, from the stock (PLA, PETG, ASA), then with a purchase. {#tab:materials}
| piece | best from stock | why | to buy | gain |
|---|---|---|---|---|
| levers up to 60 + 60 mm, 5 mm spacing | ASA 3 × 12 on edge, 6 walls | 0.23 mm under 1.5 N, 98 °C, moderate creep | PA-CF 3 × 12 | 0.09 mm, allows 80 + 80 mm |
| levers up to 80 + 80 mm, 7.5 mm spacing | ASA 5 × 12 | 0.32 mm (limit) | PA-CF 5 × 12 | 0.13 mm |
| levers above 80 mm, long return bars | metal on edge (aluminium 2 × 8, steel 1.5 × 8, water-jet) | no plastic of the stock holds 0.3 mm | - | metal stays |
| pivots, hubs, brackets | ASA, drilled and reamed 2 H7, or brass tube 3 × 2 | 98 °C under the permanent preload | PC or PA-CF | button height drift ÷ 2 to 3 in a year |
| button guides (sliding) | ASA + PTFE sleeve or brass tube | all three plastics rub hard on steel | PA or POM | with a PTFE sleeve the gain vanishes (× 1.1) |
| frame, button plate | ASA (PETG if ASA warps) | a PLA plate under 70 springs warps in summer | PC | heat resistance only |
| buttons | PETG or ASA | no load | - | - |
| living hinges | PETG 0.4 mm over 5 mm (~10 000 cycles) | PLA cracks in 10 to 100 | PA 0.4 to 0.6 mm | over 10^6 cycles |
| springs | steel coil springs of the stock | no creep | - | - |

### Printing

- Print a lever **lying in its plane of rotation**: the axle hole vertical (round, not oval), the strands along the lever, so that bending pulls on the strands and not on the layer interfaces (which keep only 50 to 70 % of the stiffness).
- Nozzle 0.6: a 3 mm lever is five walls, solid; set six walls or 100 % infill, layers 0.2 mm. Thirty per cent infill is for large unloaded supports only.
- Frames and supports: PETG at least (68 °C), ASA or PC if the instrument may stay in a car (60 to 70 °C in summer); PA-CF for what carries an axle or a spring.
- PA and PA-CF: dry the filament, anneal 2 h at 80 °C to stabilise the dimensions before reaming.

### When to use metal (rods of the stock: 1, 1.5, 2, 3 mm)

- Levers longer than 60 mm and long return bars: aluminium 2 mm or steel 1.5 mm on edge, water-jet cut like the present mechanism rods.
- Everything under the permanent load of the spring: axles, hubs (brass tube), spring anchors.
- Individual lever axles: 2 mm. A common axle through all levers of a band, and the axles of the return bars: 3 mm, supported every 40 mm (0.02 mm of deflection under 2 N per lever at 5 mm spacing).
- Link rods: 1.5 mm in compression, 1 mm in tension. Better in tension: attach the rod on the other side of the bracket pivot so that the finger pulls it.

### Buttons at 15 mm, pallets at 17.5 mm

The buttons are 15 mm apart, a pallet with its seat needs 17.5 mm. Three layouts hold.

Table: Placing pallets at 17.5 mm under buttons at 15 mm. {#tab:pitch}
| layout | force | room | complexity |
|---|---|---|---|
| fan of levers (angle at most 7 to 10°) | + 2 to 5 % friction | none | 43 different levers, one parameter in the CAD |
| pallets on two staggered rows (30 mm per row) | + 0 % | + 25 mm of depth | two lever lengths, equal r through the arms |
| pallets at 15 mm with a hole 11 × 27 mm | + 0 % | none | new soundboard and chambers; same area, A/P 3.9 mm |
| cranked arms | + 0 % in metal | none | in plastic, torsion adds 0.15 mm and a tilting moment |

Proposed: a **fan** if the levers are metal and at least 100 mm long (angle 7° or less, 5 % of friction at most); **two rows** if they are short (60 mm). Both combine (a fan of 3°).

### Springs, and seventy keys alike

- One steel spring per pallet, on the lever: preload 1.0 to 1.4 N at the pallet for a hole of 300 mm² and peaks of 2 to 3 kPa, stiffness 0.06 to 0.07 N/mm (25 % rise over the lift).
- Torsion spring on the axle: wire 1.0 to 1.2 mm, diameter 7 to 10 mm, 8 to 12 coils, preload 45 to 100°. Wire 0.8 mm is overstressed.
- Tension spring (as on the v5): wire 0.5 mm, diameter 5 mm, 15 coils, hooked 25 mm from the axle, 10 mm of preload stretch. A stiff spring (1 N/mm) hooks near the axle (15 mm) and pulls 5.5 N, so the rail must hold 70 × 5.5 N = 385 N; a soft one (0.15 to 0.25 N/mm) hooks 25 to 30 mm out and pulls 3 N.
- Commercial springs vary by 10 %; for 5 g of spread at the button, each key needs an adjustment: the anchor on an M3 screw (a quarter turn is about 2 g at the button) or a torsion leg that is bent.
- Every button is set to the same force, and the largest hole sets the level: the small notes get a stronger spring than they need.

## Measuring with almost nothing

Equipment: a kitchen scale (1 g), coins (1 c = 2.3 g, 5 c = 3.9 g, 10 c = 4.1 g, 20 c = 5.7 g, 50 c = 7.8 g, 1 € = 7.5 g, 2 € = 8.5 g), a 0 to 500 g spring balance, a dial gauge on a stand, feeler shims, a clear tube of 1 m and a ruler, a telephone (sound level, recorder, slow motion), a drill for the endurance bench.

1. **Bellows pressure (U-tube).** Half-filled tube, one side connected to the inside of the bellows; play a grave bass from pianissimo to sforzando, push and draw, and film the tube. Δp = h × 0.098 kPa per centimetre. It is the number that sets the spring and the force.
2. **Pallet on the bench.** One pallet on a block with the hole, connected to the bellows or a vacuum cleaner with an adjustable leak. Sealing: coins on the pallet without spring, the least mass without whistle at 3 kPa (soapy water around the seat). Lift-off on the draw: a spring balance on the pallet, pulled slowly; then the force at 1, 2, 3 and 5 mm of lift.
3. **Smallest hole for a BB95 tongue.** Plates with holes of 300, 225, 144 and 100 mm², lifts of 1 to 8 mm; level at 50 cm, recording, pitch. The smallest hole and lift with no audible loss: every square millimetre less is force less at the button.
4. **Force at the button, hysteresis, return.** A light cup on the button, coins until it goes down, then remove until it comes back up. Hysteresis = down − up = twice the friction; aim below 25 g. Again bellows inflated (push) and deflated (draw). Ten grave keys, five returns, five high ones. The same on the reference Maugein: it is the number to beat.
5. **Dead travel and float.** Dial gauge on the button, a second one on the pallet edge; lower the button in steps of 0.05 mm: travel before the pallet moves is the dead travel, aim below 0.2 mm. Push the button sideways with 50 g: aim below 0.3 mm.
6. **Stiffness of a lever.** Lever clamped at its axle, 100 g at the button point, dial gauge; then turned by 90°: the ratio must be (h/b)².
7. **Sliding rod (v5).** Spring balance along the axis, then through the offset pin: the ratio is the drawer factor. Record 20 presses at 10 cm, count the squeaks. Again with a PTFE sleeve, then a brass tube.
8. **Creep and heat.** Three identical pieces: at rest, under load for a week, under load 2 h at 50 °C. Expected: PLA − 20 to − 40 % in a week and collapsed at 50 °C, PETG − 10 %, PA-CF − 5 %, steel 0.
9. **Endurance.** A cam on a drill pressing a key at 2 to 3 Hz: 10 000 cycles in an hour; force, dead travel and noise before and after.
10. **Repetition.** Metronome; repeat the gravest note and a return, faster and faster until a note is missed. Aim: 8 notes per second, no difference between key and return.
11. **Springs of the stock.** Length at rest, then with 100 g and 200 g: k = 0.98 N / (L2 − L1). Leave 24 h under 300 g: if it has grown, it was stretched past its elastic limit.

## Saving the v5?

The v5 (a button sliding in the plate, a pin, a printed bracket, a link rod, an aluminium lever with a tension spring) can be repaired in four light gestures: PTFE or brass sleeves in the plate; 2 mm steel axles in reamed holes or brass tubes in the brackets; brackets and supports reprinted in ASA; link rods put in tension. This brings the lost force from + 100 % to + 10 to 15 % and the clearance from 0.2 to 0.05 mm per pivot. What stays, by principle: four to six joints per key against one or two for idea 1, rods at an angle that load the pivots sideways, the routing of the 27 returns under the plate, and a remaining slide at the button.

Table: The defects of the v5, their cause, and the lightest correction that keeps its principle. {#tab:v5}
| defect | cause | lightest correction | gain |
|---|---|---|---|
| button rod grinds and is hard | µ 0.4, stick-slip; pin 5 mm off a guide of 8 mm: force × 2 | PTFE sleeve 2 × 4 in the plate, bearing 10 to 12 mm; or oiled brass tube | × 1.1 (PTFE), × 1.2 (brass), no stick-slip |
| button wobbles | hole printed on its side: oval by 0.1 to 0.3 mm | the same sleeve; an entry chamfer | float 0.3 to 0.1 mm |
| clearance of the printed pivots | raw hole, short hub | drill and ream 2 H7 or pressed brass tube, 2 mm music-wire axle | 0.02 to 0.05 mm per pivot |
| creep of PLA | 57 °C, strong creep under the permanent preload | reprint the same files in ASA, PETG for buttons | button drift ÷ 3 to 5 |
| rods at an angle | at 30°: 58 % of the force sideways, + 23 % friction if guided | turn the brackets so the rod runs in the plane of the lever; or a cable in tension | friction + 23 % to + 7 % |
| no room for the return rods | rigid rods in compression must be straight and must not touch | returns by two brackets and a link, or cables in tension on two levels | crossings without contact |
| aluminium levers soft | if laid flat (8 × 2): 2.6 mm under 1.5 N on 100 + 100 mm | check (test 6); turn on edge or add a rib | 2.6 to 0.16 mm |
| tension springs on the rail | 25 to 60 % rise depending on the anchor | anchor 20 to 25 mm from the axle, adjusting screw | 20 to 25 % rise, 2 g per quarter turn |

What the repair does not change is the floor of the force. It is in the hole and the pressure: repairing the v5 or building idea 1 gives the same 177 g for a hole of 300 mm² at a 3 kPa peak. What differs is what is added to it: + 10 to 15 % and 0.1 to 0.25 mm of float for the repaired v5, + 2 to 4 % and 0.05 mm for idea 1.

Table: Criteria to decide, measured on the repaired v5 (10 grave keys, 5 returns, 5 high). {#tab:decision}
| criterion | test | threshold to keep the v5 | expected repaired v5 | idea 1 |
|---|---|---|---|---|
| force at mid-stroke | 4 | floor + 15 % (177 to 204 g for 300 mm²) | floor + 10 to 15 % | floor + 2 to 4 % |
| key / return equality | 4 | difference 10 g or less | 5 to 15 g | 2 to 5 g |
| hysteresis | 4 | 25 g or less | 15 to 30 g | 5 to 10 g |
| return at the 3 kPa push | 4 and 10 | all keys return, 8 notes/s | tight if return < 40 g | same floor |
| dead travel | 5 | 0.2 mm or less | 0.1 to 0.25 mm | under 0.1 mm |
| side float | 5 | 0.3 mm or less | 0.1 to 0.2 mm | 0.2 mm |
| noise | 7 | no squeak, no click audible at 50 cm | clicks possible at rod ends | silent with a felted comb |
| after 10 000 presses | 9 | force + 10 %, clearance + 0.05 mm at most | ASA with brass: holds | holds |
| 2 h at 50 °C | 8 | button height drift under 0.3 mm | ASA good, PETG limit, PLA no | same materials |
| working time | estimate | repair a third of idea 1 or less | 3 to 6 days | 10 to 20 days |

Decision rule: if two criteria or more remain out after the repair (most likely hysteresis, dead travel and noise), build idea 1. If everything passes except the working time, keep the v5 as the instrument that validates the hole, the pressure and the springs (all of that knowledge carries over to idea 1), and build idea 1 afterwards, losing nothing of the two months.

> To be completed (Ewen): the results of tests 1, 2, 4 and 5 on the v5 and on the Maugein, in the decision table, and the choice that follows.
