import random

NBA_LANGUAGE = {
    "intro_templates": [
        "Around the NBA, the night featured a mix of standout individual performances and games that turned in the second half.",
        "Across the league, several teams leaned on star production while a handful of matchups tightened in the fourth quarter.",
        "Around the NBA, a busy slate delivered a combination of high-scoring efforts, close finishes and a few games that opened up late."
    ],
    "win_verbs": {
        "close": ["held off", "edged", "outlasted"],
        "normal": ["beat", "defeated", "topped"],
        "comfortable": ["pulled away from", "handled"],
        "blowout": ["cruised past", "rolled past"]
    },
    "flow_phrases": [
        "pulled away in the fourth quarter",
        "took control in the second half",
        "closed strong down the stretch",
        "answered with a late run",
        "weathered a late push",
        "built separation after halftime"
    ]
}

NFL_LANGUAGE = {
    "intro_templates": [
        "Around the NFL, the week featured a mix of sharp quarterback play, timely defensive stops and a few games that swung in the fourth quarter.",
        "Across the league, several teams leaned on balanced offenses while others closed out tight games late.",
        "Around the NFL, the schedule delivered a combination of efficient passing, physical rushing attacks and late-game turns."
    ],
    "win_verbs": {
        "close": ["held off", "edged", "survived against"],
        "normal": ["beat", "defeated"],
        "comfortable": ["pulled away from", "handled"],
        "blowout": ["rolled past", "routed"]
    }
}

NHL_LANGUAGE = {
    "intro_templates": [
        "Around the NHL, the night featured a mix of tight finishes, strong goaltending efforts and a few games decided late.",
        "Across the league, several teams leaned on timely scoring and steady work in net to collect wins.",
        "Around the NHL, the slate delivered close-checking games, a handful of offensive bursts and late-game tension."
    ],
    "win_verbs": {
        "close": ["edged", "held off", "slipped past"],
        "normal": ["beat", "defeated"],
        "comfortable": ["pulled away from", "handled"],
        "blowout": ["rolled past", "skated past"]
    }
}

WNBA_LANGUAGE = {
    "intro_templates": [
        "Around the WNBA, the night featured strong individual performances, disciplined team play and a few games that tightened late.",
        "Across the league, several clubs leaned on star production while others closed effectively in the fourth quarter.",
        "Around the WNBA, the schedule delivered a mix of efficient offense, steady defensive stretches and close finishes."
    ],
    "win_verbs": {
        "close": ["held off", "edged", "outlasted"],
        "normal": ["beat", "defeated"],
        "comfortable": ["pulled away from", "handled"],
        "blowout": ["rolled past", "cruised past"]
    }
}

NCAAFB_LANGUAGE = {
    "intro_templates": [
        "Around college football, the day featured momentum swings, efficient quarterback play and several games shaped by second-half execution.",
        "Across the college football slate, teams leaned on explosive plays, defensive stops and timely drives to separate themselves.",
        "Around college football, the schedule delivered rivalry tension, big-play offense and a few games that turned after halftime."
    ],
    "win_verbs": {
        "close": ["held off", "edged", "survived against"],
        "normal": ["beat", "defeated"],
        "comfortable": ["pulled away from", "handled"],
        "blowout": ["rolled past", "ran away from"]
    }
}

NCAAB_LANGUAGE = {
    "intro_templates": [
        "Around college basketball, the night featured scoring runs, late-game pressure and several matchups that tightened in the final minutes.",
        "Across the college basketball slate, teams leaned on balanced scoring, defensive stops and second-half adjustments.",
        "Around college basketball, the schedule delivered a mix of close finishes, strong individual efforts and games shaped by momentum swings."
    ],
    "win_verbs": {
        "close": ["held off", "edged", "outlasted"],
        "normal": ["beat", "defeated"],
        "comfortable": ["pulled away from", "handled"],
        "blowout": ["rolled past", "cruised past"]
    }
}

def pick_intro(language_pack):
    return random.choice(language_pack["intro_templates"])

def pick_win_verb(language_pack, margin):
    if margin <= 3:
        return random.choice(language_pack["win_verbs"]["close"])
    if margin <= 10:
        return random.choice(language_pack["win_verbs"]["normal"])
    if margin <= 20:
        return random.choice(language_pack["win_verbs"]["comfortable"])
    return random.choice(language_pack["win_verbs"]["blowout"])