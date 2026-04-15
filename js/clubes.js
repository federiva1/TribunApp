// TribunApp — Configuración de todos los clubes de la Liga Profesional Argentina 2026
// squad: [] — se completa con el scraper; cada jugador tendrá {num, name, fid}

const CLUBES_CONFIG = {
  velezsarsfield: {
    id: 438, nombre: 'Vélez Sarsfield', nombreCorto: 'Vélez',
    color: '#003087', colorSecundario: '#fff',
    squad: []
  },
  estudiantes: {
    id: 450, nombre: 'Estudiantes de La Plata', nombreCorto: 'Estudiantes',
    color: '#e53935', colorSecundario: '#fff',
    squad: []
  },
  bocajuniors: {
    id: 451, nombre: 'Boca Juniors', nombreCorto: 'Boca',
    color: '#003087', colorSecundario: '#f5c518',
    squad: []
  },
  defensayjusticia: {
    id: 442, nombre: 'Defensa y Justicia', nombreCorto: 'Def. Justicia',
    color: '#f5c518', colorSecundario: '#003087',
    squad: []
  },
  union: {
    id: 441, nombre: 'Unión de Santa Fe', nombreCorto: 'Unión SF',
    color: '#e53935', colorSecundario: '#fff',
    squad: []
  },
  lanus: {
    id: 446, nombre: 'Lanús', nombreCorto: 'Lanús',
    color: '#006847', colorSecundario: '#fff',
    squad: []
  },
  talleres: {
    id: 456, nombre: 'Talleres de Córdoba', nombreCorto: 'Talleres',
    color: '#003087', colorSecundario: '#fff',
    squad: []
  },
  independiente: {
    id: 453, nombre: 'Independiente', nombreCorto: 'Independiente',
    color: '#e53935', colorSecundario: '#fff',
    squad: []
  },
  sanlorenzo: {
    id: 460, nombre: 'San Lorenzo', nombreCorto: 'San Lorenzo',
    color: '#003087', colorSecundario: '#e53935',
    squad: []
  },
  clubatleticoplatense: {
    id: 1064, nombre: 'Platense', nombreCorto: 'Platense',
    color: '#003087', colorSecundario: '#f5c518',
    squad: []
  },
  gimnasiamendoza: {
    id: 1066, nombre: 'Gimnasia y Esgrima de Mendoza', nombreCorto: 'Gimnasia M',
    color: '#2e7d32', colorSecundario: '#fff',
    squad: []
  },
  centralcordobadesantiago: {
    id: 1065, nombre: 'Central Córdoba de Santiago', nombreCorto: 'Cen. Córdoba',
    color: '#1a1a1a', colorSecundario: '#e53935',
    squad: []
  },
  instituto: {
    id: 478, nombre: 'Instituto de Córdoba', nombreCorto: 'Instituto',
    color: '#003087', colorSecundario: '#e53935',
    squad: []
  },
  deportivoriestra: {
    id: 476, nombre: 'Deportivo Riestra', nombreCorto: 'Riestra',
    color: '#e53935', colorSecundario: '#fff',
    squad: []
  },
  newellsoldboys: {
    id: 457, nombre: "Newell's Old Boys", nombreCorto: "Newell's",
    color: '#e53935', colorSecundario: '#000',
    squad: []
  },
  independienterivadavia: {
    id: 473, nombre: 'Independiente Rivadavia', nombreCorto: 'Ind. Rivadavia',
    color: '#003087', colorSecundario: '#fff',
    squad: []
  },
  riverplate: {
    id: 435, nombre: 'River Plate', nombreCorto: 'River',
    color: '#e53935', colorSecundario: '#fff',
    squad: []
  },
  argentinosjuniors: {
    id: 458, nombre: 'Argentinos Juniors', nombreCorto: 'Argentinos',
    color: '#e53935', colorSecundario: '#fff',
    squad: []
  },
  belgrano: {
    id: 440, nombre: 'Belgrano', nombreCorto: 'Belgrano',
    color: '#003087', colorSecundario: '#fff',
    squad: []
  },
  racingclub: {
    id: 436, nombre: 'Racing Club', nombreCorto: 'Racing',
    color: '#1a1a1a', colorSecundario: '#e53935',
    squad: []
  },
  rosariocentral: {
    id: 437, nombre: 'Rosario Central', nombreCorto: 'Rosario C',
    color: '#f5c518', colorSecundario: '#1a1a1a',
    squad: []
  },
  tigre: {
    id: 452, nombre: 'Tigre', nombreCorto: 'Tigre',
    color: '#e53935', colorSecundario: '#f5c518',
    squad: []
  },
  barracascentral: {
    id: 2432, nombre: 'Barracas Central', nombreCorto: 'Barracas C',
    color: '#e53935', colorSecundario: '#fff',
    squad: []
  },
  sarmiento: {
    id: 474, nombre: 'Sarmiento de Junín', nombreCorto: 'Sarmiento',
    color: '#2e7d32', colorSecundario: '#fff',
    squad: []
  },
  huracan: {
    id: 445, nombre: 'Huracán', nombreCorto: 'Huracán',
    color: '#e53935', colorSecundario: '#fff',
    squad: []
  },
  gimnasialp: {
    id: 434, nombre: 'Gimnasia y Esgrima LP', nombreCorto: 'Gimnasia LP',
    color: '#003087', colorSecundario: '#fff',
    squad: []
  },
  banfield: {
    id: 449, nombre: 'Banfield', nombreCorto: 'Banfield',
    color: '#2e7d32', colorSecundario: '#fff',
    squad: []
  },
  atleticotucuman: {
    id: 455, nombre: 'Atlético Tucumán', nombreCorto: 'Atl. Tucumán',
    color: '#003087', colorSecundario: '#fff',
    squad: []
  },
  aldosivi: {
    id: 463, nombre: 'Aldosivi', nombreCorto: 'Aldosivi',
    color: '#006847', colorSecundario: '#f5c518',
    squad: []
  },
  estudiantesderiocuarto: {
    id: 2424, nombre: 'Estudiantes de Río Cuarto', nombreCorto: 'Est. Río Cuarto',
    color: '#e53935', colorSecundario: '#000',
    squad: []
  }
};

// Mapeo API-Sports ID → slug
const ESCUDO_MAP = {
  438:'velezsarsfield', 450:'estudiantes', 451:'bocajuniors', 442:'defensayjusticia',
  441:'union', 446:'lanus', 456:'talleres', 453:'independiente', 460:'sanlorenzo',
  1064:'clubatleticoplatense', 1066:'gimnasiamendoza', 1065:'centralcordobadesantiago',
  478:'instituto', 476:'deportivoriestra', 457:'newellsoldboys', 473:'independienterivadavia',
  435:'riverplate', 458:'argentinosjuniors', 440:'belgrano', 436:'racingclub',
  437:'rosariocentral', 452:'tigre', 2432:'barracascentral', 474:'sarmiento',
  445:'huracan', 434:'gimnasialp', 449:'banfield', 455:'atleticotucuman',
  463:'aldosivi', 2424:'estudiantesderiocuarto'
};

const NOMBRE_CORTO_T = {
  438:'Vélez', 450:'Estudiantes', 451:'Boca', 442:'Def. Justicia', 441:'Unión SF',
  446:'Lanús', 456:'Talleres', 453:'Independiente', 460:'San Lorenzo', 1064:'Platense',
  1066:'Gimnasia M', 1065:'Cen. Córdoba', 478:'Instituto', 476:'Riestra', 457:"Newell's",
  473:'Ind. Rivadavia', 435:'River', 458:'Argentinos', 440:'Belgrano', 436:'Racing',
  437:'Rosario C', 452:'Tigre', 2432:'Barracas C', 474:'Sarmiento', 445:'Huracán',
  434:'Gimnasia LP', 449:'Banfield', 455:'Atl. Tucumán', 463:'Aldosivi', 2424:'Est. Río Cuarto'
};
