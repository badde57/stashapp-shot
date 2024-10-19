# stashapp-shot
Shot Boundary Detection Plugin for Stashapp

# PHash Plugin for Stashapp

This plugin performs shot boundary detection (SBD), identifying shot
boundaries, aka cut points, within a scene.

## Purpose

This is useful for creating tagged markers within a scene. Typically, the
content within a shot is consistent. It's only likely to change between shots.

## How to configure the plugin

0. Install requirements: `pip install -r requirements.txt`. Briefly, it's ffmpeg-python, stashapp-tools, torch, and their respective dependencies. This is tested with Python 3.10

1. Create a database for storing perceptual hashes:
  ```
  echo "
    CREATE TABLE shot (
      endpoint TEXT NOT NULL,
      stash_id TEXT NOT NULL,
      time_offset FLOAT NOT NULL, 
      time_duration FLOAT NOT NULL, 
      score FLOAT NOT NULL, 
      method TEXT NOT NULL, 
      UNIQUE (stash_id, time_offset, method)
    );
  " | sqlite3 /path/to/shot.sqlite

2. Update `shot.yml` to use the path to the sqlite datbase you created. In the config, it's by default:
  `  - "{pluginDir}/../shot.sqlite"`
  Change accordingly.

## How to use the plugin

In stashapp settings > tasks, under plugin tasks, find a new task labeled
`SBD scenes`. This will trigger a database-wide hashing operation. It may
take many days to complete. Don't worry about interrupting it, it only commits
hashes to its database after processing a file, so interruption won't be a
problem - you can resume quickly anytime and without losing progress.
