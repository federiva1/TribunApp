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
  clubatleticoplatense:     { type: 'solid',    colors: ['#6a4423'] },
  union:                    { type: 'stripesV', colors: ['#e11b22', '#ffffff'], div: 11 },

  // Fecha 2 / correcciones
  barracascentral:          { type: 'stripesV', colors: ['#d4232a', '#ffffff'] },
  bocajuniors:              { type: 'band',     colors: ['#03448b', '#f4c300'] },
  estudiantes:              { type: 'stripesV', colors: ['#e2181f', '#ffffff'] },
  newellsoldboys:           { type: 'halves',   colors: ['#e2181f', '#141414'] },   // izq rojo, der negro
  deportivoriestra:         { type: 'band',     colors: ['#ffffff', '#171717'] },   // franja horizontal negra
  riverplate:               { type: 'sashR',    colors: ['#ffffff', '#e0142b'] },   // banda roja diagonal ↙
  sanlorenzo:               { type: 'stripesV', colors: ['#1f3d6b', '#d4232a'] },   // azulgrana
  talleres:                 { type: 'stripesV', colors: ['#2a3566', '#ffffff'] },
  tigre:                    { type: 'bandV',    colors: ['#182a8a', '#d4232a'] },   // azul | rojo | azul
  velezsarsfield:           { type: 'svg', colors: ['#ffffff'], svg: "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><path d='M4 3 L50 78 L96 3 L70 3 L50 52 L30 3 Z' fill='%230c4f9e'/></svg>" },

  // Rivales de copa (slug derivado del nombre api-sports, no están en CLUBES_CONFIG)
  santafe:                  { type: 'svg', colors: ['#ffffff'], svg: "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><rect width='100' height='100' fill='white'/><rect width='100' height='28' fill='%23d7182a'/><circle cx='70' cy='66' r='10' fill='%23d7182a'/></svg>" },   // Ind. Santa Fe: rojo arriba + puntito
  fluminense:               { type: 'svg', colors: ['#ffffff'], svg: "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><rect width='100' height='100' fill='white'/><rect x='0' width='20' height='100' fill='%23861638'/><rect x='40' width='20' height='100' fill='%23107a42'/><rect x='80' width='20' height='100' fill='%23861638'/></svg>" },   // tricolor: graná | blanco | verde
  saopaulo:                 { type: 'svg', colors: ['#ffffff'], svg: "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><rect width='100' height='100' fill='white'/><rect y='32' width='100' height='17' fill='%23e2231a'/><rect y='49' width='100' height='17' fill='%23141414'/></svg>" },   // blanco con franjas roja y negra
  corinthians:              { type: 'solid',    colors: ['#ffffff'] },   // titular blanca lisa
};

// Kit del club; si no tiene uno definido, sólido con su color de escudo (club-colors.js).
function clubKit(slug) {
  if (typeof KITS !== 'undefined' && KITS[slug]) return KITS[slug];
  var cc = (typeof CLUB_COLORS !== 'undefined' && CLUB_COLORS[slug]) || {};
  var cfg = (typeof CLUBES_CONFIG !== 'undefined' && CLUBES_CONFIG[slug]) || {};
  return { type: 'solid', colors: [cc.primary || cfg.color || '#444'] };
}

// `background` CSS del kit, con anchos proporcionales al tamaño del chip.
// SVG → data: URI apto para un url() sin comillas. Se normaliza el '%23' que traen
// los kits (el '#' de los colores ya viene escapado) antes de encodear, para no
// terminar con un doble escape '%2523'. encodeURIComponent deja pasar ' ( ),
// que en un url() sin comillas también rompen, así que se encodean aparte.
function _svgUri(svg) {
  return encodeURIComponent(String(svg || '').replace(/%23/g, '#'))
    .replace(/[()']/g, function (c) { return '%' + c.charCodeAt(0).toString(16).toUpperCase(); });
}

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
    // OJO: el valor que devuelve esta función también se interpola en atributos
    // style="..." armados con innerHTML (tribunapp-equipo.html, estadisticas.html),
    // así que NO puede contener comillas: una comilla doble cerraba el atributo y
    // el resto del CSS se volcaba como texto en la página. Por eso el data: URI va
    // sin comillas y percent-encodeado — url() sin comillas tampoco admite espacios,
    // comillas simples ni paréntesis. Cualquier tipo nuevo debe respetar lo mismo.
    case 'svg':      return (a || '#ffffff') + ' url(data:image/svg+xml,' + _svgUri(kit.svg) + ') center/100% no-repeat';
    default:         return a;
  }
}

// Números siempre en blanco con contorno oscuro (legibles sobre cualquier patrón).
var NUM_OUTLINE = '-1px -1px 0 rgba(0,0,0,0.55),1px -1px 0 rgba(0,0,0,0.55),'
  + '-1px 1px 0 rgba(0,0,0,0.55),1px 1px 0 rgba(0,0,0,0.55),0 2px 3px rgba(0,0,0,0.5)';
