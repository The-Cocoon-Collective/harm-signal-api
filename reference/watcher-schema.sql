-- ===========================================================================
--  harm-signal-api - reference physical schema  (MySQL 8 / MariaDB 10.5+)
--
--  The 9 event families and 26 observation types of SPEC.md, as tables you can
--  create today. This file is generated from the reference emitter's own
--  schema code, so it cannot drift from what that plugin actually builds.
--
--  Read IMPLEMENTATION.md alongside it: these tables are the PRIVATE store.
--  They hold real ids and real message text on purpose. Observations are a
--  projection of them, and the projection is where an id becomes a ref and an
--  utterance becomes a content_ref.
--
--  Every table answers the same five questions:
--      event_type / who / where (server, world, x, y, z) / who else / when
--
--  `others` is co-presence AT WRITE TIME. It is the one column that cannot be
--  backfilled: presence has duration, events have instants, and "in range" is
--  a judgement only the platform can make, and only then.
-- ===========================================================================


CREATE TABLE IF NOT EXISTS session_events (
  id           BIGINT AUTO_INCREMENT PRIMARY KEY,
  player_uuid  CHAR(36)    NOT NULL,
  player_name  VARCHAR(32) NOT NULL,
  kind         VARCHAR(16) NOT NULL,
  server       VARCHAR(16) NOT NULL,
  at           TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP,
  KEY idx_player (player_uuid, at),
  KEY idx_when   (at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS sightings (
  id           BIGINT AUTO_INCREMENT PRIMARY KEY,
  post_id      VARCHAR(64)  NOT NULL,
  player_uuid  CHAR(36)     NOT NULL,
  player_name  VARCHAR(32)  NOT NULL,
  server       VARCHAR(16)  NOT NULL,
  world        VARCHAR(64)  NOT NULL,
  x            INT          NOT NULL,
  y            INT          NOT NULL,
  z            INT          NOT NULL,
  others       VARCHAR(512) NULL,
  seen_at      TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  acknowledged TINYINT(1)   NOT NULL DEFAULT 0,
  KEY idx_post   (post_id, acknowledged),
  KEY idx_player (player_uuid, seen_at),
  KEY idx_when   (seen_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS chat_events (
  id           BIGINT AUTO_INCREMENT PRIMARY KEY,
  player_uuid  CHAR(36)     NOT NULL,
  player_name  VARCHAR(32)  NOT NULL,
  message      TEXT         NOT NULL,
  channel      VARCHAR(32)  NOT NULL DEFAULT 'public',
  server       VARCHAR(16)  NOT NULL,
  world        VARCHAR(64)  NOT NULL,
  x            INT          NOT NULL,
  y            INT          NOT NULL,
  z            INT          NOT NULL,
  others       VARCHAR(512) NULL,
  said_at      TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  KEY idx_player (player_uuid, said_at),
  KEY idx_when   (said_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS proximity_events (
  id           BIGINT AUTO_INCREMENT PRIMARY KEY,
  event_type   VARCHAR(32)  NOT NULL,
  player_uuid  CHAR(36)     NOT NULL,
  player_name  VARCHAR(32)  NOT NULL,
  other_uuid   CHAR(36)     NOT NULL,
  other_name   VARCHAR(32)  NOT NULL,
  server       VARCHAR(16)  NOT NULL,
  world        VARCHAR(64)  NOT NULL,
  x            INT          NOT NULL,
  y            INT          NOT NULL,
  z            INT          NOT NULL,
  duration_ms  INT          NULL,
  distance_avg DOUBLE       NULL,
  samples      INT          NULL,
  others       VARCHAR(512) NULL,
  at           TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  KEY idx_player (player_uuid, at),
  KEY idx_other  (other_uuid, at),
  KEY idx_pair   (player_uuid, other_uuid, at),
  KEY idx_type   (event_type, at),
  KEY idx_when   (at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS interaction_events (
  id           BIGINT AUTO_INCREMENT PRIMARY KEY,
  event_type   VARCHAR(32)  NOT NULL,
  player_uuid  CHAR(36)     NOT NULL,
  player_name  VARCHAR(32)  NOT NULL,
  target_uuid  CHAR(36)     NULL,
  target_name  VARCHAR(32)  NULL,
  verb         VARCHAR(32)  NULL,
  magnitude    INT          NULL,
  outcome      VARCHAR(32)  NULL,
  server       VARCHAR(16)  NOT NULL,
  world        VARCHAR(64)  NOT NULL,
  x            INT          NOT NULL,
  y            INT          NOT NULL,
  z            INT          NOT NULL,
  others       VARCHAR(512) NULL,
  at           TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  KEY idx_player (player_uuid, at),
  KEY idx_target (target_uuid, at),
  KEY idx_type   (event_type, at),
  KEY idx_when   (at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS affiliation_events (
  id           BIGINT AUTO_INCREMENT PRIMARY KEY,
  event_type   VARCHAR(32)  NOT NULL,
  player_uuid  CHAR(36)     NOT NULL,
  player_name  VARCHAR(32)  NOT NULL,
  subject_uuid CHAR(36)     NULL,
  subject_name VARCHAR(32)  NULL,
  group_id     VARCHAR(64)  NOT NULL,
  group_kind   VARCHAR(32)  NULL,
  size_after   INT          NULL,
  server       VARCHAR(16)  NOT NULL,
  world        VARCHAR(64)  NOT NULL,
  x            INT          NOT NULL,
  y            INT          NOT NULL,
  z            INT          NOT NULL,
  others       VARCHAR(512) NULL,
  at           TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  KEY idx_player  (player_uuid, at),
  KEY idx_subject (subject_uuid, at),
  KEY idx_group   (group_id, at),
  KEY idx_type    (event_type, at),
  KEY idx_when    (at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS artifact_events (
  id            BIGINT AUTO_INCREMENT PRIMARY KEY,
  event_type    VARCHAR(32)  NOT NULL,
  player_uuid   CHAR(36)     NOT NULL,
  player_name   VARCHAR(32)  NOT NULL,
  artifact_kind VARCHAR(64)  NULL,
  artifact_ref  VARCHAR(64)  NULL,
  owner_uuid    CHAR(36)     NULL,
  quantity      INT          NULL,
  server        VARCHAR(16)  NOT NULL,
  world         VARCHAR(64)  NOT NULL,
  x             INT          NOT NULL,
  y             INT          NOT NULL,
  z             INT          NOT NULL,
  others        VARCHAR(512) NULL,
  at            TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  KEY idx_player (player_uuid, at),
  KEY idx_owner  (owner_uuid, at),
  KEY idx_type   (event_type, at),
  KEY idx_when   (at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS transfer_events (
  id            BIGINT AUTO_INCREMENT PRIMARY KEY,
  event_type    VARCHAR(32)  NOT NULL,
  player_uuid   CHAR(36)     NOT NULL,
  player_name   VARCHAR(32)  NOT NULL,
  to_uuid       CHAR(36)     NOT NULL,
  to_name       VARCHAR(32)  NOT NULL,
  medium        VARCHAR(32)  NULL,
  item_ref      VARCHAR(64)  NULL,
  quantity      INT          NULL,
  unit_value    INT          NULL,
  total_value   INT          NULL,
  reciprocal_of BIGINT       NULL,
  server        VARCHAR(16)  NOT NULL,
  world         VARCHAR(64)  NOT NULL,
  x             INT          NOT NULL,
  y             INT          NOT NULL,
  z             INT          NOT NULL,
  others        VARCHAR(512) NULL,
  at            TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  KEY idx_player (player_uuid, at),
  KEY idx_to     (to_uuid, at),
  KEY idx_pair   (player_uuid, to_uuid, at),
  KEY idx_when   (at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS moderation_events (
  id           BIGINT AUTO_INCREMENT PRIMARY KEY,
  event_type   VARCHAR(32)  NOT NULL,
  player_uuid  CHAR(36)     NULL,
  player_name  VARCHAR(32)  NULL,
  subject_uuid CHAR(36)     NOT NULL,
  subject_name VARCHAR(32)  NOT NULL,
  actor_kind   VARCHAR(16)  NULL,
  reason_code  VARCHAR(48)  NULL,
  automated    TINYINT(1)   NOT NULL DEFAULT 0,
  server       VARCHAR(16)  NOT NULL,
  world        VARCHAR(64)  NULL,
  x            INT          NULL,
  y            INT          NULL,
  z            INT          NULL,
  others       VARCHAR(512) NULL,
  at           TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  KEY idx_subject (subject_uuid, at),
  KEY idx_actor   (player_uuid, at),
  KEY idx_type    (event_type, at),
  KEY idx_when    (at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS watcher_meta (
  k          VARCHAR(64) PRIMARY KEY,
  v          VARCHAR(255) NOT NULL,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                        ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- ---------------------------------------------------------------------------
--  Additive migrations, for a store that predates the full surface.
--  MySQL has no ADD COLUMN IF NOT EXISTS, so the emitter checks information_schema
--  first. Run these only if the column is absent.
-- ---------------------------------------------------------------------------

ALTER TABLE `sightings` ADD COLUMN `event_type` VARCHAR(32) NOT NULL DEFAULT 'presence.enter';
ALTER TABLE `sightings` ADD COLUMN `scope_kind` VARCHAR(32) NULL;
ALTER TABLE `sightings` ADD COLUMN `duration_ms` INT NULL;
ALTER TABLE `sightings` ADD COLUMN `left_at` TIMESTAMP NULL;
ALTER TABLE `chat_events` ADD COLUMN `event_type` VARCHAR(32) NOT NULL DEFAULT 'communication.utterance';
ALTER TABLE `chat_events` ADD COLUMN `content_ref` CHAR(32) NULL;
ALTER TABLE `chat_events` ADD COLUMN `length_chars` INT NULL;
ALTER TABLE `chat_events` ADD COLUMN `recipient_uuid` CHAR(36) NULL;
ALTER TABLE `chat_events` ADD COLUMN `recipient_name` VARCHAR(32) NULL;
ALTER TABLE `session_events` ADD COLUMN `event_type` VARCHAR(32) NULL;
ALTER TABLE `session_events` ADD COLUMN `world` VARCHAR(64) NULL;
ALTER TABLE `session_events` ADD COLUMN `duration_ms` INT NULL;

-- ---------------------------------------------------------------------------
INSERT INTO watcher_meta (k, v) VALUES ('schema_version', '0.2.0')
  ON DUPLICATE KEY UPDATE v = VALUES(v);
