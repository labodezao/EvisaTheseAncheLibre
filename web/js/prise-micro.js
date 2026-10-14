// Le micro et la prise de son, côté page (Ewen, 14/10/2026) : quel micro est
// utilisé, quel est le meilleur des micros branchés, ce que dit chaque alerte du
// contrôle de la prise (dsp/prise.js) et le geste exact à faire. Pur, sans DOM,
// commun à la nouvelle interface (ui/) et à l'ancienne page (app.js) : les textes
// sont ici, en français et en anglais (`lang`), donc hors des dictionnaires de
// l'interface.

// ---- Reconnaître un micro à son nom ------------------------------------------------
// Chrome ne donne que le nom (« Microphone (USB Audio Devive) (0020:0b21) »), pas la
// marque ; on reconnaît des familles. Une interface audio connue passe devant un micro
// générique ; « Communications » (l'alias de Windows pour les appels) et les casques
// Bluetooth (mains libres : 8 ou 16 kHz, traitement vocal) passent derrière.
const BLUETOOTH = /bluetooth|hands[- ]?free|\bhfp\b|airpods|\bbuds\b|\bbt\b[ -]?(headset|audio)|wh-1000|wf-1000|jabra|plantronics|poly voyager/i;
const COMMUNICATIONS = /^\s*(communications?|communication)\b|^\s*communications?\s*-/i;
const PAR_DEFAUT = /^\s*(default|par d[ée]faut)\b/i;
const VIRTUEL = /vb-?audio|cable (input|output)|voicemeeter|virtual|virtuel|droidcam|obs\b|stereo mix|mixage st[ée]r[ée]o|steam streaming|loopback|nvidia broadcast|krisp|nahimic|asio4all|camo|iriun|epoccam/i;
const INTERFACE = /zoom|focusrite|scarlett|clarett|behringer|x[- ]?air|\bumc\d|\bumx|steinberg|\bur\d{2}\b|presonus|audient|motu|\brme\b|babyface|fireface|universal audio|apollo|tascam|\bus-\d|roland|\brode\b|\bnt-?usb|shure|\bmv\d|audio-?technica|\bat20\d\d|\bblue\b|yeti|samson|maono|irig|m-audio|maya ?44|soundcraft|allen & heath|fifine|tonor|akg|sennheiser|neumann/i;
const GENERIQUE = /usb audio|usb pnp|usb microphone|microphone array|r[ée]seau de microphones|realtek|high definition audio|conexant|\bwebcam|\bcamera|cam[ée]ra|\bhd pro|logitech|integrated|int[ée]gr[ée]/i;

export function classerMicro(label = '', deviceId = '') {
  const l = String(label);
  const id = String(deviceId);
  return {
    bluetooth: BLUETOOTH.test(l),
    communications: COMMUNICATIONS.test(l) || id === 'communications',
    parDefaut: PAR_DEFAUT.test(l) || id === 'default',
    virtuel: VIRTUEL.test(l),
    interfaceConnue: INTERFACE.test(l) && !BLUETOOTH.test(l),
    generique: GENERIQUE.test(l),
  };
}

// Note d'un micro (plus haut = meilleur). Une interface audio connue gagne ; l'alias
// « Communications » et le Bluetooth perdent ; un alias « par défaut » ne vaut pas le
// micro lui-même (il peut pointer ailleurs demain).
export function scoreMicro(label, deviceId = '') {
  const c = classerMicro(label, deviceId);
  let s = 40;
  if (c.interfaceConnue) s += 100;
  if (c.generique) s -= 15;
  if (c.virtuel) s -= 50;
  if (c.bluetooth) s -= 90;
  if (c.communications) s -= 70;
  if (c.parDefaut) s -= 10;
  return s;
}

// Un micro sert au même appareil sous deux entrées (« default », « communications » et
// l'identifiant propre) : on garde la liste telle quelle mais on retrouve le même par
// `groupId`.
export function meilleurMicro(micros) {
  const liste = (micros ?? []).filter((m) => m && m.id);
  if (liste.length < 2) return null;
  let best = null;
  for (const m of liste) {
    const s = scoreMicro(m.nom ?? m.label, m.id);
    if (!best || s > best.score) best = { ...m, score: s };
  }
  return best;
}

// Faut-il proposer un autre micro que celui qui sert ? Oui si le meilleur vaut
// nettement plus (30 points) et n'est pas le même appareil (même groupe). Rend
// { id, nom, raison } ou null. `actif` : { label, deviceId, groupId }.
export function propositionMicro(micros, actif, lang = 'fr') {
  const best = meilleurMicro(micros);
  if (!best || !actif) return null;
  if (best.id === actif.deviceId || (best.groupId && best.groupId === actif.groupId)) return null;
  const sa = scoreMicro(actif.label, actif.deviceId);
  if (best.score < sa + 30) return null;
  const c = classerMicro(best.nom ?? best.label);
  const ca = classerMicro(actif.label, actif.deviceId);
  const fr = lang !== 'en';
  let raison;
  if (ca.bluetooth) raison = fr ? 'le micro actuel est un casque Bluetooth (qualité téléphone)' : 'the current mic is a Bluetooth headset (phone quality)';
  else if (ca.communications) raison = fr ? 'le micro actuel est l\'entrée « Communications » de Windows' : 'the current mic is the Windows "Communications" input';
  else if (c.interfaceConnue) raison = fr ? 'interface audio reconnue' : 'known audio interface';
  else raison = fr ? 'meilleur choix parmi les micros branchés' : 'best of the connected mics';
  return { id: best.id, nom: best.nom ?? best.label, raison };
}

// Le micro mémorisé est-il encore là ? Rend { id, repli } : l'id à demander (null = le
// micro par défaut du système) et `repli` (l'id voulu mais absent) quand il est débranché.
export function choisirMicro(micros, memorise) {
  if (!memorise) return { id: null, repli: null };
  const trouve = (micros ?? []).some((m) => m.id === memorise);
  // Avant la permission, la liste est vide et sans noms : on tente l'id, le navigateur tranche.
  if (!micros?.length || trouve) return { id: memorise, repli: null };
  return { id: null, repli: memorise };
}

// ---- Les mots -------------------------------------------------------------------------
export function plateforme(ua = globalThis.navigator?.userAgent ?? '') {
  if (/android/i.test(ua)) return 'android';
  if (/iphone|ipad|ipod/i.test(ua)) return 'ios';
  if (/windows/i.test(ua)) return 'windows';
  if (/mac os x|macintosh/i.test(ua)) return 'mac';
  if (/linux|x11|cros/i.test(ua)) return 'linux';
  return 'autre';
}

const nombre = (n, d = 0, lang = 'fr') => (Number.isFinite(n) ? n.toLocaleString(lang === 'en' ? 'en-GB' : 'fr-FR', { minimumFractionDigits: d, maximumFractionDigits: d }) : '—');

// Ligne permanente : « ZOOM H6 · 44 100 Hz · 2 canaux ».
// `micro` : { label, settings }, `capture` : message du Worker { sampleRate, canaux }.
export function ligneMicro(micro, capture, lang = 'fr') {
  const fr = lang !== 'en';
  if (capture?.error) return fr ? 'micro refusé ou introuvable' : 'mic refused or not found';
  if (capture?.gen) return fr ? 'générateur d\'essai' : 'test generator';
  if (capture?.fichier != null) return fr ? 'enregistrement rejoué' : 'recording replay';
  if (!micro?.label && !capture?.sampleRate) return fr ? 'aucun micro lancé' : 'no mic running';
  const sr = capture?.sampleRate ?? micro?.settings?.sampleRate;
  const ch = capture?.canaux ?? micro?.settings?.channelCount;
  const parts = [micro?.label || (fr ? 'micro sans nom' : 'unnamed mic')];
  if (sr) parts.push(`${nombre(sr, 0, lang)} Hz`);
  if (ch) parts.push(fr ? (ch > 1 ? `${ch} canaux` : `${ch} canal`) : `${ch} channel${ch > 1 ? 's' : ''}`);
  return parts.join(' · ');
}

const ENTREE = (nom, os, fr) => {
  const n = nom ? `« ${nom} »` : (fr ? 'votre micro' : 'your mic');
  if (os === 'windows') return fr
    ? `Windows : Paramètres > Système > Son > Entrée > ${n} > Améliorations audio : Désactivées.`
    : `Windows: Settings > System > Sound > Input > ${n} > Audio enhancements: Off.`;
  if (os === 'mac') return fr
    ? 'macOS : Réglages Système > Son > Entrée, puis dans la barre des menus, Modes du micro : Standard (ni Isolation vocale, ni Spectre large).'
    : 'macOS: System Settings > Sound > Input, then in the menu bar Mic Mode: Standard (no Voice Isolation, no Wide Spectrum).';
  if (os === 'android' || os === 'ios') return fr
    ? 'Téléphone : branchez un micro externe ou une interface audio ; coupez la réduction de bruit du système (Paramètres > Son).'
    : 'Phone: plug in an external mic or audio interface; turn off the system noise reduction (Settings > Sound).';
  return fr
    ? 'Désactivez la réduction de bruit et le traitement vocal dans les réglages son du système.'
    : 'Turn off noise reduction and voice processing in the system sound settings.';
};

const AUTRE_MICRO = (fr) => (fr
  ? ' Ou choisissez une interface audio (Zoom, Focusrite, Scarlett…) comme micro.'
  : ' Or pick an audio interface (Zoom, Focusrite, Scarlett…) as the mic.');

// Ce que dit une alerte (code du contrôle) et le geste à faire.
//   alerte : { code, detail } ; ctx : { nom (du micro), os, lang }
// Rend { code, titre, texte, geste, court }. `court` : la mention « prise douteuse : … ».
export function consigne(alerte, ctx = {}) {
  const fr = ctx.lang !== 'en';
  const os = ctx.os ?? plateforme();
  const nom = ctx.nom ?? '';
  const d = alerte?.detail ?? {};
  switch (alerte?.code) {
    case 'gate': return {
      code: 'gate',
      titre: fr ? 'Suppresseur de bruit détecté' : 'Noise suppressor detected',
      texte: fr
        ? 'Le son contient du silence numérique entre les notes : un traitement (réduction de bruit, porte) coupe le signal. Il fausse les battements et les partiels faibles.'
        : 'The sound has digital silence between notes: processing (noise reduction, gate) cuts the signal. It distorts beats and weak partials.',
      geste: ENTREE(nom, os, fr) + AUTRE_MICRO(fr),
      court: fr ? 'suppresseur de bruit' : 'noise suppressor',
    };
    case 'pompage': return {
      code: 'pompage',
      titre: fr ? 'Gain automatique ou compresseur détecté' : 'Automatic gain or compressor detected',
      texte: fr
        ? `Le ronflement du secteur, d'amplitude constante, suit le niveau du son (écart ${nombre(d.ecart_db, 1, 'fr')} dB) : le niveau est traité. Les amplitudes relatives des partiels ne sont plus fiables.`
        : `The mains hum, constant in reality, follows the sound level (spread ${nombre(d.ecart_db, 1, 'en')} dB): the level is being processed. Relative partial amplitudes are not reliable.`,
      geste: ENTREE(nom, os, fr) + (fr ? ' Coupez aussi « Gain automatique » (AGC) dans le logiciel du micro.' : ' Also turn off "Automatic gain" (AGC) in the mic software.') + AUTRE_MICRO(fr),
      court: fr ? 'gain automatique' : 'automatic gain',
    };
    case 'trous': return {
      code: 'trous',
      titre: fr ? 'Des blocs de son ont été perdus' : 'Blocks of sound were lost',
      texte: fr
        ? `La date du flux a sauté de ${nombre(Math.abs(d.dernier_ms), 0, 'fr')} ms par rapport aux échantillons reçus, à ${nombre(d.dernier_t_s, 1, 'fr')} s du début de la prise (${d.total ?? 1} fois). Les hauteurs lues autour de cet instant sont à écarter.${d.cause === 'retard' ? ' Le calcul de l’accordeur a lui-même pris du retard à cet instant.' : ''}`
        : `The stream clock jumped by ${nombre(Math.abs(d.dernier_ms), 0, 'en')} ms against the samples received, ${nombre(d.dernier_t_s, 1, 'en')} s into the take (${d.total ?? 1} times). Pitches read around that moment should be discarded.${d.cause === 'retard' ? ' The tuner’s own processing fell behind at that moment.' : ''}`,
      geste: d.cause === 'retard' ? (fr ? 'Fermez les autres onglets et applications, branchez l’ordinateur sur secteur (mode performance), puis refaites la prise.' : 'Close other tabs and apps, plug the computer in (performance mode), then redo the take.') : fr
        ? 'Fermez les autres applications qui utilisent le son, branchez le micro directement (sans hub USB), fermez les onglets lourds, puis refaites la prise.'
        : 'Close other apps using sound, plug the mic in directly (no USB hub), close heavy tabs, then redo the take.',
      court: fr ? 'blocs perdus' : 'lost blocks',
    };
    case 'ecretage': return {
      code: 'ecretage',
      titre: fr ? 'Le micro sature' : 'The mic is clipping',
      texte: fr ? 'Des échantillons touchent le maximum : le son est écrêté, les partiels aigus sont faux.' : 'Samples hit the maximum: the sound is clipped and the high partials are wrong.',
      geste: fr
        ? 'Baissez le gain du micro (Windows : Paramètres > Système > Son > Entrée > Volume ; ou le bouton gain de l\'interface) ou éloignez le micro.'
        : 'Lower the mic gain (Windows: Settings > System > Sound > Input > Volume; or the interface gain knob) or move the mic away.',
      court: fr ? 'saturation' : 'clipping',
    };
    case 'secteur': return {
      code: 'secteur',
      titre: fr ? `Ronflement du secteur (${d.hz ?? 50} Hz) fort` : `Strong mains hum (${d.hz ?? 50} Hz)`,
      texte: fr
        ? `Une raie à ${d.hz ?? 50} Hz et ses harmoniques dépasse le fond de ${nombre(d.ratio_db, 0, 'fr')} dB${d.trop_fort ? ' et le retrait n\u2019a pas suffi : le ronflement est trop fort pour être retiré' : ''}.`
        : `A ${d.hz ?? 50} Hz line and its harmonics stand ${nombre(d.ratio_db, 0, 'en')} dB above the floor${d.trop_fort ? ' and removal was not enough: the hum is too strong to be removed' : ''}.`,
      geste: fr
        ? 'Dans cet ordre : 1) utilisez une interface audio (par exemple le Zoom H6) plutôt qu\u2019un micro USB alimenté par le bus ; 2) branchez le micro sur un autre port USB, directement sur l\u2019ordinateur (pas de hub, pas de port en façade) ; 3) éloignez les câbles secteur du micro et de son câble.'
        : 'In this order: 1) use an audio interface (for example the Zoom H6) instead of a bus-powered USB mic; 2) plug the mic into another USB port, directly on the computer (no hub, no front-panel port); 3) move mains cables away from the mic and its cable.',
      court: fr ? 'ronflement secteur' : 'mains hum',
    };
    case 'lent': return {
      code: 'lent',
      titre: fr ? 'Micro à faible fréquence d\'échantillonnage' : 'Low sample-rate mic',
      texte: fr
        ? `Le micro livre ${nombre(d.sr, 0, 'fr')} Hz (qualité téléphone, souvent Bluetooth « mains libres ») : les partiels aigus ne sont pas captés.`
        : `The mic delivers ${nombre(d.sr, 0, 'en')} Hz (phone quality, often Bluetooth hands-free): high partials are not captured.`,
      geste: (fr
        ? 'Utilisez un micro filaire (USB) ou une interface audio. '
        : 'Use a wired (USB) mic or an audio interface. ')
        + (os === 'windows' ? (fr ? 'Windows : Paramètres > Système > Son > Entrée > Format : 48 000 Hz.' : 'Windows: Settings > System > Sound > Input > Format: 48,000 Hz.') : ''),
      court: fr ? 'fréquence trop basse' : 'sample rate too low',
    };
    case 'secteurProche': return {
      code: 'secteurProche',
      titre: fr ? 'Partiel proche d\u2019une harmonique du secteur' : 'Partial close to a mains harmonic',
      texte: fr ? 'Cette note a un partiel à moins de 1 Hz d\u2019une harmonique du secteur, que le retrait du ronflement abîme : la lecture n\u2019est pas dite sûre.' : 'This note has a partial within 1 Hz of a mains harmonic, which the hum removal damages: the reading is not called reliable.',
      geste: fr ? 'Lisez la note sur un autre partiel (autre note proche) ou coupez le retrait du ronflement dans Réglages > Mesure.' : 'Read the note on another partial or turn off hum removal in Settings > Measure.',
      court: fr ? 'partiel près du secteur' : 'partial near mains',
    };
    case 'bluetooth': return {
      code: 'bluetooth',
      titre: fr ? 'Micro Bluetooth' : 'Bluetooth mic',
      texte: fr
        ? 'Un casque Bluetooth en mode « mains libres » donne un son de téléphone (8 à 16 kHz, compression de la voix) : inutilisable pour accorder.'
        : 'A Bluetooth headset in hands-free mode gives phone-quality sound (8 to 16 kHz, voice compression): unusable for tuning.',
      geste: fr
        ? 'Choisissez un micro filaire ou une interface audio dans la liste des micros.'
        : 'Pick a wired mic or an audio interface in the mic list.',
      court: fr ? 'micro Bluetooth' : 'Bluetooth mic',
    };
    default: return null;
  }
}

// Les informations du contrôle (pas des alertes) : « ronflement 50 Hz supprimé ». Une ligne discrète, aucun conseil.
export function informations(etat, ctx = {}) {
  const fr = ctx.lang !== 'en';
  return (etat?.infos ?? []).map((i) => {
    if (i.code === 'secteurRetire') return { code: i.code, texte: fr ? `ronflement ${i.detail?.hz ?? 50} Hz supprimé` : `${i.detail?.hz ?? 50} Hz hum removed` };
    return null;
  }).filter(Boolean);
}

// Ordre d'affichage : le plus grave d'abord.
const ORDRE = ['gate', 'pompage', 'trous', 'bluetooth', 'lent', 'ecretage', 'secteur'];

// Le bandeau : une consigne par alerte, la plus grave en tête. `etat` : la sortie de
// ControlePrise.etat() (message `prise` du Worker). Rend [] si la prise est saine.
export function consignes(etat, ctx = {}) {
  const alertes = [...(etat?.alertes ?? [])].sort((a, b) => ORDRE.indexOf(a.code) - ORDRE.indexOf(b.code));
  return alertes.map((a) => consigne(a, ctx)).filter(Boolean);
}

// La mention courte pour une mesure : « prise douteuse : suppresseur de bruit ».
export function mentionDouteuse(codes, ctx = {}) {
  const fr = ctx.lang !== 'en';
  const mots = (codes ?? []).map((c) => consigne({ code: c }, ctx)?.court).filter(Boolean);
  return `${fr ? 'prise douteuse' : 'doubtful capture'}${mots.length ? ` : ${mots.join(', ')}` : ''}`;
}

// ---- Pour le JSON de la session ------------------------------------------------------------
// Empreinte courte d'un identifiant (SHA-256, 12 caractères hexadécimaux) : on garde de quoi
// reconnaître le même micro d'une session à l'autre, sans l'identifiant lui-même.
export async function hacher(texte) {
  if (!texte) return null;
  try {
    const sub = globalThis.crypto?.subtle;
    if (sub) {
      const h = await sub.digest('SHA-256', new TextEncoder().encode(String(texte)));
      return [...new Uint8Array(h)].slice(0, 6).map((b) => b.toString(16).padStart(2, '0')).join('');
    }
  } catch { /* repli ci-dessous */ }
  let x = 0x811c9dc5;
  for (const c of String(texte)) { x ^= c.codePointAt(0); x = Math.imul(x, 0x01000193) >>> 0; }
  return `fnv${x.toString(16).padStart(8, '0')}`;
}

// Tout ce que la piste sait d'elle-même, copiable dans le JSON.
export function detailPiste(piste) {
  if (!piste) return null;
  const copie = (o) => { try { return JSON.parse(JSON.stringify(o)); } catch { return null; } };
  let settings = null, capabilities = null, contraintes = null;
  try { settings = copie(piste.getSettings?.()); } catch { /* piste fermée */ }
  try { capabilities = copie(piste.getCapabilities?.()); } catch { /* non supporté */ }
  try { contraintes = copie(piste.getConstraints?.()); } catch { /* non supporté */ }
  return { label: piste.label ?? '', settings, capabilities, contraintes, readyState: piste.readyState ?? null, muted: !!piste.muted };
}

// Le bloc « micro » du JSON : label, empreinte du deviceId, getSettings complet, classement.
export async function blocMicro({ piste, deviceId = null, groupId = null }) {
  const d = detailPiste(piste);
  const id = d?.settings?.deviceId ?? deviceId;
  const groupe = d?.settings?.groupId ?? groupId;
  const label = d?.label ?? '';
  const settings = d?.settings ? { ...d.settings } : null;
  // deviceId et groupId ne sortent pas en clair.
  if (settings) { delete settings.deviceId; delete settings.groupId; }
  return {
    label,
    device_id_hash: await hacher(id),
    group_id_hash: await hacher(groupe),
    get_settings: settings,
    get_capabilities: d?.capabilities ? (() => { const c = { ...d.capabilities }; delete c.deviceId; delete c.groupId; return c; })() : null,
    contraintes_demandees: d?.contraintes ? (() => { const c = { ...d.contraintes }; delete c.deviceId; return c; })() : null,
    classement: classerMicro(label, id),
    note: scoreMicro(label, id),
  };
}
