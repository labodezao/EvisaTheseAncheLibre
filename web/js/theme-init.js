// Applique le thème mémorisé avant le premier rendu (évite un flash sombre
// puis clair). Thème clair par défaut si rien n'est encore mémorisé ; le
// bouton du bandeau le change et le mémorise (app.js, clé aal.theme).
// Fichier à part (et non <script> en ligne) : la CSP de index.html interdit
// les scripts en ligne.
document.documentElement.setAttribute('data-theme', localStorage.getItem('aal.theme') || 'light');
