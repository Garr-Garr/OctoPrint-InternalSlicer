---
layout: plugin
    
id: slicer
title: Internal Slicer
description: A full-blown GUI-based slicer. Rotate and scale model; slice multiple STL files at a time; set layer height and other slicing settings.
author: Garrett Broters
license: AGPLv3
    
# today's date in format YYYY-MM-DD, e.g.
date: 2024-02-26
    
homepage: https://github.com/Garr-Garr/OctoPrint-InternalSlicer
source: https://github.com/Garr-Garr/OctoPrint-InternalSlicer
archive: https://github.com/Garr-Garr/OctoPrint-InternalSlicer/archive/master.zip
    
# set this to true if your plugin uses the dependency_links setup parameter to include
# library versions not yet published on PyPi. SHOULD ONLY BE USED IF THERE IS NO OTHER OPTION!
follow_dependency_links: false
    
tags:
- slicer
- gcode
- stl

screenshots: 
- url: /assets/img/plugins/slicer/screenshot1.png
  alt: Slicer plugin screenshot
  caption: Slicer plugin screenshot

featuredimage: /assets/img/plugins/slicer/screenshot1.png

compatibility:
  # list of compatible versions, for example 1.2.0. If left empty no specific version requirement will be assumed
  octoprint:
  - 1.2.14

  # list of compatible operating systems, valid values are linux, windows, macos, leaving empty defaults to all
  os:
  - linux
  - windows
  - macos
---

Slicer plugin offers useful features that OctoPrint's built-in slicer doesn't have:

- Rotate, scale, and move STL models.
- Slice multiple STLs at a time.
- Auto-arrange models into optimized layout (experimental).
- Slice based on Cura profiles you upload to OctoPrint.
- Customizable slicing settings, including Basic (layer height, bed temperature ...) and Advanced (print speed, start/end G-code ...).
- More is coming...
