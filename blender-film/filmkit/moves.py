"""The move library.

A move is a list of steps. Each step is (seconds, pose) or (seconds, pose, hold_seconds).
The character moves into each pose over `seconds` (heads and arms follow a moment later,
like real bodies), then holds it. Unless the move says "stay": True, the character relaxes
back to rest at the end. Feet stay planted on the ground and knees bend automatically.

A pose describes body parts in plain words (angles in degrees, distances in meters):

    "body":  lean (+forward / -back), twist (+left / -right), side (+tilt left)
    "hips":  bob (+up / -down: knees bend), sway (+to the right), twist (+left)
    "head":  nod (+down / -up), turn (+left / -right), tilt (+left / -right)
    "arm_r", "arm_l":  forward (+), out (+away from the body, - across it), bend (elbow), wrist
    "leg_r", "leg_l":  forward, out, bend (knee), point (toes). Setting a leg frees it from the ground.
    "feet": "free"     both legs follow their pose (for jumps)
    "brows": raise (meters, e.g. 0.02), angle (+worried / -angry)
    "face":  smile (-1..1), smirk (-1..1), lids (0 closed..1 wide open), look=(x, y) degrees

Add your own:  MOVES["salute"] = {"steps": [(0.3, {"arm_r": {"forward": 100, "out": 40, "bend": 120}}, 1.0)]}
"""

_wave_hi = {"arm_r": {"out": 160, "bend": 20}, "head": {"tilt": -6}, "brows": {"raise": 0.012}, "face": {"smile": 0.8}}
_wave_lo = {"arm_r": {"out": 138, "bend": 50}, "head": {"tilt": -6}, "brows": {"raise": 0.012}, "face": {"smile": 0.8}}
_count_a = {"arm_l": {"forward": 48, "out": -22, "bend": 88}, "arm_r": {"forward": 52, "out": -28, "bend": 96, "wrist": 25},
            "head": {"nod": 28}, "face": {"look": (0, -18), "smirk": 0.5}}
_count_b = {"arm_l": {"forward": 48, "out": -22, "bend": 88}, "arm_r": {"forward": 50, "out": -24, "bend": 92, "wrist": -15},
            "head": {"nod": 26}, "face": {"look": (0, -18), "smirk": 0.5}}
_crossed = {"arm_r": {"forward": 72, "out": -52, "bend": 118}, "arm_l": {"forward": 66, "out": -48, "bend": 112}}

MOVES = {
    "wave": {"steps": [(0.3, _wave_hi), (0.17, _wave_lo), (0.17, _wave_hi), (0.17, _wave_lo), (0.17, _wave_hi)]},
    "cheer": {"repeat": 2, "steps": [
        (0.14, {"hips": {"bob": -0.06}, "arm_r": {"out": 120, "bend": 40}, "arm_l": {"out": 120, "bend": 40},
                "face": {"smile": 1}, "brows": {"raise": 0.02}}),
        (0.16, {"hips": {"bob": 0.12}, "feet": "free", "leg_r": {"bend": 25, "forward": 10}, "leg_l": {"bend": 35},
                "arm_r": {"out": 165}, "arm_l": {"out": 165}, "head": {"nod": -15}, "face": {"smile": 1, "lids": 1},
                "brows": {"raise": 0.03}}),
        (0.16, {"hips": {"bob": -0.04}, "arm_r": {"out": 140, "bend": 25}, "arm_l": {"out": 140, "bend": 25},
                "face": {"smile": 1}, "brows": {"raise": 0.02}}),
    ]},
    "jump": {"steps": [
        (0.18, {"hips": {"bob": -0.12}, "body": {"lean": 18}, "arm_r": {"forward": -40}, "arm_l": {"forward": -40}}),
        (0.2, {"hips": {"bob": 0.38}, "feet": "free", "leg_r": {"forward": 30, "bend": 45}, "leg_l": {"forward": 10, "bend": 30},
               "arm_r": {"out": 150, "forward": 30}, "arm_l": {"out": 150, "forward": 30}, "head": {"nod": -20}}),
        (0.22, {"hips": {"bob": -0.1}, "body": {"lean": 12}, "arm_r": {"out": 30}, "arm_l": {"out": 30}}),
    ]},
    "kick": {"steps": [
        (0.3, {"leg_r": {"forward": -35, "bend": 40}, "body": {"lean": 8}, "arm_r": {"out": 25}, "arm_l": {"out": 25},
               "hips": {"bob": -0.03}}),
        (0.12, {"leg_r": {"forward": 92, "bend": 8, "point": 30}, "body": {"lean": -18}, "arm_r": {"out": 50, "forward": -20},
                "arm_l": {"out": 50, "forward": -20}, "hips": {"bob": -0.04}, "face": {"smile": -0.3}}, 0.25),
    ]},
    "point": {"steps": [(0.3, {"arm_r": {"forward": 88, "bend": 5}, "brows": {"raise": 0.01}}, 0.9)]},
    "point_up": {"steps": [(0.3, {"arm_r": {"forward": 155, "out": 10}, "head": {"nod": -25},
                                  "brows": {"raise": 0.025}, "face": {"lids": 1}}, 1.2)]},
    "think": {"steps": [(0.45, {"arm_r": {"forward": 40, "out": -32, "bend": 128}, "arm_l": {"forward": 32, "out": -40, "bend": 92},
                                "head": {"tilt": 10, "nod": -6}, "brows": {"angle": -8}, "face": {"look": (12, 14), "smile": 0.1}}, 1.4)]},
    "sad": {"steps": [(0.6, {"head": {"nod": 30}, "body": {"lean": 10}, "hips": {"bob": -0.02}, "arm_r": {"forward": 10},
                             "arm_l": {"forward": 10}, "brows": {"angle": 20}, "face": {"smile": -0.6, "lids": 0.6}}, 1.2)]},
    "shrug": {"steps": [(0.25, {"arm_r": {"out": 32, "forward": 22, "bend": 82, "wrist": -30},
                                "arm_l": {"out": 32, "forward": 22, "bend": 82, "wrist": -30}, "head": {"tilt": 12},
                                "hips": {"bob": 0.01}, "brows": {"raise": 0.025, "angle": 10}, "face": {"smile": -0.1}}, 0.7)]},
    "nod": {"steps": [(0.15, {"head": {"nod": 18}}), (0.15, {"head": {"nod": -4}}), (0.15, {"head": {"nod": 18}})]},
    "cool_nod": {"steps": [(0.25, {"head": {"nod": -14}, "face": {"smirk": 0.6}}), (0.35, {"head": {"nod": 10}, "face": {"smirk": 0.6}}, 0.2)]},
    "shake_head": {"repeat": 2, "steps": [(0.15, {"head": {"turn": 30}}), (0.15, {"head": {"turn": -30}})]},
    "look_around": {"steps": [
        (0.5, {"head": {"turn": 60}, "body": {"twist": 12}, "face": {"look": (20, 0)}}, 0.3),
        (0.7, {"head": {"turn": -60}, "body": {"twist": -12}, "face": {"look": (-20, 0)}}, 0.3),
    ]},
    "sneaky_look": {"steps": [
        (0.2, {"head": {"turn": 55}, "hips": {"bob": -0.04}, "body": {"lean": 10}, "face": {"look": (25, 0), "lids": 0.6}}, 0.35),
        (0.25, {"head": {"turn": -55}, "hips": {"bob": -0.04}, "body": {"lean": 10}, "face": {"look": (-25, 0), "lids": 0.6}}, 0.35),
    ]},
    "surprised": {"steps": [(0.15, {"body": {"lean": -12}, "hips": {"bob": 0.01}, "arm_r": {"out": 45, "forward": 30, "bend": 55},
                                    "arm_l": {"out": 45, "forward": 30, "bend": 55}, "head": {"nod": -12},
                                    "brows": {"raise": 0.035}, "face": {"lids": 1, "smile": -0.2}}, 0.6)]},
    "dance": {"repeat": 4, "steps": [
        (0.28, {"arm_r": {"forward": 60, "out": 25, "bend": 70}, "arm_l": {"forward": -15, "out": 20, "bend": 30},
                "head": {"tilt": -10}, "hips": {"twist": 14, "sway": 0.04, "bob": -0.04}, "body": {"twist": -6, "side": -5},
                "face": {"smile": 0.9}}),
        (0.28, {"arm_r": {"forward": -15, "out": 20, "bend": 30}, "arm_l": {"forward": 60, "out": 25, "bend": 70},
                "head": {"tilt": 10}, "hips": {"twist": -14, "sway": -0.04, "bob": -0.04}, "body": {"twist": 6, "side": 5},
                "face": {"smile": 0.9}}),
    ]},
    "bow": {"steps": [(0.5, {"body": {"lean": 42}, "hips": {"shift": 0.04}, "arm_r": {"forward": 70, "out": -25, "bend": 70},
                             "arm_l": {"forward": -20}, "head": {"nod": 15}}, 0.7)]},
    "talk": {"repeat": 2, "steps": [
        (0.3, {"arm_r": {"forward": 35, "out": 8, "bend": 55, "wrist": -20}, "head": {"nod": -5}}),
        (0.3, {"arm_l": {"forward": 35, "out": 8, "bend": 55, "wrist": -20}}),
    ]},
    "clap": {"repeat": 3, "steps": [
        (0.12, {"arm_r": {"forward": 65, "out": 18, "bend": 60}, "arm_l": {"forward": 65, "out": 18, "bend": 60}, "face": {"smile": 0.9}}),
        (0.12, {"arm_r": {"forward": 65, "out": -14, "bend": 55}, "arm_l": {"forward": 65, "out": -14, "bend": 55},
                "brows": {"raise": 0.015}, "face": {"smile": 0.9}}),
    ]},
    # --- attitude
    "arms_crossed": {"stay": True, "steps": [(0.4, dict(_crossed, body={"lean": -4}))]},
    "lean_back": {"stay": True, "steps": [(0.5, dict(_crossed, body={"lean": -9}, hips={"shift": -0.02, "bob": -0.01},
                                                    head={"nod": -6, "tilt": 6}, face={"smirk": 0.6, "lids": 0.55}))]},
    "count_money": {"steps": [(0.35, _count_a), (0.15, _count_b), (0.15, _count_a), (0.15, _count_b), (0.15, _count_a),
                              (0.15, _count_b), (0.3, _count_a, 0.3)]},
    "hand_out": {"stay": True, "steps": [(0.35, {"arm_r": {"forward": 62, "out": -4, "bend": 22, "wrist": -25},
                                                 "body": {"lean": 3}})]},
    "whisper": {"steps": [(0.4, {"body": {"lean": 16, "twist": -8}, "hips": {"bob": -0.03},
                                 "arm_r": {"forward": 78, "out": -22, "bend": 135, "wrist": 10},
                                 "head": {"tilt": 10, "nod": 6}, "face": {"lids": 0.6}, "brows": {"raise": 0.01}}, 1.4)]},
    "facepalm": {"steps": [(0.3, {"arm_r": {"forward": 85, "out": -22, "bend": 150, "wrist": 10}, "head": {"nod": 22},
                                  "body": {"lean": 8}, "face": {"smile": -0.4, "lids": 0.2}}, 1.0)]},
    "sigh": {"steps": [(0.5, {"body": {"lean": -6}, "hips": {"bob": 0.01}, "arm_r": {"out": 10}, "arm_l": {"out": 10},
                              "head": {"nod": -12}, "face": {"lids": 0.5, "smile": -0.3}}),
                       (0.7, {"body": {"lean": 6}, "hips": {"bob": -0.03}, "head": {"nod": 14},
                              "face": {"lids": 0.55, "smile": -0.2}}, 0.3)]},
    "gasp": {"steps": [(0.12, {"body": {"lean": -10}, "arm_r": {"forward": 70, "out": -20, "bend": 120},
                               "arm_l": {"forward": 70, "out": -20, "bend": 120}, "brows": {"raise": 0.04},
                               "face": {"lids": 1, "smile": -0.5}}, 0.8)]},
    "swag": {"steps": [(0.3, {"body": {"lean": -6, "side": 6}, "hips": {"sway": 0.03, "bob": -0.02},
                              "arm_r": {"forward": 30, "out": 20, "bend": 70, "wrist": -20}, "head": {"tilt": -10, "nod": -6},
                              "face": {"smirk": 0.8, "lids": 0.6}}, 0.6)]},
}
