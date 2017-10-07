create table `league` (
    `id` int(11) unsigned NOT NULL AUTO_INCREMENT,
    `name` varchar(128),
    PRIMARY KEY (`id`)
);

create table `team` (
    `id` int(11) NOT NULL,
    `name` varchar(128),
    `short_name` varchar(64),
    PRIMARY KEY (`id`)
);

create table `player` (
    `id` int(11) NOT NULL,
    `name` varchar(128),
    `date_of_birth` date,
    `weight` float,
    `height` float,
    `country` varchar(128),
    PRIMARY KEY (`id`)
);

create table `participation` (
    `id` int(11) unsigned NOT NULL AUTO_INCREMENT,
    `player_id` int(11),
    `match_id` int(11),
    `init_loc_x` float(11),
    `init_loc_y` float(11),
    `position` varchar(8),
    PRIMARY KEY (`id`)
);

create table `match` (
    `id` int(11) NOT NULL,
    `league_id` int(11),
    `kickoff_time` datetime,
    `stadium` varchar(128),
    `summary` varchar(256),
    `home_team_id` int(11),
    `away_team_id` int(11),
    `home_score` int(11) DEFAULT 0,
    `away_score` int(11) DEFAULT 0,
    PRIMARY KEY (`id`)
);

create table `event` (
    `id` int(11) unsigned NOT NULL AUTO_INCREMENT,
    `player_id` int(11),
    `counterparty_id` int(11),
    `match_id` int(11) NOT NULL,
    `minsec` int(11) NOT NULL,
    `event_type` varchar(32),

    `start_x` float,
    `start_y` float,
    `end_x` float,
    `end_y` float,

    `yz_plane_pt_x` float,
    `yz_plane_pt_y` float,

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
    PRIMARY KEY (`id`)
);
