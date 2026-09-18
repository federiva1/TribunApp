(function (root, factory) {
  "use strict";
  var api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  if (root) root.CampanasCore = api;
})(typeof window !== "undefined" ? window : null, function () {
  "use strict";
  function normalize(value) {
    return String(value == null ? "" : value)
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .toLowerCase()
      .trim()
      .replace(/\s+/g, " ");
  }
  function acceptedAnswer(answer, player) {
    var name = typeof player === "string" ? player : player.name;
    var aliases = typeof player === "object" ? player.accepted_answers || [] : [];
    if (normalize(name) === "cortes") aliases = aliases.concat("cortez");
    return (
      !!normalize(answer) &&
      [name].concat(aliases).some(function (item) {
        return normalize(item) === normalize(answer);
      })
    );
  }
  function pointsForPlayer(level) {
    return level === undefined ? 3 : [2, 1][level] || 0;
  }
  function scorerCandidates(match) {
    var seen = new Set();
    var roster = ["home", "away"].flatMap(function (side) {
      return (match[side + "XI"] || [])
        .map(function (p) {
          return Object.assign({}, p, { substitute: false });
        })
        .concat(
          (match[side + "Subs"] || []).map(function (p) {
            return Object.assign({}, p, { substitute: true });
          }),
        )
        .map(function (p) {
          return Object.assign({}, p, { id: match[side] + "|" + p.name, team: match[side] });
        });
    });
    // A goal event can name a player omitted/abbreviated in the source roster.
    // Keep that recorded author selectable without inventing a shirt or role.
    (match.scorers || []).forEach(function (name, index) {
      var team = (match.scorerTeams || [])[index];
      if (
        team &&
        !roster.some(function (p) {
          return p.team === team && normalize(p.name) === normalize(name);
        })
      ) {
        roster.push({
          id: team + "|" + name,
          team: team,
          name: name,
          n: null,
          substitute: false,
          rosterUnknown: true,
        });
      }
    });
    return roster.filter(function (p) {
      var key = normalize(p.id);
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });
  }
  function actualScorers(match) {
    var candidates = scorerCandidates(match);
    return match.scorers.map(function (name, index) {
      var team = (match.scorerTeams || [])[index];
      var options = candidates.filter(function (p) {
        return normalize(p.name) === normalize(name) && (!team || p.team === team);
      });
      if (options.length !== 1)
        throw new Error("Autor de gol ambiguo o ausente: " + match.id + " / " + name);
      return options[0].id;
    });
  }
  function scoreScorers(selected, match, hints) {
    var expected = actualScorers(match).map(normalize).sort();
    var answers = selected.map(normalize).sort();
    var correct =
      expected.length > 0 &&
      answers.length === expected.length &&
      answers.every(function (answer, i) {
        return answer === expected[i];
      });
    return { correct: correct, score: correct ? [20, 14, 8, 0][hints || 0] || 0 : -5 };
  }
  function eligible(matches, club, mode) {
    return matches.filter(function (match) {
      return (
        (!club ||
          club === "all" ||
          [match.home, match.away, match.homeSlug, match.awaySlug].includes(club)) &&
        (mode !== "scorers" ||
          (match.scorers.length > 0 && !match.scorerAmbiguous && !match.scorerIncomplete))
      );
    });
  }
  return {
    normalize: normalize,
    acceptedAnswer: acceptedAnswer,
    pointsForPlayer: pointsForPlayer,
    scorerCandidates: scorerCandidates,
    actualScorers: actualScorers,
    scoreScorers: scoreScorers,
    eligible: eligible,
  };
});
