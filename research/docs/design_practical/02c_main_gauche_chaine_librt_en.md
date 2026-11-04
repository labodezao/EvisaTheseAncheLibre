### What the real Lib RT linkage changed (October and November 2026)

The opening chapter reasons on a simple rocker lever and concludes "$r$ at most 1". The mechanism as drawn has two stages: the button pushes a rod, the rod pulls a link, the link turns the lever $r$ that lifts the pallet. Each stage has its own arms, and the six chains (A1 to A3, B1 to B3) do not have the same ones. The lift-to-travel ratio is therefore not one choice: it is computed chain by chain. Everything here comes from CAD dimensions and a calculation. Nothing has yet been measured on a part.

**The model.** XY plane, rigid parts, rotations about Z axes. The piston rises by the travel $d$ = 5 mm; the rod turns until its contact point has risen by $d$; the link keeps its length; from that the angle of the lever $r$ follows, and the lift at the centre of the pallet. The exact ratio is $r$ = lift / $d$. The force at the finger is taken as 177 g × $r$, the 177 g coming from the opening calculation (300 mm² hole, 3 kPa peak, $r$ = 1, mid-stroke). The model ignores clearances, bending, friction, sliding at the contact and offsets along Z. The link between A and the second hole of $r$ is an assumption. The travel is not dimensioned in the CAD.

Table: Exact lift-to-travel ratio on the six chains, before correction and for each proposal (computed from the CAD survey, travel 5 mm except P2 and P3) {#tab:chaines-librt}

| Case | Ratio min / median / max | Lift min / median / max (mm) | Force min / median / max (g) |
|---|---|---|---|
| Before | 0.629 / 1.063 / 1.289 | 3.15 / 5.31 / 6.44 | 111 / 188 / 228 |
| P1: holes of $r$ or attachments moved | 1.050 everywhere | 5.25 | 186 |
| P2: travel stop per row | 0.635 / 1.062 / 1.297 | 5.06 / 5.07 / 5.12 | 112 / 188 / 230 |
| P3: travel 6.5 on A1 and B1, rods moved | 0.632 / 1.036 / 1.140 | 4.11 / 5.18 / 5.70 | 112 / 183 / 202 |
| P4: rods only, ligament at least 3 mm | 0.629 / 1.050 / 1.050 | 3.15 / 5.25 / 5.25 | 111 / 186 / 186 |
| P5: rods or levers, ligament at least 3 mm | 1.050 everywhere | 5.25 | 186 |
| P5 retained: hole on the axis, A1 undecided | 0.629 / 1.050 / 1.051 | 3.15 / 5.25 / 5.25 | 111 / 186 / 186 |

**What the calculation teaches.** Before correction, the ratio runs from 0.63 to 1.29: twice as much from one chain to another, hence twice the force under the finger for the same gesture. Equalising the lift with a stop (P2) settles nothing: the lift becomes equal, the force stays between 112 and 230 g, because it is the ratio that sets the force. The small-angle formula departs from the exact calculation by 6 % on B2 (1.213 against 1.140): the exact ratio is the one to quote.

**Why 1.05.** The range 1 to 1.1 comes from the opening calculation (travel 5 mm, lift 5 to 5.5 mm). The audit of 26/10/2026 proposes to equalise within that range; 1.05 is its middle, 5.25 mm of lift. The decision of 26/10: P5 validated, hole kept on the axis of the mechanism, the whole rod may be shifted. This 1.05 replaces the "$r$ at most 1" of the opening chapter for the Lib RT, and costs 186 g instead of 177 g.

> To be confirmed. A1 stays at 0.629, undecided. The 177 g base assumes a 300 mm² hole; the audit of 26/10 also reasons on the 15 × 25 mm hole of table 017: the force has to be redone with the hole of each chain. Lift and force are to be measured with a dial gauge and a spring scale on the first part. Data and calculations: `research/data/librt_leviers_20261026/`.
