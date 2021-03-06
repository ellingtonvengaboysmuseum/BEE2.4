import os
import os.path
import sys
import subprocess
import shutil
import random
from enum import Enum
from collections import defaultdict
from decimal import Decimal

from property_parser import Property
from utils import Vec
from BEE2_config import ConfigFile
import vmfLib as VLib
import utils
import voiceLine
import instanceLocs

# Configuration data extracted from VBSP_config
settings = {
    "textures":       {},
    "fizzler":        {},
    "options":        {},
    "pit":            {},
    "deathfield":     {},

    "style_vars":      defaultdict(bool),
    "has_attr":        defaultdict(bool),

    "voice_data_sp":   Property("Quotes_SP", []),
    "voice_data_coop": Property("Quotes_COOP", []),
    }

import conditions

TEX_VALVE = {
    # all the non-wall textures produced by the Puzzlemaker, and their
    # replacement keys:
    'signage/signage_exit': "overlay.exit",
    "signage/signage_overlay_arrow": "overlay.arrow",
    "signage/signage_overlay_catapult1": "overlay.catapultfling",
    "signage/signage_overlay_catapult2": "overlay.catapultland",
    "signage/shape01": "overlay.dot",
    "signage/shape02": "overlay.moon",
    "signage/shape03": "overlay.triangle",
    "signage/shape04": "overlay.cross",
    "signage/shape05": "overlay.square",
    "signage/signage_shape_circle": "overlay.circle",
    "signage/signage_shape_sine": "overlay.sine",
    "signage/signage_shape_slash": "overlay.slash",
    "signage/signage_shape_star": "overlay.star",
    "signage/signage_shape_wavy": "overlay.wavy",
    "anim_wp/framework/backpanels_cheap": "special.behind",
    "plastic/plasticwall004a": "special.pedestalside",
    "anim_wp/framework/squarebeams": "special.edge",
    "nature/toxicslime_a2_bridge_intro": "special.goo",
    "nature/toxicslime_puzzlemaker_cheap": "special.goo_cheap",
    "glass/glasswindow007a_less_shiny": "special.glass",
    "metal/metalgrate018": "special.grating",
    "effects/laserplane": "special.laserfield",
    "sky_black": "special.sky",
    }

TEX_DEFAULTS = [
    # extra default replacements we need to specially handle. These
    # have the same item so we can't store this in the regular dictionary.
    ('metal/black_floor_metal_001c', 'black.floor'),
    ('tile/white_floor_tile002a',    'white.floor'),
    ('metal/black_floor_metal_001c', 'black.ceiling'),
    ('tile/white_floor_tile002a',    'white.ceiling'),
    ('tile/white_wall_tile003a',     'white.wall'),
    ('tile/white_wall_tile003h',     'white.wall'),
    ('tile/white_wall_tile003c',     'white.2x2'),
    ('tile/white_wall_tile003f',     'white.4x4'),
    ('metal/black_wall_metal_002c',  'black.wall'),
    ('metal/black_wall_metal_002e',  'black.wall'),
    ('metal/black_wall_metal_002a',  'black.2x2'),
    ('metal/black_wall_metal_002b',  'black.4x4'),
    ('',                             'special.white'),
    ('',                             'special.black'),
    ('',                             'special.white_gap'),
    ('',                             'special.black_gap'),
    ('',                             'special.goo_wall'),

    # And these defaults have the extra scale information, which isn't
    # in the maps.
    ('0.25|signage/indicator_lights/indicator_lights_floor',
        'overlay.antline'),
    ('1|signage/indicator_lights/indicator_lights_corner_floor',
        'overlay.antlinecorner'),
    ('', 'overlay.antlinecornerfloor'),
    ('', 'overlay.antlinefloor'),
    ]


class ORIENT(Enum):
    floor = 1
    wall = 2
    ceiling = 3
    ceil = 3

WHITE_PAN = [
    "tile/white_floor_tile002a",
    "tile/white_wall_tile003a",
    "tile/white_wall_tile003h",
    "tile/white_wall_tile003c",
    "tile/white_wall_tile003f",
    ]

BLACK_PAN = [
    "metal/black_floor_metal_001c",
    "metal/black_wall_metal_002c",
    "metal/black_wall_metal_002e",
    "metal/black_wall_metal_002a",
    "metal/black_wall_metal_002b",
    ]

GOO_TEX = [
    "nature/toxicslime_a2_bridge_intro",
    "nature/toxicslime_puzzlemaker_cheap",
    ]

ANTLINES = {
    "signage/indicator_lights/indicator_lights_floor": "antline",
    "signage/indicator_lights/indicator_lights_corner_floor": "antlinecorner",
    }  # these need to be handled separately to accommodate the scale-changing

DEFAULTS = {
    "bottomless_pit":           "0",  # Convert goo into bottomless pits
    "remove_info_lighting":     "0",  # Remove the glass info_lighting ents
    "remove_pedestal_plat":     "0",  # Remove pedestal button platforms
    "remove_exit_signs":        "0",  # Remove the exit sign overlays
    "random_blackwall_scale":   "0",  # P1 style randomly sized black walls

    "fix_glass":                "0",
    "fix_portal_bump":          "0",

    "no_mid_voices":            "0",  # Remove the midpoint voice lines
    "force_fizz_reflect":       "0",  # Force fast reflections on fizzlers
    "force_brush_reflect":      "0",  # Force fast reflections on func_brushes
    "force_paint":              "0",  # Force paintinmap = 1
    "sky":                      "sky_black",  # Change the skybox
    "glass_scale":              "0.15",  # Scale of glass texture
    "grating_scale":            "0.15",  # Scale of grating texture
    "staticPan":                "NONE",  # folder for static panels
    "signInst":                 "NONE",  # adds this instance on all the signs.

    # If set, use these as the glass/grating 128x128 instances
    "glassInst":                "NONE",
    "gratingInst":              "NONE",

    "clump_wall_tex":           "0",  # Use the clumping wall algorithm
    "clump_size":               "4",  # The maximum length of a clump
    "clump_width":              "2",  # The width of a clump
    "clump_number":             "6",  # The number of clumps created
    "music_instance":           "",  # The instance for the chosen music
    "music_soundscript":        "",  # The soundscript for the chosen music
    # Default to the origin of the elevator instance - that's likely to
    # be enclosed
    "music_location_sp":        "-2000 2000 0",
    "music_location_coop":      "-2000 -2000 0",
    # BEE2 sets this to tell conditions what music is selected
    "music_id":                 "<NONE>",
    "global_pti_ents":          "",  # Instance used for pti_ents
    # Default pos is next to arrival_departure_ents
    "global_pti_ents_loc":      "-2400 -2800 0",
    # Location of the model changer instance if needed
    "model_changer_loc":        "-2400 -2800 -256",
    # The file path of the BEE2 app that generated the config
    "bee2_loc":                 "",
    }

# angles needed to ensure fizzlers are not upside-down
# (key=original, val=fixed)
FIZZLER_ANGLE_FIX = {
    "0 0 -90":    "0 180 90",
    "0 0 180":    "0 180 180",
    "0 90 0":     "0 -90 0",
    "0 90 -90":   "0 -90 90",
    "0 180 -90":  "0 0 90",
    "0 -90 -90":  "0 90 90",
    "90 180 0":   "-90 0 0",
    "90 -90 0":   "-90 90 0",
    "-90 180 0":  "90 0 0",
    "-90 -90 0":  "90 90 0",
    }

TEX_FIZZLER = {
    "effects/fizzler_center": "center",
    "effects/fizzler_l": "left",
    "effects/fizzler_r": "right",
    "effects/fizzler": "short",
    "tools/toolsnodraw": "nodraw",
    }

FIZZ_OPTIONS = {
    "scanline": "0",
    }

BEE2_config = None

# A list of sucessful AddGlobal commands, so we can prevent adding the same
# instance twice.
global_instances = []

##################
# UTIL functions #
##################


def get_opt(name):
    return settings['options'][name.casefold()]


def get_bool_opt(name, default=False):
    return utils.conv_bool(get_opt(name), default)


def get_tex(name):
    if name in settings['textures']:
        return random.choice(settings['textures'][name])
    else:
        raise Exception('No texture "' + name + '"!')


def alter_mat(face, seed=None):
    """Randomise the texture used for a face, based on configured textures.

    This uses the TEX_VALVE dict to identify the kind of texture, but
    uses the face orientation to determine the wall direction - the
    PeTI often uses textures on the wrong sides for various reasons.
    """
    mat = face.mat.casefold()
    if seed:
        random.seed(seed)

    if mat in TEX_VALVE:  # should we convert it?
        face.mat = get_tex(TEX_VALVE[mat])
        return True
    elif mat in BLACK_PAN or mat in WHITE_PAN:
        surf_type = 'white' if mat in WHITE_PAN else 'black'
        orient = get_face_orient(face)
        if orient == ORIENT.wall:
            if (mat == 'metal/black_wall_metal_002b' or
                    mat == 'tile/white_wall_tile_003f'):
                orient = '4x4'
            elif (mat == 'metal/black_wall_metal_002a' or
                    mat == 'tile/white_wall_tile003c'):
                orient = '2x2'
            else:
                orient = 'wall'
        elif orient == ORIENT.floor:
            orient = 'floor'
        elif orient == ORIENT.ceiling:
            orient = 'ceiling'
        face.mat = get_tex(surf_type + '.' + orient)
        return True
    elif mat in TEX_FIZZLER:
        face.mat = settings['fizzler'][TEX_FIZZLER[mat]]
    else:
        return False

##################
# MAIN functions #
##################


def load_settings():
    """Load in all our settings from vbsp_config."""
    global BEE2_config
    try:
        with open("bee2/vbsp_config.cfg") as config:
            conf = Property.parse(config, 'bee2/vbsp_config.cfg')
    except FileNotFoundError:
        conf = Property(None, [])
        # All the find_all commands will fail, and we will use the defaults.

    tex_defaults = list(TEX_VALVE.items()) + TEX_DEFAULTS

    for item, key in tex_defaults:  # collect textures from config
        cat, name = key.split(".")
        value = [prop.value for prop in conf.find_all('textures', cat, name)]
        if len(value) == 0:
            settings['textures'][key] = [item]
        else:
            settings['textures'][key] = value

    # get misc options
    for option_block in conf.find_all('options'):
        for opt in option_block:
            settings['options'][opt.name.casefold()] = opt.value
    for key, default in DEFAULTS.items():
        if key.casefold() not in settings['options']:
            settings['options'][key.casefold()] = default

    for item, key in TEX_FIZZLER.items():
        settings['fizzler'][key] = item

    for key, item in FIZZ_OPTIONS.items():
        settings['fizzler'][key] = item

    for fizz_opt in conf.find_all('fizzler'):
        for item, key in TEX_FIZZLER.items():
            settings['fizzler'][key] = fizz_opt[key, settings['fizzler'][key]]

        for key, item in FIZZ_OPTIONS.items():
            settings['fizzler'][key] = fizz_opt[key, settings['fizzler'][key]]

    for quote_block in conf.find_all("quotes_sp"):
        settings['voice_data_sp'] += quote_block.value

    for quote_block in conf.find_all("quotes_coop"):
        settings['voice_data_coop'] += quote_block.value

    for stylevar_block in conf.find_all('stylevars'):
        for var in stylevar_block:
            settings['style_vars'][
                var.name.casefold()] = utils.conv_bool(var.value)

    for cond in conf.find_all('conditions', 'condition'):
        conditions.add(cond)

    if get_bool_opt('bottomless_pit'):
        pit = conf.find_key("bottomless_pit", [])
        settings['pit'] = {
            'tex_goo': pit['goo_tex', 'nature/toxicslime_a2_bridge_intro'],
            'tex_sky': pit['sky_tex', 'tools/toolsskybox'],
            'should_tele': utils.conv_bool(pit['teleport', '0']),
            'tele_dest': pit['tele_target', '@goo_targ'],
            'tele_ref': pit['tele_ref', '@goo_ref'],
            'off_x': utils.conv_int(pit['off_x', '0']),
            'off_y': utils.conv_int(pit['off_y', '0']),
            'height': utils.conv_int(pit['max_height', '386'], 386),
            'side': [prop.value for prop in pit.find_all("side_inst")],
            'pillar': [prop.value for prop in pit.find_all("pillar_inst")],
            }
        if len(settings['pit']['side']) == 0:
            settings['pit']['side'] = [""]

        if len(settings['pit']['pillar']) == 0:
            settings['pit']['pillar'] = [""]

    if get_opt('BEE2_loc') != '':
        BEE2_config = ConfigFile(
            'config/compile.cfg',
            root=get_opt('BEE2_loc'),
        )
    else:
        BEE2_config = ConfigFile(None)

    instanceLocs.load_conf()

    utils.con_log(settings['pit'])
    utils.con_log("Settings Loaded!")


def load_map(map_path):
    global VMF
    with open(map_path) as file:
        utils.con_log("Parsing Map...")
        props = Property.parse(file, map_path)
    file.close()
    VMF = VLib.VMF.parse(props)
    utils.con_log("Parsing complete!")


def add_voice(voice_config, mode):
    print(mode)
    if mode == 'COOP':
        utils.con_log('Adding Coop voice lines!')
        data = settings['voice_data_coop']
    elif mode == 'SP':
        utils.con_log('Adding Singleplayer voice lines!')
        data = settings['voice_data_sp']
    else:
        return

    voiceLine.add_voice(
        voice_data=data,
        has_items=settings['has_attr'],
        style_vars_=settings['style_vars'],
        vmf_file=VMF,
        timer_config=voice_config,
        mode=mode,
        )


def get_map_info():
    """Determine various attributes about the map.

    - SP/COOP status
    - if in preview mode
    - timer values for entry/exit corridors
    """
    game_mode = 'ERR'
    is_preview = 'ERR'

    # Timer_delay values for the entry/exit corridors, needed for quotes
    voice_timer_pos = {}

    inst_files = set()  # Get a set of every instance in the map.
    file_coop_exit = instanceLocs.resolve('[coopExit]')
    file_sp_exit = instanceLocs.resolve('[spExit]')
    file_sp_entry = instanceLocs.resolve('[spEntry]')
    file_coop_corr = instanceLocs.resolve('[coopCorr]')
    file_sp_entry_corr = instanceLocs.resolve('[spEntryCorr]')
    file_sp_exit_corr = instanceLocs.resolve('[spExitCorr]')
    file_obs = instanceLocs.resolve('<ITEM_OBSERVATION_ROOM>')
    file_coop_entry = instanceLocs.resolve('[coopEntry]')

    for item in VMF.by_class['func_instance']:
        file = item['file'].casefold()
        if file in file_coop_exit:
            game_mode = 'COOP'
        elif file in file_sp_exit:
            game_mode = 'SP'
        elif file in file_sp_entry:
            is_preview = not utils.conv_bool(item.fixup['no_player_start'])
            game_mode = 'SP'
        elif file in file_coop_corr:
            is_preview = not utils.conv_bool(item.fixup['no_player_start'])
            voice_timer_pos['exit'] = (
                item.fixup['timer_delay', '0']
                )
            game_mode = 'COOP'
        elif file in file_sp_entry_corr:
            voice_timer_pos['entry'] = (
                item.fixup['timer_delay', '0']
                )
            is_preview = not utils.conv_bool(item.fixup['no_player_start'])
        elif file in file_sp_exit_corr:
            voice_timer_pos['exit'] = (
                item.fixup['timer_delay', '0']
                )
        elif file in file_coop_entry:
            voice_timer_pos['entry'] = (
                item.fixup['timer_delay', '0']
                )
        elif file in file_obs:
            voice_timer_pos['obs'] = (
                item.fixup['timer_delay', '0']
                )

        inst_files.add(item['file'])

    utils.con_log("Game Mode: " + game_mode)
    utils.con_log("Is Preview: " + str(is_preview))

    if game_mode == 'ERR':
        raise Exception(
            'Unknown game mode - Map missing exit room!'
        )
    if is_preview == 'ERR':
        raise Exception(
            "Can't determine if preview is enabled "
            '- Map likely missing entry room!'
        )

    return is_preview, game_mode, voice_timer_pos, inst_files


def calc_rand_seed():
    """Use the ambient light entities to create a map seed.

     This ensures textures remain the same when the map is recompiled.
    """
    amb_light = instanceLocs.resolve('<ITEM_POINT_LIGHT>')
    lst = [
        inst['targetname'] or '-'  # If no targ
        for inst in
        VMF.by_class['func_instance']
        if inst['file'].casefold() in amb_light
        ]
    if len(lst) == 0:
        # Very small maps won't have any ambient light entities at all.
        return 'SEED'
    else:
        return '|'.join(lst)


def make_bottomless_pit(solids):
    """Transform all the goo pits into bottomless pits."""
    tex_sky = settings['pit']['tex_sky']
    teleport = settings['pit']['should_tele']
    tele_ref = settings['pit']['tele_ref']
    tele_dest = settings['pit']['tele_dest']
    tele_off_x = settings['pit']['off_x']+64
    tele_off_y = settings['pit']['off_y']+64
    for solid, wat_face in solids:
        wat_face.mat = tex_sky
        for vec in wat_face.planes:
            vec.z = float(Decimal(vec.z) - Decimal('95.5'))
            # subtract 95.5 from z axis to make it 0.5 units thick
            # we do the calc with Decimal to ensure precision
    pit_height = settings['pit']['height']

    # To figure out what positions need edge pieces, we use a dict
    # indexed by XY tuples. The four Nones match the NSEW directions.
    # For each trigger, we loop through the grid points it's in. We
    # set all the center parts to None, but set the 4 neighbouring
    # blocks if they aren't None.
    # If a value = None, it is occupied by goo.
    edges = defaultdict(lambda: [None, None, None, None])
    dirs = [
        # index, x, y, angles
        (0, 0, 128,  '0 270 0'),  # North
        (1, 0, -128, '0 90 0'),  # South
        (2, 128, 0,  '0 180 0'),  # East
        (3, -128, 0, '0 0 0')  # West
    ]
    if teleport:
        # transform the skybox physics triggers into teleports to move cubes
            # into the skybox zone
        for trig in VMF.by_class['trigger_multiple']:
            if trig['wait'] == '0.1':
                bbox_min, bbox_max = trig.get_bbox()
                origin = (bbox_min + bbox_max)/2
                """:type :Vec"""
                # We only modify triggers which are below the given z-index
                if origin.z < pit_height:
                    trig['classname'] = 'trigger_teleport'
                    trig['spawnflags'] = '4106'  # Physics and npcs
                    trig['landmark'] = tele_ref
                    trig['target'] = tele_dest
                    trig.outputs.clear()
                    for x in range(int(bbox_min.x), int(bbox_max.x), 128):
                        for y in range(int(bbox_min.y), int(bbox_max.y), 128):
                            # Remove the pillar from the center of the item
                            edges[x, y] = None
                            for i, xoff, yoff, angle in dirs:
                                side = edges[x+xoff, y+yoff]
                                if side is not None:
                                    side[i] = origin.z - 13

                    # The triggers are 26 high, make them 10 units thick to
                    # make it harder to see the teleport
                    for side in trig.sides():
                        for plane in side.planes:
                            if plane.z > origin.z:
                                plane.z -= 16

    side_opts = settings['pit']['side']
    pillar_opts = settings['pit']['pillar']

    utils.con_log('Pillar:', pillar_opts)
    for (x, y), mask in edges.items():
        if mask is None:
            continue
        for i, xoff, yoff, angle in dirs:
            if mask[i] is None:
                continue
            random.seed(str(x) + str(y) + angle)
            file = random.choice(side_opts)
            if file != '':
                VMF.create_ent(
                    classname='func_instance',
                    file=file,
                    targetname='goo_side',
                    origin='{!s} {!s} {!s}'.format(
                        x+tele_off_x,
                        y+tele_off_y,
                        mask[i],
                        ),
                    angles=angle
                ).make_unique()
        random.seed(str(x) + str(y) + '-pillar')
        file = random.choice(pillar_opts)
        if file != '':
            VMF.create_ent(
                classname='func_instance',
                file=file,
                targetname='goo_side',
                angles='0 0 0',
                origin='{!s} {!s} {!s}'.format(
                    x+tele_off_x,
                    y+tele_off_y,
                    max(
                        x
                        for x in mask
                        if x is not None
                    ),
                ),
            ).make_unique()


def change_goo_sides():
    """Replace the textures on the sides of goo with specific ones.

    """
    if settings['textures']['special.goo_wall'] == ['']:
        return
    utils.con_log("Changing goo sides...")
    face_dict = {}
    for solid in VMF.iter_wbrushes(world=True, detail=False):
        for face in solid:
            if face.mat.casefold() != 'tools/toolsnodraw':
                # Don't record the goo textured brushes
                x, y, z = face.get_origin()
                face_dict[x, y, z] = face

    dirs = [
        # x, y, z
        (0, 64, 0),  # North
        (0, -64, 0),  # South
        (64, 0, 0),  # East
        (-64, 0, 0),  # West
        (0, 0, -64),  # Down
    ]
    for trig in VMF.by_class['trigger_multiple']:
        if trig['wait'] != '0.1':
            continue
        bbox_min, bbox_max = trig.get_bbox()
        z = int(bbox_min.z + 64)
        for x in range(int(bbox_min.x)+64, int(bbox_max.x), 128):
            for y in range(int(bbox_min.y)+64, int(bbox_max.y), 128):
                for xoff, yoff, zoff in dirs:
                    try:
                        face = face_dict[x+xoff, y+yoff, z+zoff]
                    except KeyError:
                        pass
                    else:
                        utils.con_log('Success: ', face.mat.casefold())
                        if (
                                face.mat.casefold() in BLACK_PAN or
                                face.mat.casefold() == 'tools/toolsnodraw'
                                ):
                            face.mat = get_tex('special.goo_wall')
    utils.con_log("Done!")


def change_brush():
    """Alter all world/detail brush textures to use the configured ones."""
    utils.con_log("Editing Brushes...")
    glass_inst = get_opt('glassInst')
    glass_scale = get_opt('glass_scale')
    is_bottomless = get_bool_opt('bottomless_pit')

    # Check the clump algorithm has all its arguements
    can_clump = (get_bool_opt("clump_wall_tex") and
                 get_opt("clump_size").isnumeric() and
                 get_opt("clump_width").isnumeric() and
                 get_opt("clump_number").isnumeric())

    if utils.conv_bool(get_opt('remove_pedestal_plat')):
        # Remove the pedestal platforms
        for ent in VMF.by_class['func_detail']:
            for side in ent.sides():
                if side.mat.casefold() == 'plastic/plasticwall004a':
                    VMF.remove_ent(ent)
                    break  # Skip to next entity

    if is_bottomless:
        pit_solids = []
        pit_height = settings['pit']['height']
        pit_goo_tex = settings['pit']['tex_goo']

    if glass_inst == "NONE":
        glass_inst = None

    for solid in VMF.iter_wbrushes(world=True, detail=True):
        is_glass = False
        for face in solid:
            is_glass = False
            if face.mat.casefold() in GOO_TEX:
                # Force this voice attribute on, since conditions can't
                # detect goo pits / bottomless pits
                settings['has_attr']['goo'] = True
                if is_bottomless:
                    if face.planes[2].z < pit_height:
                        settings['has_attr']['bottomless_pit'] = True
                        pit_solids.append((solid, face))
                    else:
                        face.mat = pit_goo_tex
            if face.mat.casefold() == "glass/glasswindow007a_less_shiny":
                split_u = face.uaxis.split(" ")
                split_v = face.vaxis.split(" ")
                split_u[-1] = glass_scale  # apply the glass scaling option
                split_v[-1] = glass_scale
                face.uaxis = " ".join(split_u)
                face.vaxis = " ".join(split_v)
                settings['has_attr']['glass'] = True
                is_glass = True
        if is_glass and glass_inst is not None:
            inst = find_glass_inst(solid.get_origin())
            if inst:
                inst['file'] = glass_inst
    if is_bottomless:
        utils.con_log('Creating Bottomless Pits!')
        make_bottomless_pit(pit_solids)
        utils.con_log('Done!')

    if can_clump:
        clump_walls()
    else:
        random_walls()


def find_glass_inst(origin):
    """Find the glass instance placed in the specified location."""
    loc = Vec(
        origin.x//128 * 128 + 64,
        origin.y//128 * 128 + 64,
        origin.z//128 * 128 + 64,
        )
    direction = (origin-loc).norm()
    ang_vec = Vec(-1, 0, 0)  # The brush parts are on this side!
    loc_str = loc.join(' ')
    gls_file = instanceLocs.resolve('[glass_128]')
    for inst in VMF.by_class['func_instance']:
        if inst['origin', ''] == loc_str and inst['file', ''] in gls_file:
            # (45, 45, 45) will never match any of the directions, so we
            # effectively skip instances without angles
            inst_ang = Vec.from_str(inst['angles', ''], 45, 45, 45)
            rot = ang_vec.rotate(inst_ang.x, inst_ang.y, inst_ang.z)
            print(rot, direction)
            if round(rot) == direction:
                return inst

    # TODO - make this actually work
    return None


def face_seed(face):
    """Create a seed unique to this brush face.

    This is the same regardless of side direction.
    """
    origin = face.get_origin()
    for axis in "xyz":
        if origin[axis] % 128 < 2:
            origin[axis] //= 128  # This side
        else:
            origin[axis] = origin[axis] // 128 + 64
    return origin.join()


def random_walls():
    """The original wall style, with completely randomised walls."""
    scale_walls = get_bool_opt("random_blackwall_scale")
    for solid in VMF.iter_wbrushes(world=True, detail=True):
        for face in solid:
            orient = get_face_orient(face)
            # Only modify black walls and ceilings
            if (scale_walls and
                    face.mat.casefold() in BLACK_PAN and
                    orient is not ORIENT.floor):
                random.seed(face_seed(face) + '_SCALE_VAL')
                # randomly scale textures to achieve the P1 multi-sized
                #  black tile look without custom textues
                scale = random.choice(("0.25", "0.5", "1"))
                split = face.uaxis.split(" ")
                split[-1] = scale
                face.uaxis = " ".join(split)

                split = face.vaxis.split(" ")
                split[-1] = scale
                face.vaxis = " ".join(split)
            alter_mat(face, face_seed(face))


def clump_walls():
    """A wall style where textures are used in small groups near each other.

    This replicates the Old Aperture maps, which are cobbled together
    from many different materials.
    """
    # For this, we ignore all of Valve's wall textures.
    # We then start making clumps.
    # These are 2x2x4 maximum rectangular areas (configurable), which all get
    #  the same texture. We don't overwrite previously-set ones though.
    # After that, we fill in any unset textures with the white/black_gap ones.
    # This makes it look like those areas were patched up
    # The floor and ceiling are made normally.

    # Additionally, we are able to nodraw all attached faces.
    walls = {}

    # we keep a list for the others, so we can nodraw them if needed
    others = {}
    for solid in VMF.iter_wbrushes(world=True, detail=True):
        # first build a dict of all textures and their locations...
        for face in solid:
            mat = face.mat.casefold()
            if face.mat in (
                    'glass/glasswindow007a_less_shiny',
                    'metal/metalgrate018',
                    'anim_wp/framework/squarebeams',
                    'tools/toolsnodraw',
                    ):
                # These textures aren't always on grid, ignore them..
                alter_mat(face)
                continue

            if face.mat in GOO_TEX:
                # For goo textures, don't add them to the dicts
                # or floors will be nodrawed.
                alter_mat(face)
                break

            origin = face.get_origin().as_tuple()
            orient = get_face_orient(face)
            if orient is ORIENT.wall:
                # placeholder to indicate these can be replaced.
                if mat in WHITE_PAN:
                    face.mat = "WHITE"
                elif mat in BLACK_PAN:
                    face.mat = "BLACK"
                if origin in walls:
                    # The only time two textures will be in the same
                    # place is if they are covering each other -
                    # nodraw them both and ignore them
                    face.mat = "tools/toolsnodraw"
                    walls[origin].mat = "tools/toolsnodraw"
                    del walls[origin]
                else:
                    walls[origin] = face
            else:
                if origin in others:
                    # The only time two textures will be in the same
                    # place is if they are covering each other - delete
                    #  them both.
                    face.mat = "tools/toolsnodraw"
                    others[origin].mat = "tools/toolsnodraw"
                    del others[origin]
                else:
                    others[origin] = face
                    alter_mat(face, face_seed(face))

    todo_walls = len(walls)  # number of walls un-edited
    clump_size = int(get_opt("clump_size"))
    clump_wid = int(get_opt("clump_width"))
    clump_numb = (todo_walls // clump_size) * int(get_opt("clump_number"))
    wall_pos = sorted(list(walls.keys()))
    random.seed(MAP_SEED)
    for _ in range(clump_numb):
        pos = random.choice(wall_pos)
        wall_type = walls[pos].mat
        state = random.getstate()  # keep using the map_seed for the clumps
        if wall_type == "WHITE" or wall_type == "BLACK":
            random.seed(pos)
            pos_min = [0, 0, 0]
            pos_max = [0, 0, 0]
            # these are long strips extended in one direction
            direction = random.randint(0, 2)
            for i in range(3):
                if i == direction:
                    pos_min[i] = int(
                        pos[i] - random.randint(0, clump_size) * 128)
                    pos_max[i] = int(
                        pos[i] + random.randint(0, clump_size) * 128)
                else:
                    pos_min[i] = int(
                        pos[i] - random.randint(0, clump_wid) * 128)
                    pos_max[i] = int(
                        pos[i] + random.randint(0, clump_wid) * 128)

            tex = get_tex(wall_type.lower() + '.wall')
            # Loop though all these grid points, and set to the given
            # texture if they have the same wall type
            for x in range(pos_min[0], pos_max[0], 128):
                for y in range(pos_min[1], pos_max[1], 128):
                    for z in range(pos_min[2], pos_max[2], 128):
                        if (x, y, z) in walls:
                            side = walls[x, y, z]
                            if side.mat == wall_type:
                                side.mat = tex
        # Return to the map_seed state.
        random.setstate(state)

    for pos, face in walls.items():
        random.seed(pos)
        # We missed these ones!
        if face.mat == "WHITE":
            # Allow using special textures for these, to fill in gaps.
            if not get_tex("special.white_gap") == "":
                face.mat = get_tex("special.white_gap")
            else:
                face.mat = get_tex("white.wall")
        elif face.mat == "BLACK":
            if not get_tex("special.black_gap") == "":
                face.mat = get_tex("special.black_gap")
            else:
                face.mat = get_tex("black.wall")
        else:
            alter_mat(face, seed=pos)


def get_face_orient(face):
    """Determine the orientation of an on-grid face."""
    if face.planes[0]['z'] == face.planes[1]['z'] == face.planes[2]['z']:
        if face.planes[0]['y'] < face.planes[2]['y']:
            return ORIENT.ceiling
        else:
            return ORIENT.floor
    else:
        return ORIENT.wall


def set_antline_mat(over, mat, raw_mat=False):
    """Set the material on an overlay to the given value, applying options.

    If raw_mat is set to 1, use the given texture directly.
    The material is split into 3 parts, separated by '|':
    - Scale: the u-axis width of the material, used for clean antlines.
    - Material: the material
    - Static: if 'static', the antline will lose the targetname. This
      makes it non-dynamic, and removes the info_overlay_accessor
      entity fromt the compiled map.
    If only 2 parts are given, the overlay is assumed to be dynamic.
    If one part is given, the scale is assumed to be 0.25
    """
    if not raw_mat:
        if get_tex('overlay.' + mat + 'floor') != '':
            # For P1 style, check to see if the antline is on the floor or
            # walls.
            ang = Vec.from_str(over['angles'])
            direction = round(Vec(0, 0, 1).rotate(ang.x, ang.y, ang.z))
            utils.con_log('Ant dir: ', over['angles'], direction)
            if direction == Vec(0, 0, 1) or direction == Vec(0, 0, -1):
                mat += 'floor'
                utils.con_log('Floor!')

        mat = get_tex('overlay.' + mat)

    mat = mat.split('|')
    if len(mat) == 2:
        # rescale antlines if needed
        over['endu'], over['material'] = mat
    elif len(mat) == 3:
        over['endu'], over['material'], static = mat
        if static == 'static':
            # If specified, remove the targetname so the overlay
            # becomes static.
            over['targetname'] = ''
    else:
        over['material'] = mat
        over['endu'] = '0.25'


def change_overlays():
    """Alter the overlays."""
    utils.con_log("Editing Overlays...")
    sign_inst = get_opt('signInst')
    if sign_inst == "NONE":
        sign_inst = None
    for over in VMF.by_class['info_overlay']:
        if (over['targetname'] == 'exitdoor_stickman' or
                over['targetname'] == 'exitdoor_arrow'):
            if get_bool_opt("remove_exit_signs"):
                # Some styles have instance-based ones, remove the
                # originals if needed to ensure it looks nice.
                VMF.remove_ent(over)
                continue  # Break out, to make sure the instance isn't added
            else:
                # blank the targetname, so we don't get the
                # useless info_overlay_accessors for these signs.
                del over['targetname']

        if over['material'].casefold() in TEX_VALVE:
            sign_type = TEX_VALVE[over['material'].casefold()]
            if sign_inst is not None:
                new_inst = VMF.create_ent(
                    classname='func_instance',
                    origin=over['origin'],
                    angles=over['angles', '0 0 0'],
                    file=sign_inst,
                )
                new_inst.fixup['mat'] = sign_type.replace('overlay.', '')

            over['material'] = get_tex(sign_type)
        if over['material'].casefold() in ANTLINES:
            set_antline_mat(over, ANTLINES[over['material'].casefold()])


def change_trig():
    """Check the triggers and fizzlers."""
    utils.con_log("Editing Triggers...")
    for trig in VMF.by_class['trigger_portal_cleanser']:
        for side in trig.sides():
            alter_mat(side)
        target = trig['targetname', '']
        # Change this so the base instance can directly modify the brush.
        if target.endswith('_brush'):
            trig['targetname'] = target[:-6] + '-br_fizz'
        trig['useScanline'] = settings["fizzler"]["scanline"]
        trig['drawInFastReflection'] = get_opt("force_fizz_reflect")

    for trig in VMF.by_class['trigger_hurt']:
        target = trig['targetname', '']
        # Change this so the base instance can directly modify the brush.
        if target.endswith('_brush'):
            trig['targetname'] = target[:-6] + '-br_hurt'


def add_extra_ents(mode):
    """Add the various extra instances to the map."""
    utils.con_log("Adding Music...")
    if mode == "COOP":
        loc = get_opt('music_location_coop')
    else:
        loc = get_opt('music_location_sp')

    sound = get_opt('music_soundscript')
    inst = get_opt('music_instance')
    if sound != '':
        VMF.create_ent(
            classname='ambient_generic',
            spawnflags='17',  # Looping, Infinite Range, Starts Silent
            targetname='@music',
            origin=loc,
            message=sound,
            health='10',  # Volume
            )

    if inst != '':
        VMF.create_ent(
            classname='func_instance',
            targetname='music',
            angles='0 0 0',
            origin=loc,
            file=inst,
            fixup_style='0',
            )
    pti_file = get_opt("global_pti_ents")
    pti_loc = get_opt("global_pti_ents_loc")
    if pti_file != '':
        utils.con_log('Adding Global PTI Ents')
        global_pti_ents = VMF.create_ent(
            classname='func_instance',
            targetname='global_pti_ents',
            angles='0 0 0',
            origin=pti_loc,
            file=pti_file,
            fixup_style='0',
            )
        has_cave = utils.conv_bool(
            settings['style_vars'].get('multiversecave', '1')
        )
        global_pti_ents.fixup[
            'disable_pti_audio'
            ] = utils.bool_as_int(not has_cave)

    model_changer_loc = get_opt('model_changer_loc')
    chosen_model = BEE2_config.get_val('General', 'player_model', 'PETI')
    # We don't change the player model in Coop, or if Bendy is selected.
    if mode == 'SP' and chosen_model != 'PETI' and model_changer_loc != '':
        VMF.create_ent(
            classname='func_instance',
            targetname='model_changer',
            angles='0 0 0',
            origin=model_changer_loc,
            file='instances/BEE2/logic/model_changer/' + chosen_model + '.vmf',
            fixup_style='0',
        )


def change_func_brush():
    """Edit func_brushes."""
    utils.con_log("Editing Brush Entities...")
    grating_inst = get_opt("gratingInst")
    grating_scale = get_opt("grating_scale")

    if grating_inst == "NONE":
        grating_inst = None
    for brush in (
            VMF.by_class['func_brush'] |
            VMF.by_class['func_door_rotating']
            ):
        brush['drawInFastReflection'] = get_opt("force_brush_reflect")
        parent = brush['parentname', '']
        brush_type = ""

        target = brush['targetname', '']
        # Fizzlers need their custom outputs.
        # Change this so the base instance can directly modify the brush.
        if target.endswith('_brush'):
            brush['targetname'] = target[:-6] + '-br_brush'

        # Func_brush/func_rotating (for angled panels and flip panels)
        # often use different textures, so let the style do that.

        is_grating = False
        delete_brush = False
        for side in brush.sides():
            if (side.mat.casefold() == "anim_wp/framework/squarebeams" and
                    "special.edge" in settings['textures']):
                side.mat = get_tex("special.edge")
            elif side.mat.casefold() in WHITE_PAN:
                brush_type = "white"
                if not get_tex("special.white") == "":
                    side.mat = get_tex("special.white")
                elif not alter_mat(side):
                    side.mat = get_tex("white.wall")
            elif side.mat.casefold() in BLACK_PAN:
                brush_type = "black"
                if not get_tex("special.black") == "":
                    side.mat = get_tex("special.black")
                elif not alter_mat(side):
                    side.mat = get_tex("black.wall")
            else:
                if side.mat.casefold() == 'metal/metalgrate018':
                    is_grating = True
                    split_u = side.uaxis.split(" ")
                    split_v = side.vaxis.split(" ")
                    split_u[-1] = grating_scale  # apply the grtating
                    split_v[-1] = grating_scale  # scaling option
                    side.uaxis = " ".join(split_u)
                    side.vaxis = " ".join(split_v)
                alter_mat(side)  # for gratings, laserfields and some others

            # The style blanked the material, so delete the brush
            if side.mat == '':
                delete_brush = True
                break

        if delete_brush:
            VMF.remove_ent(brush)
            continue

        if is_grating and grating_inst is not None:
            settings['has_attr']['grating'] = True
            inst = find_glass_inst(brush.get_origin())
            if inst:
                inst['file'] = grating_inst
        if "-model_arms" in parent:  # is this an angled panel?:
            # strip only the model_arms off the end
            targ = '-'.join(parent.split("-")[:-1])
            for ins in (
                    VMF.by_class['func_instance'] &
                    VMF.by_target[targ]
                    ):
                if make_static_pan(ins, brush_type):
                    # delete the brush, we don't want it if we made a static one
                    VMF.remove_ent(brush)
                else:
                    brush['targetname'] = brush['targetname'].replace(
                        '_panel_top',
                        '-brush',
                        )


def make_static_pan(ent, pan_type):
    """Convert a regular panel into a static version.

    This is done to save entities and improve lighting."""
    if get_opt("staticPan") == "NONE":
        return False  # no conversion allowed!

    angle = "00"
    if ent.fixup['animation'] is not None:
        # the 5:7 is the number in "ramp_45_deg_open"
        angle = ent.fixup['animation'][5:7]
    if ent.fixup['start_deployed'] == "0":
        angle = "00"  # different instance flat with the wall
    if ent.fixup['connectioncount', '0'] != "0":
        return False
    # something like "static_pan/45_white.vmf"
    ent["file"] = get_opt("staticPan") + angle + "_" + pan_type + ".vmf"
    return True


def make_static_pist(ent):
    """Convert a regular piston into a static version.

    This is done to save entities and improve lighting."""
    if get_opt("staticPan") == "NONE":
        return False  # no conversion allowed!

    print("Trying to make static...")
    bottom_pos = ent.fixup['bottom_level', '-1']

    if (ent.fixup['connectioncount', '0'] != "0" or
            ent.fixup['disable_autodrop'] != "0"):  # can it move?
        if int(bottom_pos) > 0:
            # The piston doesn't go fully down, use alt instances.
            ent['file'] = ent['file'][:-4] + "_" + bottom_pos + ".vmf"
    else:  # we are static
        ent['file'] = (
            get_opt("staticPan") + "pist_"
            + (
                ent.fixup['top_level', '1']
                if utils.conv_bool(ent.fixup['start_up'], False)
                else bottom_pos
                )
            + ".vmf"
            )
        # something like "static_pan/pist_3.vmf"
    return True


def change_ents():
    """Edit misc entities."""
    utils.con_log("Editing Other Entities...")
    if get_bool_opt("remove_info_lighting"):
        # Styles with brush-based glass edges don't need the info_lighting,
        # delete it to save ents.
        for ent in VMF.by_class['info_lighting']:
            ent.remove()
    for auto in VMF.by_class['logic_auto']:
        # Remove all the logic_autos that set attachments, we can
        # replicate this in the instance
        for out in auto.outputs:
            if 'panel_top' in out.target:
                VMF.remove_ent(auto)


def fix_inst():
    """Fix some different bugs with instances, especially fizzler models.

    """
    clear_pan_file = instanceLocs.resolve('<ITEM_PANEL_CLEAR>')
    pist_plat_file = instanceLocs.resolve('<ITEM_PISTON_PLAT>')

    utils.con_log("Editing Instances...")
    for inst in VMF.by_class['func_instance']:
        # Fizzler model names end with this special string
        if ("_modelStart" in inst['targetname', ''] or
                "_modelEnd" in inst['targetname', '']):

            # strip off the extra numbers on the end, so fizzler
            # models recieve inputs correctly (Valve bug!)
            if "_modelStart" in inst['targetname', '']:

                inst['targetname'] = (
                    inst['targetname'].split("_modelStart")[0] +
                    "_modelStart"
                    )
            else:
                inst['targetname'] = (
                    inst['targetname'].split("_modelEnd")[0] +
                    "_modelEnd"
                    )

            # one side of the fizzler models are rotated incorrectly
            # (upsidown), fix that...
            if inst['angles'] in FIZZLER_ANGLE_FIX:
                inst['angles'] = FIZZLER_ANGLE_FIX[inst['angles']]

        elif "ccflag_comball_base" in inst['file', '']:  # Rexaura Flux Fields
            # find the triggers that match this entity and mod them
            for trig in VMF.iter_ents(
                    classname='trigger_portal_cleanser',
                    targetname=inst['targetname'] + "_brush",
                    ):
                for side in trig.sides():
                    side.mat = "tools/toolstrigger"

                # get rid of the _, allowing direct control from the instance.
                trig['targetname'] = inst['targetname'] + "-trigger"
                trig['classname'] = "trigger_multiple"
                trig["filtername"] = "@filter_pellet"
                trig["wait"] = "0.1"
                trig['spawnflags'] = "72"  # Physics Objects, Everything
                # generate the output that triggers the pellet logic.
                trig.add_out(VLib.Output(
                    "OnStartTouch",
                    inst['targetname'] + "-branch_toggle",
                    "FireUser1",
                    ))

            inst.outputs.clear()  # All the original ones are junk, delete them!

            for in_out in VMF.iter_ents_tags(
                    vals={
                        'classname': 'func_instance',
                        'origin': inst['origin'],
                        'angles': inst['angles'],
                        },
                    tags={
                        'file': 'ccflag_comball_out',
                        }
                    ):
                # Find the instance to use for output and add the
                # commands to trigger its logic
                inst.add_out(VLib.Output(
                    "OnUser1",
                    in_out['targetname'],
                    "FireUser1",
                    inst_in='in',
                    inst_out='out',
                    ))
                inst.add_out(VLib.Output(
                    "OnUser2",
                    in_out['targetname'],
                    "FireUser2",
                    inst_in='in',
                    inst_out='out',
                    ))

        elif inst['file'] in clear_pan_file:
            # white/black are found via the func_brush
            make_static_pan(inst, "glass")
        elif inst['file'] in pist_plat_file:
            make_static_pist(inst)  # try to convert to static piston


def fix_worldspawn():
    """Adjust some properties on WorldSpawn."""""
    utils.con_log("Editing WorldSpawn")
    if VMF.spawn['paintinmap'] != '1':
        # if PeTI thinks there should be paint, don't touch it
        VMF.spawn['paintinmap'] = get_opt('force_paint')
    VMF.spawn['skyname'] = get_tex("special.sky")


def save(path):
    """Save the modified map back to the correct location.
    """
    utils.con_log("Saving New Map...")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as f:
        VMF.export(dest_file=f, inc_version=True)
    utils.con_log("Complete!")


def run_vbsp(vbsp_args, do_swap, path, new_path):
    """Execute the original VBSP, copying files around so it works correctly."""

    # We can't overwrite the original vmf, so we run VBSP from a separate
    # location.
    if do_swap:
        if os.path.isfile(path.replace(".vmf", ".log")):
            shutil.copy(
                path.replace(".vmf", ".log"),
                new_path.replace(".vmf", ".log"),
            )
    # Put quotes around args which contain spaces, and remove blank args.
    vbsp_args = [('"' + x + '"' if " " in x else x) for x in vbsp_args if x]

    arg = (
        '"'
        + os.path.normpath(
            os.path.join(
                os.getcwd(),
                "vbsp_original"
                )
            )
        + '" '
        + " ".join(vbsp_args)
        )

    utils.con_log("Calling original VBSP...")
    utils.con_log(arg)
    code = subprocess.call(
        arg,
        stdout=None,
        stderr=subprocess.PIPE,
        shell=True,
    )
    if code == 0:
        utils.con_log("Done!")
    else:
        utils.con_log("VBSP failed! (" + str(code) + ")")
        sys.exit(code)
    if do_swap:  # copy over the real files so vvis/vrad can read them
        for ext in (".bsp", ".log", ".prt"):
            if os.path.isfile(new_path.replace(".vmf", ext)):
                shutil.copy(
                    new_path.replace(".vmf", ext),
                    path.replace(".vmf", ext),
                )


def main():
    """Main program code.

    """
    global MAP_SEED, IS_PREVIEW, GAME_MODE
    utils.con_log("BEE2 VBSP hook initiallised.")

    args = " ".join(sys.argv)
    new_args = sys.argv[1:]
    old_args = sys.argv[1:]
    new_path = ""
    path = ""
    for i, a in enumerate(new_args):
        fixed_a = os.path.normpath(a)
        if "sdk_content\\maps\\" in fixed_a:
            new_args[i] = fixed_a.replace(
                'sdk_content\\maps\\',
                'sdk_content\\maps\styled\\',
                1,
                )
            new_path = new_args[i]
            path = a
        # We need to strip these out, otherwise VBSP will get confused.
        if a == '-force_peti' or a == '-force_hammer':
            new_args[i] = ''
            old_args[i] = ''
        # Strip the entity limit, and the following number
        if a == '-entity_limit':
            new_args[i] = ''
            if len(new_args) > i+1 and new_args[i+1] == '1750':
                new_args[i+1] = ''

    utils.con_log('Map path is "' + path + '"')
    if path == "":
        raise Exception("No map passed!")
    if not path.endswith(".vmf"):
        path += ".vmf"
        new_path += ".vmf"

    utils.con_log("Loading settings...")
    load_settings()

    if '-force_peti' in args or '-force_hammer' in args:
        # we have override command!
        if '-force_peti' in args:
            utils.con_log('OVERRIDE: Attempting to convert!')
            is_hammer = False
        else:
            utils.con_log('OVERRIDE: Abandoning conversion!')
            is_hammer = True
    else:
        # If we don't get the special -force args, check for the entity
        # limit to determine if we should convert
        is_hammer = "-entity_limit 1750" not in args
    if is_hammer:
        utils.con_log("Hammer map detected! skipping conversion..")
        run_vbsp(
            vbsp_args=old_args,
            do_swap=False,
            path=path,
            new_path=new_path,
        )
    else:
        utils.con_log("PeTI map detected!")

        load_map(path)

        MAP_SEED = calc_rand_seed()

        (
            IS_PREVIEW,
            GAME_MODE,
            voice_timer_pos,
            all_inst,
        ) = get_map_info()

        conditions.init(
            seed=MAP_SEED,
            inst_list=all_inst,
            vmf_file=VMF,
            game_mode=GAME_MODE,
            is_pre=IS_PREVIEW,
            )

        fix_inst()
        conditions.check_all()
        add_extra_ents(mode=GAME_MODE)

        change_ents()
        change_goo_sides()  # Must be done before!
        change_brush()
        change_overlays()
        change_trig()
        change_func_brush()

        fix_worldspawn()
        add_voice(voice_timer_pos, GAME_MODE)
        save(new_path)

        run_vbsp(
            vbsp_args=new_args,
            do_swap=True,
            path=path,
            new_path=new_path,
        )

    utils.con_log("BEE2 VBSP hook finished!")


if __name__ == '__main__':
    main()