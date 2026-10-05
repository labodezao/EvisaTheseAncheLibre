# Les anches à l'établi

## Un ressort qui chante

Une anche est une languette d'acier à ressort rivée par son talon sur une plaque, au-dessus d'une fente à peine plus large qu'elle de quelques centièmes de millimètre. Sur l'autre face de la plaque, une seconde languette couvre une seconde fente, dans l'autre sens, et chaque fente a sa valve, un rabat de peau ou de plastique, du côté d'où ne vient pas son air. La thèse consacre toute une partie à ce qui fait sonner une telle languette. Ce chapitre demande ce qu'en font le facteur et le réparateur : comment l'accorder, comment la régler, quoi mesurer, et que faire quand elle ne parle pas.

### Où gratter

Une languette est un ressort avec une masse, et sa fréquence va comme la racine de la raideur sur la masse. Une lime ou un grattoir peut ôter l'une ou l'autre, selon l'endroit où il mord. Près du bout, l'acier bouge le plus et plie le moins : gratter là enlève de la masse où elle compte et de la raideur où elle ne compte pas, et la note monte. Près du talon, l'acier plie le plus et bouge le moins : gratter là enlève de la raideur, et la note descend. D'où la règle imprimée sur le stroboscope de l'accordeur de ce travail : trop haut, gratter vers le talon ; trop bas, gratter vers le bout.

Quelle sensibilité ? Pour une lame d'épaisseur régulière, la fréquence est proportionnelle à l'épaisseur : amincir toute la languette d'un pour cent fait baisser la note d'un pour cent, 17 cents, un sixième de demi-ton. Un grattage local fait bien moins qu'un amincissement régulier, et c'est justement pourquoi on peut gratter, un coup à la fois, sous l'œil de l'accordeur. La même proportion explique pourquoi les valeurs de manuel de l'acier ne suffisent pas pour accorder : la raideur de l'acier à ressort varie d'environ 3 % selon la nuance, soit 26 cents sur la note. La thèse donne la façon de la mesurer sur une bande du même acier.

### À quelle pression accorder

Toutes les versions des modèles de la thèse disent que la note d'une anche libre baisse quand le musicien pousse plus fort. Une anche accordée à une pression est donc un peu fausse aux autres, et la question « à quelle pression accordes-tu ? » n'est pas un détail. Sur l'instrument d'Ewen, l'accordeur a trouvé 15 à 25 cents d'écart entre poussé et tiré sur les mêmes notes, ce qui est l'autre face de la même question : les deux languettes d'une plaque sont deux lames différentes, accordées séparément, et elles doivent s'accorder à la pression dont la musique se sert.

> À compléter (Ewen) : à quelle pression, ou avec quel geste de soufflet, tu accordes ; si c'est la même pour les basses et les aigus ; et ta tolérance en cents pour un instrument de stage.

### Deux voix et leur battement

Une note accordée en musette, ce sont deux ou trois languettes légèrement désaccordées, dont le battement fait le trémolo. Le battement est la différence de leurs fréquences, et le tableau @tab:fr-battements le donne autour du la 440 Hz pour les écarts dont se sert un accordeur.

Table: Battement de deux voix autour du la 440 Hz (outils_atelier.py battement). {#tab:fr-battements}
| écart (cents) | battement (Hz) | battements par minute |
|---|---|---|
| 2 | 0,51 | 31 |
| 3 | 0,76 | 46 |
| 5 | 1,27 | 76 |
| 10 | 2,55 | 153 |
| 15 | 3,83 | 230 |
| 20 | 5,11 | 307 |

La thèse ajoute un avertissement que l'accordeur devrait connaître. Deux languettes qui partagent l'air d'une soupape sont couplées, et le modèle de réseau prédit que près de l'unisson elles s'entraînent l'une l'autre : sous environ 2 cents, au la 4 et à 1000 Pa, les deux voix se verrouillent sur une seule fréquence et le battement disparaît ; à 5 cents, le battement est encore 12 % plus lent que la différence des lames ; à 20 cents, il est libre. Près du verrouillage, le battement entendu n'est pas la différence des lames mais $\sqrt{\Delta^2-\Delta_L^2}$, la loi de deux oscillateurs couplés. Si le modèle a raison, une voix accordée à 2 cents de sa partenaire ne battra plus du tout une fois les deux libres, et un trémolo lent doit être accordé un peu plus large que sa cible. L'expérience E3 de la thèse le teste à l'accordeur : accorder une languette avec l'autre bloquée par une bande de papier, la libérer, et lire si le battement survit.

> À compléter (Ewen) : l'expérience E3 sur une note musette : le battement lu avec l'autre voix bloquée puis libre, à 1, 2, 3 et 5 cents. Le battement disparaît-il sous environ 2 cents ?

### La levée de la languette, et les quatre pressions

Le bout d'une languette ne repose pas à plat dans sa fente ; il se tient un peu au-dessus, c'est la levée. La levée décide de la façon dont l'anche démarre et de jusqu'où on peut la pousser. Quatre pressions la décrivent, toutes mesurables au banc : la pression à laquelle elle démarre, $p_{\mathrm{on}}$, le pianissimo le plus doux qu'on puisse attaquer ; la pression à laquelle elle se plaque et se tait alors que la pression monte encore, le fortissimo le plus fort ; et, en redescendant, la pression à laquelle elle repart et celle à laquelle elle s'éteint, $p_{\mathrm{off}}$, le pianissimo le plus doux qu'on puisse tenir. Le but d'Ewen pour un sommier, la plus grande plage de jeu avec le seuil le plus bas, s'écrit dans ces quatre nombres.

L'hypothèse de travail, tirée des travaux classiques de St Hilaire et de ses collègues et prolongée dans ce projet, est qu'à géométrie égale la pression de démarrage croît comme le carré de la fréquence fois la levée, tandis que la pression de plaquage croît comme la raideur fois la levée sur la surface. Une levée basse démarrerait alors facilement et se plaquerait tôt ; une levée haute tiendrait un fortissimo et refuserait un pianissimo. L'expérience E19 mesure les quatre pressions pour trois anches à trois levées, et contredirait l'hypothèse si la pression de démarrage ne bougeait pas avec la levée.

> À compléter (Ewen) : comment tu règles la levée aujourd'hui (à l'œil, à la cale), et les anches que tu choisirais pour E19, une grave, une médium, une aiguë.

### La valve

La valve rend le passage d'air par une fente à sens unique. Sans elle, l'air du soufflet fuirait par la fente de la languette muette de chaque plaque, et cette languette, si elle est proche de son seuil, chuchoterait : une note fantôme. Les modèles de la thèse prennent la valve pour parfaite ; une vraie valve a une masse, fuit un peu, et claque contre la plaque à chaque changement de sens du soufflet, là où l'accordeur de ce travail voit le changement de sens. La thèse a un protocole pour comparer valves de peau et de plastique ; à l'établi, la valve est une pièce qui s'use, se recroqueville, colle ou se décolle.

> À compléter (Ewen) : tes valves sont-elles posées avant le stage ou par le stagiaire ? Avec quelle colle, et comment ?

## Les outils de l'établi

**L'accordeur de ce travail** montre chaque anche à la fois à la façon d'un stroboscope et dit quoi faire de la languette ; quatre voyants s'allument quand l'anche approche de sa cible, à 5, 1, 0,3 et 0,1 cent. Le mode registre mesure deux à cinq voix ensemble sans en bloquer aucune, montre le battement de chaque voix désaccordée, et une liste de battements, le trémolo cible, peut se copier d'un instrument à un autre. Poussé et tiré sont mesurés et gardés à part.

**Le tube en U** donne la pression à laquelle une anche est accordée ou ses seuils lus ; **le gazomètre** donne l'air que consomme une anche ; **les cales d'épaisseur et une lampe** donnent la levée et les jeux ; **un téléphone filmant à 240 images par seconde** montre une languette grave battre, et si son bout sort de la fente.

**Une languette pincée** en dit long avant tout souffle : pincez-la d'un ongle, enregistrez-la au téléphone, et la fréquence et l'amortissement sortent de l'enregistrement (pince.py dans la thèse). Une languette qui sonne bien plus court que ses voisines a un rivet desserré, une fêlure, ou quelque chose qui la touche.

## À l'établi du réparateur

**Une anche qui ne parle pas.** Par ordre de probabilité : elle touche la fente ou la case (regarder contre une lumière), sa levée est perdue (le bout est couché dans la fente), la valve de sa partenaire manque et son air fuit, la cire autour de sa plaque fuit, ou une saleté est dans la fente. Une cale fine passée autour de la languette trouve un grain.

**Une anche qui parle tard, ou seulement fort.** Son seuil est haut : levée trop grande, ou une fuite qui lui prend sa pression (la partie fuites de ce livre). Comparer sa pression de démarrage avec une voisine au tube en U.

**Un grésillement ou un cliquetis.** Une languette qui frôle, un rivet desserré (le pincement sonne court), une valve qui claque ou à moitié décollée.

**Une note fausse après des années.** La réaccorder, mais regarder d'abord : la rouille ajoute de la masse là où elle se forme, et une languette piquée peut se fêler plus tard. Une languette fêlée ou cassée se remplace, elle ne s'accorde pas.

> À compléter (Ewen) : ta liste des réparations d'anches, de la plus fréquente, et le délai du fournisseur pour une anche de rechange.
