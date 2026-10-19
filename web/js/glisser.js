// Glisser-déposer aux événements pointer (souris, doigt, stylet).
// activerGlisser(racine, { source, cible, onDepose(src, dst), seuil })
//  - `source` : sélecteur des éléments qu'on peut saisir (data-uid) ;
//  - `cible` : sélecteur des éléments où l'on peut lâcher ;
//  - pendant le glisser, la cible survolée porte la classe `drop-cible` et
//    l'élément saisi `glisse` ; un fantôme suit le pointeur.
// Un simple clic (déplacement sous le seuil) reste un clic. Les éléments
// saisissables doivent avoir `touch-action: none` (CSS) pour que le doigt
// glisse au lieu de faire défiler la page.
export function activerGlisser(racine, { source, cible, onDepose, seuil = 6, libelle = (el) => el.textContent.trim().slice(0, 30) }) {
  for (const el of racine.querySelectorAll(source)) {
    el.addEventListener('pointerdown', (e) => {
      if (e.button != null && e.button > 0) return;
      const x0 = e.clientX, y0 = e.clientY;
      let actif = false, fantome = null, survol = null;
      const dessus = (x, y) => {
        if (fantome) fantome.style.display = 'none';
        const t = document.elementFromPoint(x, y)?.closest(cible) ?? null;
        if (fantome) fantome.style.display = '';
        return t;
      };
      const marquer = (t) => {
        if (t === survol) return;
        survol?.classList.remove('drop-cible');
        survol = t && t !== el ? t : null;
        survol?.classList.add('drop-cible');
      };
      const bouge = (ev) => {
        if (!actif) {
          if (Math.hypot(ev.clientX - x0, ev.clientY - y0) < seuil) return;
          actif = true;
          el.classList.add('glisse');
          fantome = document.createElement('div');
          fantome.className = 'glisse-fantome';
          fantome.textContent = libelle(el);
          document.body.appendChild(fantome);
          try { el.setPointerCapture(e.pointerId); } catch { /* pas critique */ }
        }
        fantome.style.left = `${ev.clientX + 10}px`;
        fantome.style.top = `${ev.clientY + 10}px`;
        marquer(dessus(ev.clientX, ev.clientY));
        ev.preventDefault();
      };
      const fin = (ev) => {
        el.removeEventListener('pointermove', bouge);
        el.removeEventListener('pointerup', fin);
        el.removeEventListener('pointercancel', fin);
        if (!actif) return;
        const dst = ev.type === 'pointerup' ? dessus(ev.clientX, ev.clientY) : null;
        survol?.classList.remove('drop-cible');
        el.classList.remove('glisse');
        fantome?.remove();
        // le clic qui suit un vrai glisser ne doit pas sélectionner la ligne
        el.addEventListener('click', (c) => c.stopImmediatePropagation(), { capture: true, once: true });
        if (dst && dst !== el) onDepose(el, dst);
      };
      el.addEventListener('pointermove', bouge);
      el.addEventListener('pointerup', fin);
      el.addEventListener('pointercancel', fin);
    });
  }
}
