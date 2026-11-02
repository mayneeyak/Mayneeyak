"""The move library.

A move is a list of steps. Each step is (seconds, pose) or (seconds, pose, hold_seconds).
The character smoothly moves into each pose over `seconds`, then holds it.
Unless the move says "stay": True, the character relaxes back to rest at the end.

A pose describes body parts in plain words (angles in degrees, distances in meters):

    "body":  lean (+forward / -back), twist (+left / -right), side (+tilt left),
             bob (+up / -down), sway (+to the right)
    "head":  nod (+down / -up), turn (+left / -right), tilt (+left / -right)
    "arm_r", "arm_l":  forward (+), out (+away from the body), bend (elbow, +)
    "leg_r", "leg_l":  forward (+), out (+away from the body)
    "brows": raise (meters, e.g. 0.03), angle (+worried / -angry)

Anything you leave out goes back to its resting position.
Add your own:  MOVES["salute"] = {"steps": [(0.3, {"arm_r": {"forward": 100, "out": 40, "bend": 120}}, 1.0)]}
"""

MOVES = {
    "wave": {"steps": [
        (0.3, {"arm_r": {"out": 160, "bend": 20}, "head": {"tilt": -8}, "brows": {"raise": 0.015}}),
        (0.18, {"arm_r": {"out": 140, "bend": 40}, "head": {"tilt": -8}, "brows": {"raise": 0.015}}),
        (0.18, {"arm_r": {"out": 165, "bend": 15}, "head": {"tilt": -8}, "brows": {"raise": 0.015}}),
        (0.18, {"arm_r": {"out": 140, "bend": 40}, "head": {"tilt": -8}, "brows": {"raise": 0.015}}),
        (0.18, {"arm_r": {"out": 165, "bend": 15}, "head": {"tilt": -8}, "brows": {"raise": 0.015}}),
    ]},
    "cheer": {"repeat": 3, "steps": [
        (0.18, {"arm_r": {"out": 165}, "arm_l": {"out": 165}, "head": {"nod": -15},
                "body": {"bob": 0.25}, "brows": {"raise": 0.03}}),
        (0.18, {"arm_r": {"out": 140, "bend": 20}, "arm_l": {"out": 140, "bend": 20}, "head": {"nod": -10},
                "brows": {"raise": 0.03}}),
    ]},
    "jump": {"steps": [
        (0.15, {"body": {"bob": -0.12, "lean": 15}, "arm_r": {"forward": -35}, "arm_l": {"forward": -35},
                "leg_r": {"forward": 10}, "leg_l": {"forward": 10}}),
        (0.22, {"body": {"bob": 0.55}, "arm_r": {"out": 160}, "arm_l": {"out": 160},
                "leg_r": {"forward": 20}, "leg_l": {"forward": -10}, "head": {"nod": -20}}),
        (0.22, {"body": {"bob": 0.0}}),
        (0.1, {"body": {"bob": -0.08, "lean": 8}}),
    ]},
    "kick": {"steps": [
        (0.3, {"leg_r": {"forward": -35}, "body": {"lean": 8}, "arm_r": {"out": 25}, "arm_l": {"out": 25}}),
        (0.12, {"leg_r": {"forward": 95}, "body": {"lean": -18}, "arm_r": {"out": 50, "forward": -20},
                "arm_l": {"out": 50, "forward": -20}}, 0.25),
    ]},
    "point": {"steps": [
        (0.3, {"arm_r": {"forward": 90}}, 0.9),
    ]},
    "point_up": {"steps": [
        (0.3, {"arm_r": {"forward": 150, "out": 10}, "head": {"nod": -25}, "brows": {"raise": 0.025}}, 1.2),
    ]},
    "think": {"steps": [
        (0.4, {"arm_r": {"forward": 60, "out": -15, "bend": 125}, "arm_l": {"forward": 35, "out": -20, "bend": 80},
               "head": {"tilt": 12, "nod": -8}, "brows": {"angle": -10}}, 1.4),
    ]},
    "sad": {"steps": [
        (0.6, {"head": {"nod": 28}, "body": {"lean": 8, "bob": -0.03}, "arm_r": {"forward": 8},
               "arm_l": {"forward": 8}, "brows": {"angle": 22}}, 1.2),
    ]},
    "shrug": {"steps": [
        (0.25, {"arm_r": {"out": 35, "forward": 25, "bend": 70}, "arm_l": {"out": 35, "forward": 25, "bend": 70},
                "head": {"tilt": 14}, "body": {"bob": 0.03}, "brows": {"raise": 0.025, "angle": 12}}, 0.7),
    ]},
    "nod": {"steps": [
        (0.15, {"head": {"nod": 20}}),
        (0.15, {"head": {"nod": -5}}),
        (0.15, {"head": {"nod": 20}}),
    ]},
    "shake_head": {"repeat": 2, "steps": [
        (0.15, {"head": {"turn": 30}}),
        (0.15, {"head": {"turn": -30}}),
    ]},
    "look_around": {"steps": [
        (0.5, {"head": {"turn": 60}, "body": {"twist": 12}}, 0.3),
        (0.7, {"head": {"turn": -60}, "body": {"twist": -12}}, 0.3),
    ]},
    "surprised": {"steps": [
        (0.15, {"body": {"lean": -12, "bob": 0.05}, "arm_r": {"out": 55, "forward": 30, "bend": 40},
                "arm_l": {"out": 55, "forward": 30, "bend": 40}, "head": {"nod": -15},
                "brows": {"raise": 0.04}}, 0.6),
    ]},
    "dance": {"repeat": 4, "steps": [
        (0.28, {"arm_r": {"forward": 60, "out": 30, "bend": 40}, "arm_l": {"forward": -20, "out": 20},
                "head": {"tilt": -10}, "body": {"twist": 12, "side": -6, "sway": 0.06, "bob": 0.04}}),
        (0.28, {"arm_r": {"forward": -20, "out": 20}, "arm_l": {"forward": 60, "out": 30, "bend": 40},
                "head": {"tilt": 10}, "body": {"twist": -12, "side": 6, "sway": -0.06, "bob": 0.04}}),
    ]},
    "bow": {"steps": [
        (0.5, {"body": {"lean": 45}, "arm_r": {"forward": 70, "out": -25, "bend": 60}, "arm_l": {"forward": -25},
               "head": {"nod": 15}}, 0.7),
    ]},
    "talk": {"repeat": 2, "steps": [
        (0.3, {"arm_r": {"forward": 35, "out": 10, "bend": 50}, "head": {"nod": -5}}),
        (0.3, {"arm_l": {"forward": 35, "out": 10, "bend": 50}}),
    ]},
    "clap": {"repeat": 3, "steps": [
        (0.12, {"arm_r": {"forward": 70, "out": 20, "bend": 50}, "arm_l": {"forward": 70, "out": 20, "bend": 50}}),
        (0.12, {"arm_r": {"forward": 70, "out": -12, "bend": 45}, "arm_l": {"forward": 70, "out": -12, "bend": 45},
                "brows": {"raise": 0.02}}),
    ]},
}
