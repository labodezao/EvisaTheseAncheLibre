# Right-hand keyboard

## A lever, a spring and a door

Take one key of the right hand out of an instrument and look at it. It is a lever turning on an axle shared with all the others. At one end, a button that the finger presses. At the other, a pallet, a small board faced with leather, lying on a hole of the soundboard. Between the two, a spring that keeps the pallet down when nobody plays. That is all. Three pieces and an axle, repeated thirty-three times on the instruments of the training courses, and almost everything a player feels under the right hand comes from the way these three pieces share one job: to keep a door shut against the wind, and to open it at once when asked.

In the workshop of Ewen the keys are cut on the numerical milling machine and the levers are bent and drilled by hand, the longest single task of the whole instrument (twelve hours for one right hand in the process sheets of 2026, an estimate). The trainee threads them on the axle in order, greases it, adds spacers where needed, sets every spring to 90 grams on a jig, glues the pallets with their jig and checks them against a lamp, then sets the buttons of a row at the same height with a rule. Each of these gestures has a reason in the physics, and this chapter gives it.

### The door against the wind

A pallet closed on its hole carries the pressure of the bellows on its whole area: a force $\Delta p\,A$. On an accordion the pallet sits on the outer face of the soundboard, so the two directions of the bellows do opposite things. On the push, the air inside is above the atmosphere and it lifts the pallet: the spring must hold it down. On the draw, the outside air presses the pallet onto its seat: the finger pays that force when it opens the note. The chapter on the left-hand mechanism follows the second burden in detail; the right hand meets the same two, only smaller, because its holes are smaller.

How strong must the spring be? Strong enough that no pallet lifts on the strongest push. The workshop criterion, a proposal still to be calibrated on real instruments, is that no pallet lifts below 1.5 times the highest playing pressure. With a playing pressure of 3 kPa at most, the force at the pallet must be

$$F \ge 1.5\,p_{\max}\,A = 4500\,\mathrm{Pa}\times A$$

which, written in the units of the bench, is a rule worth remembering: about half a gram at the pallet for every square millimetre of hole (0.46 g per mm² exactly, for 3 kPa). @tab:rh-spring gives it for a few holes.

Table: The three pallet holes of Ewen's instruments: useful lift, pressure at which a pallet held by 90 g lifts, and the force that holds it up to 1.5 times 3 kPa (force at the pallet; outils_atelier.py ressort and levee). {#tab:rh-spring}
| hole (mm) | area (mm²) | useful lift A/P (mm) | 90 g lifts at (Pa) | force for 4.5 kPa (g) |
|---|---|---|---|---|
| 8 × 12 | 96 | 2.4 | 9 200 | 44 |
| 15 × 15 | 225 | 3.75 | 3 900 | 103 |
| 20 × 15 | 300 | 4.3 | 2 900 | 138 |

The table holds a small surprise. The 90 grams of the workshop were never computed; they were found by the hand, as the force that makes a button feel right, and they are the same for every key. The air does not see it that way. On the small hole, 8 by 12 mm, 90 g hold the pallet shut up to 9.2 kPa, twice what the criterion asks: the spring there is set by the finger, not by the wind. On the 15 by 15 mm hole the same 90 g hold to 3.9 kPa, a little short of the 4.5 kPa of the criterion. On the 20 by 15 mm hole they hold only to 2.9 kPa, below the strongest playing pressure itself. One force for all holes is either too much for the small ones or too little for the large ones; the physics asks for a spring that follows the hole, about half a gram per square millimetre. The booklet of the training course already knows the consequence: a spring set weaker than the others gives a soft button, and its pallet may lift at the fortissimo. A note that sounds faintly by itself when the player pushes hard is very often that.

On the draw, the hole costs the finger $\Delta p\,A$ at the moment of opening, added to the spring: at 2 and 3 kPa, 20 and 29 g for the 8 by 12 mm hole, 46 and 69 g for the 15 by 15, 61 and 92 g for the 20 by 15. A button of 90 g on the push becomes one of 110 to 180 g at the very start of a strong draw, and the step disappears as soon as the pallet has lifted and the pressure has run through the reed. Players feel it, and rarely know why.

> To be completed (Ewen): where exactly the 90 g are read on the jig, at the button or at the pallet, and the two arms of the right-hand lever (axle to button, axle to pallet). If the arms are unequal, the force at the pallet is the force at the button times their ratio, and @tab:rh-spring must be read with it. And which of the three holes is used where (right hand, basses, chords), model by model. If the 20 by 15 mm pallets are held by a spring of 90 g at equal arms, do they whisper on a strong push?

### How far to lift

How far must the pallet rise? Not as far as one might think. The air does not go through the pallet; it leaves sideways, through the thin slit that opens between the edge of the hole and the leather. That slit runs all round the hole like a curtain hung from the pallet: its height is the lift $h$, its length is the perimeter $P$ of the hole, and its area is $P\,h$. While the curtain is smaller than the hole, it throttles the air, and lifting more helps. When the curtain equals the hole, at

$$h = A/P$$

the hole itself becomes the narrowest passage, and lifting further gives no more air (@fig:lift). For the 8 by 12 mm hole, $A$ = 96 mm² and $P$ = 40 mm: 2.4 mm. For 15 by 15 mm, 3.75 mm; for 20 by 15 mm, 4.3 mm. For a round hole of diameter $d$ it is simply $d/4$. The model of the thesis guessed 4 mm for every pallet: two thirds more than the small hole needs.

![The useful lift of a pallet. (a) The air leaves through the curtain that runs round the hole, perimeter times lift. (b) The air passage is the smaller of the curtain and the hole; it stops growing at the useful lift A/P: 2.4 mm for the 8 by 12 mm hole, 3.75 mm for 15 by 15 mm, 4.3 mm for 20 by 15 mm.](figures/pratique_levee_en.png){#fig:lift}

Every millimetre above the useful lift is travel of the button paid for nothing: a longer stroke of the finger, a slower repetition, and on a short lever more angle and more rubbing. A little margin is still wise, 10 to 20 per cent, because the leather is soft and the curtain is not a perfect slit. A useful design rule follows: draw the hole first, compute $A/P$, add a fifth, and that is the lift; the button travel is the lift times the ratio of the arms.

### What the speed of the key does

A key is not only open or shut; it opens in a time, and the note answers to that time. The simulations of the thesis let the pressure under the reed rise linearly in 20 ms, a hypothesis with no measurement behind it. A slow key gives the tongue a slow rise and a soft attack, a fast key a step. The response time of the note, from the opening to the steady sound, is already measured by the analysis chain of the research bench; what is missing is the position of the key against time next to it.

There is a subtler point, and it is a prediction of the two-reed network of the thesis. The mass of air of the road above the tongue, hole and pallet together, takes part in the start of the note: with that mass divided by ten the tongue does not start, multiplied by three it starts less well, and in between there is an optimum. A pallet barely open is a long thin passage and a large mass of air; a pallet wide open, a small one. If the prediction holds, the depth to which the player presses the key changes the ease of the start, and not only the loudness. Experiment E2 of the thesis is designed to see it: the starting pressure of one tongue, read on the U-tube, for five lifts of its pallet set with shims.

> To be completed (Ewen): the force and travel of one key against time, with a small load cell and a magnetic angle sensor on the bench; and experiment E2. Is there an optimum lift for the start, as the model says, and where is it compared with $A/P$?

### Two keys that do more

Two devices of Ewen's ask more of a key, and the physics above says what each one costs.

The first holds a note open the way the button of a ballpoint pen holds its tip out: one press to engage, one to release, so that a drone goes on sounding while the fingers are free. A latched pallet is a constant opening, and the tongue behind it depends on one thing only, the pressure of the bellows, which it shares with every other note being played. The bellows behaves more like a source of flow with an internal resistance than like a source of pressure (the bellows part of this book comes back to it): at a constant speed of the bellows, opening one more note makes the pressure fall. A drone therefore costs pressure for the melody, its own flow times the resistance of the source. And a latched note on a plate with two tongues sounds one tongue on the push and the other on the draw; on Ewen's own instrument the tuner found 15 to 25 cents between push and draw on the same notes. A drone that must stay in tune through the reversal asks for the two tongues of its plate to be tuned together more carefully than the melody does.

The second is a key with extra travel: pressed past the bottom of its ordinary stroke, it bends the note. What can the extra travel act on? Not the pressure, which belongs to the arm. It can close the pallet partly again, or open a second small passage, which changes the mass of air above the tongue; the pitch effect of that is not known and may be below what the ear notices. Or it can open a cell beside the chamber and change its volume. The thesis shows that the chamber is a strong lever only when its resonance is close to the note, within a ratio of about 1.1, and that such a chamber is hard to blow (1322 Pa of threshold against 208 Pa at a ratio of 1.3, for the same blade, in the model). A bend at the end of the stroke is therefore a trade between the depth of the bend and the ease of the note.

> To be completed (Ewen): the two mechanisms as you see them, and one measurement before building the second: reduce the volume of one chamber with modelling clay in two or three steps and read the pitch of its tongue with the tuner at a fixed pressure. If the pitch moves by less than a few cents, the chamber is not the lever for that note, and the pallet is the one to try.

## Building and adjusting the right hand

Each step of the process sheet has a reason. Here they are in the order of the training course, with the reason next to the gesture.

**Springs at 90 g, on the jig.** The jig puts every lever in the same position, so that the 90 g mean the same preload for all. The spring decides two things at once, the feel of the button and the pressure at which the pallet lifts (@tab:rh-spring); a spring set "about right" gives a button softer than its neighbours and a pallet that may whisper at the fortissimo. Check: each spring reads 90 g on the jig.

**Keys on the axle, greased, with spacers where needed.** A key must turn freely and must not slide sideways. Free turning keeps the button light and the return sure; sideways float lets the pallet land off-centre on its hole. The grease turns a dry rub into a lubricated one, and a lever turning on an axle loses far less to friction than a rod sliding in a guide (the left-hand chapter puts numbers on that difference). Check: each key turns freely, with no play sideways.

> To be completed (Ewen): your process sheet asks "spacers of 6.33 or 5.833 mm if necessary: when is it necessary?" What do you see that tells you a spacer is needed, and which one do you choose?

**Pallets with their jig, glued on the leather side, checked against a lamp.** A pallet off its centre leaves a crescent of the hole uncovered: a leak at every note, and the hole seen against the lamp shows it at once. The silicone foam under the pallets keeps them quiet when they land. Check: each pallet is centred and shuts with no light through.

**Buttons of a row at the same height, travel regular, nothing rubbing.** The height of a button is the start of its stroke; a row of buttons at the same height is a row of notes that open at the same depth of the finger. Check with a rule laid along the row, then press each button and listen.

## At the repair bench

What a player brings, what it usually means, and how to check it.

**A note that sounds by itself, faintly, when pushing hard.** Its pallet lifts below the playing pressure: a spring weaker than the rule of @tab:rh-spring, a leather compressed or hardened, or a pallet that no longer sits flat. Check: the spring on the gram gauge against its neighbours; the pallet against the lamp. A pallet that lets light through leaks at every pressure; one that is dark but lifts on the push has a weak spring.

**A heavy button at the start of a draw, light on the push.** This is the physics of the door, not a fault: the pressure clamps the pallet on the draw. It becomes a fault only if one button is much heavier than its neighbours with the same hole, which points to friction on the axle or a lever touching its neighbour.

**A button that stays down, or comes back slowly.** Friction (dry axle, swollen wood, a lever rubbing on the next one or on the grille), or a spring unhooked. Check: the key alone, spring removed, must fall back by its own weight when the instrument is turned over; if it does not, the friction is the culprit, not the spring.

**Uneven buttons, or a clicking key.** Heights lost by a moved stop or a crushed felt; a click is a landing without foam or felt. Check with the rule, and replace the felt or foam.

> To be completed (Ewen): your own list of what players bring for the right hand, in the order of how often you meet it, so that this list follows the real bench and not the theory.
