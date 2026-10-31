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
  function pointsForPlayer(level, name, hideNumber) {
    var revealed = Math.max(0, (level ?? 0) - (hideNumber ? 1 : 0));
    var letters = [...(name || "")].filter(function (letter) { return /[\p{L}\p{N}]/u.test(letter); }).length;
    if (name && (revealed >= 2 || (letters && revealed >= Math.ceil(letters / 2)))) return 0;
    return level === undefined ? 3 : [2, 1][level] || 0;
  }
  function pendingModes(match, entries) {
    return ["formation", "scorers", "result"].filter(function (mode) {
      return eligible([match], "all", mode).length && !entries.some(function (entry) {
        return entry.matchId === match.id && entry.mode === mode;
      });
    });
  }
  function scorerHintPlan(match, eliminated, used) {
    if (used >= 3) return [];
    var actual = new Set(actualScorers(match));
    var wrong = scorerCandidates(match).filter(function (p) {
      return !actual.has(p.id) && !eliminated.has(p.id);
    });
    var home = wrong.filter(function (p) { return p.team === match.home; });
    var away = wrong.filter(function (p) { return p.team === match.away; });
    var balanced = [];
    while (home.length || away.length) {
      if (home.length) balanced.push(home.shift());
      if (away.length) balanced.push(away.shift());
    }
    var count = used === 2 ? wrong.length : Math.max(1, Math.min(wrong.length - 1, Math.ceil(wrong.length / 2)));
    return balanced.slice(0, count).map(function (p) { return p.id; });
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
    var showSubstitutes = roster.some(function (p) {
      return p.substitute && (match.scorers || []).some(function (name, index) {
        return normalize(name) === normalize(p.name) && (!(match.scorerTeams || [])[index] || match.scorerTeams[index] === p.team);
      });
    });
    return roster.filter(function (p) {
      if (p.substitute && !showSubstitutes) return false;
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
        (!match.availability || match.availability[mode] === true) &&
        (!club ||
          club === "all" ||
          [match.home, match.away, match.homeSlug, match.awaySlug].includes(club)) &&
        (mode !== "scorers" ||
          (match.scorers.length > 0 && !match.scorerAmbiguous && !match.scorerIncomplete))
      );
    });
  }
  // Input order is the published chronological order. Every shorter route is a
  // prefix of the same selection priority, then displayed chronologically.
  function routeMatches(matches, club, route) {
    var options = matches.filter(function (match) {
      return (!club || club === "all" || [match.homeSlug, match.awaySlug].includes(club)) && matchModes(match).length;
    });
    var count = route === "express" ? Math.min(5, Math.ceil(options.length / 3))
      : route === "classic" ? Math.ceil(options.length / 2) : options.length;
    if (!count) return [];
    var order = [options.length - 1];
    if (options.length > 1) order.push(0);
    while (order.length < count) {
      var sorted = order.slice().sort(function (a, b) { return a - b; });
      var left = 0, gap = 0;
      for (var i = 1; i < sorted.length; i++) {
        if (sorted[i] - sorted[i - 1] > gap) { left = sorted[i - 1]; gap = sorted[i] - left; }
      }
      order.push(left + Math.ceil(gap / 2));
    }
    return order.slice(0, count).sort(function (a, b) { return a - b; }).map(function (index) { return options[index]; });
  }
  function matchModes(match) {
    return match.modes || ["formation", "scorers", "result"].filter(function (mode) { return eligible([match], "all", mode).length; });
  }
  function positionRank(position) {
    var code = String(position || "").toUpperCase();
    var groups = [
      ["G", "GK", "ARQ"],
      ["D", "DF", "DEF", "CD", "CD-L", "CD-R", "LB", "RB", "SW", "LWB", "RWB"],
      ["M", "MF", "MED", "DM", "CM", "CM-L", "CM-R", "LM", "RM", "AM", "AM-L", "AM-R"],
      ["F", "FW", "DEL", "CF", "CF-L", "CF-R", "LF", "RF", "LCF", "RCF", "LW", "RW", "ST"]
    ];
    return groups.findIndex(function (group) { return group.includes(code); });
  }
  function orderedLineup(players) {
    // Keep source indices: hints, answers and drafts must still address the same player.
    var rows = players.map(function (player, index) { return { player: player, index: index }; });
    var known = rows.filter(function (row) { return positionRank(row.player.pos) >= 0; })
      .sort(function (a, b) { return positionRank(a.player.pos) - positionRank(b.player.pos) || a.index - b.index; });
    // The legacy tournament already follows its source's pitch order, but omits roles.
    // Preserve those slots instead of guessing positions from shirt numbers or a 4-4-2.
    var next = 0;
    return rows.map(function (row) { return positionRank(row.player.pos) < 0 ? row : known[next++]; });
  }
  function randomChallenge(matches, entries, previousId, random) {
    random = random || Math.random;
    var options = matches.filter(function (match) { return matchModes(match).length; });
    var untouched = options.filter(function (match) { return !entries.some(function (entry) { return entry.matchId === match.id; }); });
    var pending = options.filter(function (match) { return matchModes(match).some(function (mode) {
      return !entries.some(function (entry) { return entry.matchId === match.id && entry.mode === mode; });
    }); });
    options = untouched.length ? untouched : pending.length ? pending : options;
    if (options.some(function (match) { return match.id !== previousId; })) options = options.filter(function (match) { return match.id !== previousId; });
    if (!options.length) return null;
    var pick = function (list) { return list[Math.min(list.length - 1, Math.max(0, Math.floor(random() * list.length)))]; };
    var match = pick(options), available = matchModes(match);
    var missing = available.filter(function (mode) { return !entries.some(function (entry) { return entry.matchId === match.id && entry.mode === mode; }); });
    return { match: match, mode: pick(missing.length ? missing : available) };
  }
  function routeStatus(matches, entries, collectionId) {
    var allowed = new Map(matches.map(function (match) { return [match.id, matchModes(match)]; }));
    var relevant = bestEntries(entries.filter(function (entry) {
      return entry.collectionId === collectionId && allowed.get(entry.matchId)?.includes(entry.mode);
    }));
    var completed = new Set(relevant.map(function (entry) { return entry.matchId; }));
    return { total: matches.length, done: completed.size, complete: matches.length > 0 && completed.size === matches.length,
      score: relevant.reduce(function (sum, entry) { return sum + entry.bestScore; }, 0),
      remaining: matches.filter(function (match) { return !completed.has(match.id); }) };
  }
  function formationSides(match, club) {
    var sides = ["home", "away"];
    return !club || club === "all" ? sides : sides.filter(function (side) { return match[side + "Slug"] === club; });
  }
  function bestEntries(entries) {
    var unique = new Map();
    entries.forEach(function (entry) {
      var key = JSON.stringify([entry.collectionId, entry.matchId, entry.mode]), previous = unique.get(key);
      if (!previous || entry.bestScore > previous.bestScore || (entry.bestScore === previous.bestScore && entry.updatedAt > previous.updatedAt)) unique.set(key, entry);
    });
    return [...unique.values()];
  }
  function progressForClub(entries, club) {
    return bestEntries(entries.filter(function (entry) {
      return entry.mode !== "formation" || !entry.formationClub || entry.formationClub === "all" || entry.formationClub === club;
    }));
  }
  function personalCampaigns(collections, activity, entries) {
    var played = new Map();
    function add(item, club, date) {
      club = item.clubSlug || club || "all";
      if (club !== "all" && !item.matches.some(function (m) { return m.homeSlug === club || m.awaySlug === club; })) return;
      var key = item.id + "|" + club, previous = played.get(key);
      if (!previous || date > previous.lastPlayedAt) played.set(key, { item: item, club: club, lastPlayedAt: date });
    }
    activity.forEach(function (record) {
      var item = collections.find(function (c) { return c.id === record.collectionId; });
      if (item) add(item, record.club, record.startedAt);
    });
    entries.forEach(function (entry) {
      var item = collections.find(function (c) { return c.id === entry.collectionId && c.matches.some(function (m) { return m.id === entry.matchId; }); });
      if (item) add(item, entry.playClub || entry.formationClub, entry.updatedAt);
    });
    return [...played.values()].sort(function (a, b) { return b.lastPlayedAt.localeCompare(a.lastPlayedAt); });
  }
  return {
    positionRank: positionRank,
    orderedLineup: orderedLineup,
    randomChallenge: randomChallenge,
    formationSides: formationSides,
    bestEntries: bestEntries,
    progressForClub: progressForClub,
    personalCampaigns: personalCampaigns,
    routeMatches: routeMatches,
    routeStatus: routeStatus,
    matchModes: matchModes,
    normalize: normalize,
    acceptedAnswer: acceptedAnswer,
    pointsForPlayer: pointsForPlayer,
    pendingModes: pendingModes,
    scorerHintPlan: scorerHintPlan,
    scorerCandidates: scorerCandidates,
    actualScorers: actualScorers,
    scoreScorers: scoreScorers,
    eligible: eligible,
  };
});
