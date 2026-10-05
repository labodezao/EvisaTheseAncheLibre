# Reeds at the bench

## A spring that sings

A reed is a tongue of spring steel riveted at its heel onto a plate, over a slot a few hundredths of a millimetre wider than itself. On the other face of the plate, a second tongue lies over a second slot, the other way round, and each slot has a valve, a flap of leather or plastic, on the side from which its air does not come. The thesis spends a whole part on what makes such a tongue sound. This chapter asks what the maker and the repairer do with it: how to tune it, how to set it, what to measure, and what to do when it will not speak.

### Where to scrape

A tongue is a spring with a mass, and its frequency goes as the square root of stiffness over mass. A file or a scraper can take away either, depending on where it bites. Near the tip, the steel moves the most and bends the least: scraping there removes mass where it counts and stiffness where it does not, and the note rises. Near the heel, the steel bends the most and moves the least: scraping there removes stiffness, and the note falls. Hence the rule printed on the strobe of the tuner of this work: too high, scrape towards the heel; too low, scrape towards the tip.

How sensitive is it? For a blade of even thickness, the frequency is proportional to the thickness: thin the whole tongue by one per cent and the note falls by one per cent, 17 cents, a sixth of a semitone. A local scrape does far less than an even thinning, which is precisely why scraping can be done at all, a stroke at a time with the tuner watching. The same proportion explains why handbook values of the steel will not do for tuning: the stiffness of spring steel varies by about 3 per cent with its grade, which is 26 cents on the note. The thesis gives the way to measure it on a strip of the same steel.

### At which pressure to tune

Every version of the models of the thesis says that the note of a free reed goes down when the player pushes harder. A reed tuned at one pressure is therefore slightly out of tune at the others, and the question "at which pressure do you tune?" is not a detail. On Ewen's own instrument the tuner found differences of 15 to 25 cents between push and draw on the same notes, which is the other face of the same question: the two tongues of a plate are two different blades, tuned separately, and they must agree at the pressure the music uses.

> To be completed (Ewen): at which pressure, or with which bellows gesture, you tune; whether it is the same for bass and treble; and your tolerance in cents for a training-course instrument.

### Two voices and their beat

A note in the musette tuning is two or three tongues, slightly detuned, whose beat makes the tremolo. The beat is the difference of their frequencies, and @tab:beats gives it at the A of 440 Hz for the detunings a tuner uses.

Table: Beat of two voices around A 440 Hz (outils_atelier.py battement). {#tab:beats}
| detuning (cents) | beat (Hz) | beats per minute |
|---|---|---|
| 2 | 0.51 | 31 |
| 3 | 0.76 | 46 |
| 5 | 1.27 | 76 |
| 10 | 2.55 | 153 |
| 15 | 3.83 | 230 |
| 20 | 5.11 | 307 |

The thesis adds a warning that the tuner should know. Two tongues that share the air of one pallet are coupled, and the network model predicts that close to the unison they pull each other into step: below about 2 cents, at A4 and 1000 Pa, the two voices lock onto one frequency and the beat disappears; at 5 cents the beat is still 12 per cent slower than the difference of the blades; at 20 cents it is free. Near the lock the beat heard is not the difference of the blades but $\sqrt{\Delta^2-\Delta_L^2}$, the law of two coupled oscillators. If the model is right, a voice tuned at 2 cents of its partner will not beat at all once both are free, and a slow tremolo must be tuned a little wider than its target. Experiment E3 of the thesis tests it with the tuner: tune one tongue with the other blocked by a strip of paper, free it, and read whether the beat survives.

> To be completed (Ewen): experiment E3 on one musette note: the beat read with the other voice blocked and free, at 1, 2, 3 and 5 cents. Does the beat vanish below about 2 cents?

### The set of the tongue, and the four pressures

The tip of a tongue does not lie flat in its slot; it stands a little above it, the set or lift. The lift decides how the reed starts and how far it can be pushed. Four pressures describe it, all measurable with the bench: the pressure at which it starts, $p_{\mathrm{on}}$, the softest pianissimo one can attack; the pressure at which it chokes and falls silent although the pressure is still rising, the loudest fortissimo; and, coming back down, the pressure at which it speaks again and the one at which it goes out, $p_{\mathrm{off}}$, the softest pianissimo one can hold. Ewen's aim for a block, the widest range of play with the lowest threshold, is written in these four numbers.

The working hypothesis, from the classic work of St Hilaire and colleagues extended in this project, is that at equal geometry the starting pressure grows as the square of frequency times lift, while the choking pressure grows as stiffness times lift over area. A low lift would then start easily and choke early; a high lift would hold a fortissimo and refuse a pianissimo. Experiment E19 measures the four pressures for three reeds at three lifts, and would contradict the hypothesis if the starting pressure did not move with the lift.

> To be completed (Ewen): how you set the lift today (by eye, by gauge), and the reeds you would choose for E19, one bass, one middle, one treble.

### The valve

The valve makes the flow through a slot one-way. Without it, the air of the bellows would leak through the slot of the silent tongue of each plate, and that tongue, if close to its threshold, would whisper: a ghost note. The models of the thesis take the valve as perfect; a real one has a mass, leaks a little, and slaps against the plate at each reversal of the bellows, which is where the tuner of this work sees the reversal. The thesis has a protocol for comparing leather and plastic valves; at the bench, the valve is a part that wears, curls, sticks or comes unglued.

> To be completed (Ewen): your valves are put on before the course or by the trainee? With which glue, and how?

## Tools at the bench

**The tuner of this work** shows each reed at once in the manner of a strobe and says what to do with the tongue; four lights come on as the reed approaches its target, at 5, 1, 0.3 and 0.1 cent. The register mode measures two to five voices together without blocking any, shows the beat of each detuned voice, and a list of beats, the target tremolo, can be copied from one instrument to another. Push and draw are measured and kept apart.

**The U-tube** gives the pressure at which a reed is tuned or its thresholds read; **the gasometer** gives the air a reed consumes; **feeler gauges and a lamp** give the lift and the gaps; **a phone filming at 240 frames per second** shows a bass tongue swing, and whether its tip leaves the slot.

**A plucked tongue** says a great deal before any air: pluck it with a fingernail, record it with a phone, and the frequency and the damping come out of the recording (pince.py in the thesis). A tongue that rings much shorter than its neighbours has a loose rivet, a crack, or something touching it.

## At the repair bench

**A reed that does not speak.** In order of likelihood: it touches the slot or the cell (look against a light), its lift is lost (the tip lies in the slot), the valve of its partner is missing so its air leaks away, the wax around its plate leaks, or dirt sits in the slot. A thin feeler passed round the tongue finds a grain.

**A reed that speaks late or only loud.** Its threshold is high: lift too great, or a leak that takes its pressure (the leak part of this book). Compare its starting pressure with a neighbour on the U-tube.

**A buzz or a rattle.** A tongue grazing, a rivet loose (the pluck rings short), a valve slapping or half unglued.

**A note out of tune after years.** Retune it, but look first: rust adds mass where it forms, and a pitted tongue may crack later. A cracked or broken tongue is replaced, not tuned.

> To be completed (Ewen): your list of reed repairs, from the most frequent, and the supplier delay for a replacement reed.
