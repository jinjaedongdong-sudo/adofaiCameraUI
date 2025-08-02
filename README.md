# ADOFAI Camera UI

This repository contains an experimental camera editor for [ADOFAI](https://store.steampowered.com/app/977950/A_Dance_of_Fire_and_Ice/) maps.  The editor is written in Python and uses `pygame` for real‑time rendering of the tile path and camera keyframes.  MoveCamera events can be created and adjusted interactively and saved back to a `.adofai` file.

## Features

* Load an existing `.adofai` level and its audio file
* Display tile path in world coordinates
* Add and move camera keyframes with a wide range of easing functions
  (Quad, Cubic, Quart, Quint, Sine, Expo, Circ, Back, Bounce, Elastic)
* Elastic easing with configurable oscillation/decay parameters
* Real‑time preview of camera position and easing curve
* Convenience shortcuts inspired by animation tools (add/delete/duplicate
  keyframes, cycle easing types, jump between keyframes)

The project is in a prototype state and many features from the original
specification are not yet implemented, such as full timeline editing,
comprehensive keyframe manipulation and a dedicated UI for parameter editing.

### Keyboard shortcuts

| Key | Action |
| --- | ------ |
| `Space` | Play/Pause |
| `N` | Add keyframe at current time |
| `Delete/Backspace` | Delete selected keyframe |
| `Ctrl+D` | Duplicate selected keyframe |
| `,` / `.` | Select previous / next keyframe |
| `Tab` / `Shift+Tab` | Cycle easing forward/backward |
| `W` `A` `S` `D` | Move selected keyframe |

## Usage

```bash
python camera_editor.py <level.adofai> <audio.ogg>
```

The editor uses `pygame` and `adofaipy`.  Ensure the required dependencies are
installed:

```bash
pip install pygame adofaipy numpy
```

## License

Released under the MIT License.
