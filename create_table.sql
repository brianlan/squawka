create table `league` (
    `id` int(11) unsigned NOT NULL AUTO_INCREMENT,
    `short_url_name` varchar(32),
    `long_url_name` varchar(64),
    `human_readable_name` varchar(128),
    `row_cre_ts` datetime DEFAULT current_timestamp(),
    PRIMARY KEY (`id`)
);

create table `team` (
    `id` int(11) NOT NULL,
    `name` varchar(128),
    `short_name` varchar(64),
    `row_cre_ts` datetime DEFAULT current_timestamp(),
    PRIMARY KEY (`id`)
);

create table `player` (
    `id` int(11) NOT NULL,
    `name` varchar(128),
    `date_of_birth` date,
    `weight` float,
    `height` float,
    `country` varchar(128),
    `row_cre_ts` datetime DEFAULT current_timestamp(),
    PRIMARY KEY (`id`)
);

create table `participation` (
    `player_id` int(11),
    `match_id` int(11),
    `team_id` int(11),
    `init_loc_0` float(11),
    `init_loc_1` float(11),
    `position` varchar(32),
    `row_cre_ts` datetime DEFAULT current_timestamp(),
    PRIMARY KEY (`player_id`, `match_id`, `team_id`)
);

create table `match` (
    `id` int(11) NOT NULL,
    `url` varchar(1024),
    `league_name` varchar(64),
    `kickoff_time` datetime,
    `stadium` varchar(128),
    `summary` varchar(256),
    `home_team_id` int(11),
    `away_team_id` int(11),
    `home_score` int(11) DEFAULT 0,
    `away_score` int(11) DEFAULT 0,
    `row_cre_ts` datetime DEFAULT current_timestamp(),
    PRIMARY KEY (`id`)
);

create table `event` (
    `id` int(11) unsigned NOT NULL AUTO_INCREMENT,
    `player_id` int(11),
    `counterparty_id` int(11),
    `match_id` int(11) NOT NULL,
    `minsec` int(11) NOT NULL,
    `event_type` varchar(32),

    `start_0` float,
    `start_1` float,
    `end_0` float,
    `end_1` float,

    `yz_plane_coord_0` float,
    `yz_plane_coord_1` float,

    `a` tinyint(1),
    `action_type` varchar(32),
    `card_type` varchar(16),
    `gy` float,
    `gz` float,
    `headed` tinyint(1),
    `injurytime_play` tinyint(1),
    `k` tinyint(1),
    `ot_id` int(11),
    `ot_outcome` tinyint(1),
    `throw_ins` tinyint(1),
    `type` varchar(32),
    `uid` varchar(16),
    `row_cre_ts` datetime DEFAULT current_timestamp(),
    PRIMARY KEY (`id`)
);
