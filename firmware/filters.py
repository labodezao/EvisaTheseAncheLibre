# Filtrage capteurs : médiane glissante (rejette les pics) suivie d'un
# passe-bas exponentiel (lisse le bruit). C'est le remède principal à
# l'« instabilité » d'affichage : les capteurs bruts sautillent, ces deux
# étages donnent une valeur stable sans traîner.


class Filtered:
    def __init__(self, n=5, alpha=0.25, init=0.0):
        self.n = n
        self.alpha = alpha
        self.buf = []
        self.value = init
        self._primed = False

    def update(self, x):
        if x is None:
            return self.value
        b = self.buf
        b.append(x)
        if len(b) > self.n:
            b.pop(0)
        med = sorted(b)[len(b) // 2]
        if not self._primed:
            self.value = med
            self._primed = True
        else:
            self.value += self.alpha * (med - self.value)
        return self.value
