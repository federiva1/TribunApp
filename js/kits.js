// Kits de los clubes — fuente ÚNICA (la usan club.html y estadisticas.html).
// Colores tomados del escudo (ver js/club-colors.js). Se renderiza como fondo de los
// "kit chips" (formación, puntajes, avatares de jugadores) vía kitBackground().
//
// type:  solid | stripesV | stripesH | halves | band | bandV | sash | sashR
//   - stripesV/H : bastones (verticales/horizontales). `div` opcional = divisor del
//                  ancho de bastón (más alto = bastones más finos; default 6).
//   - band  : franja horizontal del 2º color sobre base del 1º.
//   - bandV : franja vertical del 2º color sobre base del 1º (centrada, ancha).
//   - sash  : banda diagonal del 2º color ↘ (arriba-izq → abajo-der).
//   - sashR : banda diagonal del 2º color ↙ (arriba-der → abajo-izq).
var KITS = {
  // Ya definidos
  sarmiento:                { type: 'solid',    colors: ['#1b8a3e'] },
  argentinosjuniors:        { type: 'sash',     colors: ['#e12026', '#ffffff'] },
  atleticotucuman:          { type: 'stripesV', colors: ['#53b7e8', '#ffffff'] },
  independienterivadavia:   { type: 'solid',    colors: ['#291670'] },

  // Fecha 1 (definidos con el usuario)
  belgrano:                 { type: 'solid',    colors: ['#1fbcea'] },
  rosariocentral:           { type: 'stripesV', colors: ['#063f7c', '#f9e800'] },
  defensayjusticia:         { type: 'sashR',    colors: ['#016b2c', '#fde100'] },
  aldosivi:                 { type: 'stripesV', colors: ['#2f9e5c', '#f2d91f'] },
  gimnasiamendoza:          { type: 'stripesV', colors: ['#171717', '#ffffff'], div: 11 },
  centralcordobadesantiago: { type: 'stripesV', colors: ['#171717', '#ffffff'], div: 7 },
  racingclub:               { type: 'stripesV', colors: ['#3f9fd6', '#ffffff'] },
  gimnasialp:               { type: 'band',     colors: ['#ffffff', '#24246b'] },
  instituto:                { type: 'stripesV', colors: ['#e2181f', '#ffffff'] },
  banfield:                 { type: 'stripesV', colors: ['#2e8b40', '#ffffff'] },
  huracan:                  { type: 'bandV',    colors: ['#ffffff', '#e2231a'] },
  clubatleticoplatense:     { type: 'sashR',    colors: ['#ffffff', '#6a4423'] },
  union:                    { type: 'stripesV', colors: ['#e11b22', '#ffffff'], div: 11 },
};

// Kit del club; si no tiene uno definido, sólido con su color de escudo (club-colors.js).
function clubKit(slug) {
  if (typeof KITS !== 'undefined' && KITS[slug]) return KITS[slug];
  var cc = (typeof CLUB_COLORS !== 'undefined' && CLUB_COLORS[slug]) || {};
  var cfg = (typeof CLUBES_CONFIG !== 'undefined' && CLUBES_CONFIG[slug]) || {};
  return { type: 'solid', colors: [cc.primary || cfg.color || '#444'] };
}

// `background` CSS del kit, con anchos proporcionales al tamaño del chip.
function kitBackground(kit, size) {
  var a = kit.colors[0], b = kit.colors[1] || '#ffffff';
  var w = Math.max(3, Math.round(size / (kit.div || 6)));
  switch (kit.type) {
    case 'stripesV': return 'repeating-linear-gradient(90deg, ' + a + ' 0 ' + w + 'px, ' + b + ' ' + w + 'px ' + (2 * w) + 'px)';
    case 'stripesH': return 'repeating-linear-gradient(0deg, ' + a + ' 0 ' + w + 'px, ' + b + ' ' + w + 'px ' + (2 * w) + 'px)';
    case 'halves':   return 'linear-gradient(90deg, ' + a + ' 0 50%, ' + b + ' 50% 100%)';
    case 'band':     return 'linear-gradient(0deg, ' + a + ' 0 36%, ' + b + ' 36% 64%, ' + a + ' 64% 100%)';
    case 'bandV':    return 'linear-gradient(90deg, ' + a + ' 0 33%, ' + b + ' 33% 67%, ' + a + ' 67% 100%)';
    case 'sash':     return 'linear-gradient(45deg, ' + a + ' 0 42%, ' + b + ' 42% 58%, ' + a + ' 58% 100%)';
    case 'sashR':    return 'linear-gradient(-45deg, ' + a + ' 0 42%, ' + b + ' 42% 58%, ' + a + ' 58% 100%)';
    default:         return a;
  }
}

// Números siempre en blanco con contorno oscuro (legibles sobre cualquier patrón).
var NUM_OUTLINE = '-1px -1px 0 rgba(0,0,0,0.55),1px -1px 0 rgba(0,0,0,0.55),'
  + '-1px 1px 0 rgba(0,0,0,0.55),1px 1px 0 rgba(0,0,0,0.55),0 2px 3px rgba(0,0,0,0.5)';
