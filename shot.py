import os
import sys
import json
import sqlite3

METHOD = 'shot-1.0.0'

per_page = 10

try:
    import stashapi.log as log
    import stashapi.marker_parse as mp
    from stashapi.stashapp import StashInterface

    import ffmpeg
    import torch
    import os
    import sys
    sys.path.append(os.path.join(sys.path[0],'transnetv2pt'))
    from transnetv2pt import predict_video

except ModuleNotFoundError:
    print("You need to install the stashapp-tools (stashapi) python module. (CLI: pip install stashapp-tools)", file=sys.stderr)

# plugins don't start in the right directory, let's switch to the local directory
os.chdir(os.path.dirname(os.path.realpath(__file__)))

def exit_plugin(msg=None, err=None):
    if msg is None and err is None:
        msg = "plugin ended"
    output_json = {"output": msg, "error": err}
    print(json.dumps(output_json))
    sys.exit()

def catchup():
    #f = {"stash_ids": {"modifier": "NOT_NULL"}}

    f = {
            "stash_id_endpoint": {
                "modifier": "NOT_NULL",
            }
        }
#                "stash_id": {"modifier": "NOT_NULL"}
    log.info('Getting scene count.')
    count=stash.find_scenes(f=f,filter={"per_page": 1, "sort": "duration", "direction": "ASC"},get_count=True)[0]
    log.info(str(count)+' scenes to SBD.')
    i=0
    for r in range(1,count+1):
        log.info('fetching data: %s - %s %0.1f%%' % ((r - 1) * per_page,r * per_page,(i/count)*100,))
        scenes=stash.find_scenes(f=f,filter={"page":r,"per_page": 1, "sort": "duration", "direction": "ASC"})
        for s in scenes:
            if "stash_ids" not in s.keys() or len(s["stash_ids"]) != 1:
                log.error(f"Scene {s['id']} must have exactly one stash_id, skipping...")
                continue
            result = checkshot(s)
            i=i+1
            log.progress((i/count))
            #time.sleep(2)

def checkshot(scene):
    #log.info(scene)

    if len(scene['files']) != 1:
        log.error(f"Scene {s['id']} must have exactly one file, skipping...")
        return

    for file in scene['files']:
        scene_id = scene['id']
        path = file['path']
        file_id = file['id']
        fps = float(file['frame_rate'])
        dur = float(file['duration'])
        log.debug(f'processing {scene_id=}...')
        endpoint = scene['stash_ids'][0]['endpoint']
        stash_id = scene['stash_ids'][0]['stash_id']

        cur = con.cursor()
        cur.execute("SELECT COUNT(*) AS c FROM shot WHERE endpoint = ? AND stash_id = ?",(endpoint, stash_id,))
        rows = cur.fetchall()
        if len(rows) > 0:
            frame_count = int(rows[0][0])
            if frame_count > 100:
                log.debug(f"shot - skipping {scene_id=}, {frame_count=}")
                continue

        # CREATE TABLE phash( endpoint TEXT NOT NULL, stash_id TEXT NOT NULL, time_offset float not null, time_duration float not null, phash CHAR(12) NOT NULL, method TEXT NOT NULL, unique (stash_id, time_offset, method));
        scenes = predict_video(path, probs=True)
        for i, t in enumerate(scenes):
            frame_start = t[0]
            frame_end = t[1]
            frame_prob = t[2]
            time_duration = int(100 * (frame_end - frame_start) / fps) / 100
            time_offset = int(100 * frame_start / fps) / 100
            cur.execute('INSERT INTO shot (endpoint, stash_id, time_offset, time_duration, score, method) VALUES (?,?,?,?,?,?)',(endpoint, stash_id, time_offset, time_duration, frame_prob, METHOD,))
            #if frame_start % 1000 == 0:
            #    log.debug(f'phash - {scene_id=}, {file_id=}, frame: {frame_start}/{total_frames}, phash={curr_hash=}')
        # TODO insert final segment
        log.debug(f"shot - finished {scene_id=}")
        return con.commit()

def main():
    global stash
    json_input = json.loads(sys.stdin.read())
    FRAGMENT_SERVER = json_input["server_connection"]

    #log.debug(FRAGMENT_SERVER)

    stash = StashInterface(FRAGMENT_SERVER)
    PLUGIN_ARGS = False
    HOOKCONTEXT = False

    global con
    shot_db_path = sys.argv[1]
    log.info(shot_db_path)
    con = sqlite3.connect(shot_db_path)

    try:
#        PLUGIN_ARGS = json_input['args'].get("mode")
#        PLUGIN_DIR = json_input["PluginDir"]
        PLUGIN_ARGS = json_input['args']["mode"]
    except:
        pass

    if PLUGIN_ARGS:
        log.debug("--Starting Plugin 'shot'--")
        if "catchup" in PLUGIN_ARGS:
            log.info("Catching up with SBD on older files")
            catchup() #loops thru all scenes, and tag
        exit_plugin("shot plugin finished")

    try:
        HOOKCONTEXT = json_input['args']["hookContext"]
    except:
        exit_plugin("shot hook: No hook context")

    log.debug("--Starting Hook 'shot'--")


    sceneID = HOOKCONTEXT['id']
    scene = stash.find_scene(sceneID)

    results = checkshot(scene)
    con.close()
    exit_plugin(results)

main()
