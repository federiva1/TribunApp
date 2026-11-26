/* EUROTRIBUNAPP (prototipo): kits de los clubes europeos (camiseta titular), por id de FotMob.
   Misma idea que js/kits.js (que hay que cargar antes: usa kitBackground y NUM_OUTLINE): cada kit es un
   patrón simple — solid | stripesV | stripesH | halves | band | bandV | sash | sashR — con sus colores.
   Formato compacto: id: [tipo, color 1, color 2, grosor opcional (div: más alto = bastones más finos)].
   Son aproximados, hechos de memoria: se revisan en euro-kits.html y se corrigen acá. Un club sin kit
   cae al color que da FotMob (EURO.kit). */
const EURO_KITS = {
  // ---- Champions: clubes que no juegan en las 5 ligas
  6019: ['solid', '#43b1e6'],                       // Slovan Bratislava
  7787: ['halves', '#d82333', '#ffffff'],           // Slavia Praga
  8342: ['stripesV', '#0572ff', '#141414'],         // Club Brugge
  8402: ['solid', '#f5c800'],                       // Bodø/Glimt
  8478: ['solid', '#1b4fa0'],                       // Viking
  8563: ['solid', '#f3c200'],                       // AEK Atenas
  8637: ['halves', '#a90432', '#fdb913'],           // Galatasaray
  8640: ['stripesV', '#e00000', '#ffffff'],         // PSV
  8695: ['stripesV', '#fcd600', '#002d72'],         // Fenerbahçe
  9728: ['stripesV', '#f0602b', '#141414'],         // Shakhtar
  9768: ['stripesH', '#0a7a3c', '#ffffff', 5],      // Sporting CP
  9773: ['stripesV', '#00539f', '#ffffff'],         // Porto
  9977: ['stripesV', '#141414', '#ffffff'],         // LASK
  10235: ['halves', '#e0242a', '#ffffff'],          // Feyenoord
  951893: ['solid', '#141414'],                     // Sabah FK

  // ---- Premier League
  8455: ['solid', '#034694'],                       // Chelsea
  8456: ['solid', '#6cabdd'],                       // Manchester City
  8463: ['solid', '#ffffff'],                       // Leeds
  8472: ['stripesV', '#dc0814', '#ffffff'],         // Sunderland
  8586: ['solid', '#ffffff'],                       // Tottenham
  8650: ['solid', '#c8102e'],                       // Liverpool
  8667: ['stripesV', '#f5a31a', '#141414'],         // Hull City
  8668: ['solid', '#003399'],                       // Everton
  8669: ['solid', '#5cb8e6'],                       // Coventry
  8678: ['stripesV', '#d71921', '#141414'],         // Bournemouth
  9825: ['solid', '#ef0107'],                       // Arsenal
  9826: ['stripesV', '#1b458f', '#c4122e', 7],      // Crystal Palace
  9879: ['solid', '#ffffff'],                       // Fulham
  9902: ['solid', '#0a3d91'],                       // Ipswich
  9937: ['stripesV', '#d81920', '#ffffff'],         // Brentford
  10203: ['solid', '#c8102e'],                      // Nottingham Forest
  10204: ['stripesV', '#0057b8', '#ffffff'],        // Brighton
  10252: ['solid', '#7b003c'],                      // Aston Villa
  10260: ['solid', '#da291c'],                      // Manchester United
  10261: ['stripesV', '#141414', '#ffffff'],        // Newcastle

  // ---- Ligue 1
  6379: ['solid', '#1f3b78'],                       // Paris FC
  8121: ['stripesV', '#141414', '#ffffff'],         // Angers
  8521: ['solid', '#ed1c24'],                       // Brest
  8583: ['stripesV', '#ffffff', '#0b5ec4'],         // Auxerre
  8588: ['stripesV', '#f2b705', '#d3001a'],         // Lens
  8592: ['solid', '#ffffff'],                       // Marsella
  8639: ['solid', '#e01d13'],                       // Lille
  8682: ['stripesV', '#e11b22', '#f5c400'],         // Le Mans
  8689: ['solid', '#f58220'],                       // Lorient
  9746: ['solid', '#6fb0d8'],                       // Le Havre
  9748: ['solid', '#ffffff'],                       // Lyon
  9829: ['halves', '#e30613', '#ffffff'],           // Mónaco
  9831: ['stripesV', '#d6001c', '#141414'],         // Niza
  9847: ['bandV', '#004170', '#da291c'],            // PSG
  9848: ['solid', '#0a5bb5'],                       // Estrasburgo
  9851: ['stripesV', '#e13327', '#141414'],         // Rennes
  9941: ['solid', '#5b417b'],                       // Toulouse
  10242: ['solid', '#2a50a1'],                      // Troyes

  // ---- Bundesliga
  8149: ['solid', '#e30613'],                       // Union Berlín
  8178: ['solid', '#e32221'],                       // Leverkusen
  8226: ['solid', '#1961b5'],                       // Hoffenheim
  8232: ['stripesV', '#141414', '#ffffff'],         // Elversberg
  8358: ['solid', '#d0101f'],                       // Friburgo
  8406: ['stripesV', '#ba3733', '#ffffff'],         // Augsburgo
  8460: ['stripesV', '#004a99', '#141414'],         // Paderborn
  8697: ['solid', '#1d9053'],                       // Werder Bremen
  8722: ['solid', '#ffffff'],                       // Colonia
  9788: ['solid', '#ffffff'],                       // Gladbach
  9789: ['solid', '#fde100'],                       // Dortmund
  9790: ['solid', '#ffffff'],                       // Hamburgo
  9810: ['stripesV', '#141414', '#e1000f', 8],      // Eintracht Frankfurt
  9823: ['solid', '#dc052d'],                       // Bayern
  9905: ['solid', '#c3141e'],                       // Mainz
  10189: ['solid', '#004d9d'],                      // Schalke
  10269: ['band', '#ffffff', '#e32219'],            // Stuttgart
  178475: ['solid', '#ffffff'],                     // RB Leipzig

  // ---- Serie A
  6504: ['stripesV', '#e10032', '#ffffff'],         // Monza
  7881: ['band', '#141414', '#e87b00'],             // Venezia
  7943: ['stripesV', '#00a651', '#141414'],         // Sassuolo
  8524: ['stripesV', '#141414', '#1e71b8'],         // Atalanta
  8529: ['stripesV', '#b51f2b', '#0b2a5c', 5],      // Cagliari
  8535: ['solid', '#5f259f'],                       // Fiorentina
  8543: ['solid', '#87ceeb'],                       // Lazio
  8564: ['stripesV', '#fb090b', '#141414'],         // Milan
  8600: ['stripesV', '#141414', '#ffffff'],         // Udinese
  8636: ['stripesV', '#0068a8', '#141414'],         // Inter
  8686: ['solid', '#970a2c'],                       // Roma
  9804: ['solid', '#8a1538'],                       // Torino
  9857: ['stripesV', '#1a2f5a', '#c8102e'],         // Bolonia
  9875: ['solid', '#12a0d7'],                       // Napoli
  9885: ['stripesV', '#ffffff', '#141414'],         // Juventus
  9888: ['stripesV', '#f6c500', '#d6001c'],         // Lecce
  9891: ['stripesV', '#f5c500', '#0033a0'],         // Frosinone
  10167: ['bandV', '#ffffff', '#f5c500'],           // Parma
  10171: ['solid', '#005ea9'],                      // Como
  10233: ['halves', '#c8102e', '#0a2a5e'],          // Genoa

  // ---- LaLiga
  8302: ['solid', '#ffffff'],                       // Sevilla
  8305: ['solid', '#0057a8'],                       // Getafe
  8315: ['stripesV', '#e2001a', '#ffffff'],         // Athletic
  8370: ['sashR', '#ffffff', '#e2231a'],            // Rayo Vallecano
  8371: ['solid', '#d1111f'],                       // Osasuna
  8558: ['stripesV', '#1954b2', '#ffffff'],         // Espanyol
  8560: ['stripesV', '#0067b1', '#ffffff'],         // Real Sociedad
  8581: ['stripesV', '#0b4ea2', '#c8102e'],         // Levante
  8603: ['stripesV', '#0bb363', '#ffffff'],         // Betis
  8633: ['solid', '#ffffff'],                       // Real Madrid
  8634: ['stripesV', '#a50044', '#004d98'],         // Barcelona
  8696: ['solid', '#0b8a3a'],                       // Racing de Santander
  9783: ['stripesV', '#0b5ea8', '#ffffff'],         // Deportivo
  9864: ['stripesV', '#6baed6', '#ffffff'],         // Málaga
  9866: ['stripesV', '#0b5db5', '#ffffff'],         // Alavés
  9906: ['stripesV', '#cb3524', '#ffffff'],         // Atlético de Madrid
  9910: ['solid', '#8ac3ee'],                       // Celta
  10205: ['solid', '#fbe122'],                      // Villarreal
  10267: ['solid', '#ffffff'],                      // Valencia
  10268: ['sash', '#ffffff', '#0a8a3a'],            // Elche
};

/* Kit de un club: de la tabla de arriba; si no está, sólido con el color que da FotMob */
EURO.kit = function (id, colorFotmob) {
  const k = EURO_KITS[id];
  if (!k) return { type: 'solid', colors: [colorFotmob && colorFotmob !== '#ffffff' ? colorFotmob : '#4a5568'] };
  const o = { type: k[0], colors: k[2] ? [k[1], k[2]] : [k[1]] };
  if (k[3]) o.div = k[3];
  return o;
};
/* CSS del fondo de una ficha (círculo) de `px` de diámetro */
EURO.kitFondo = (id, px, colorFotmob) => kitBackground(EURO.kit(id, colorFotmob), px);
