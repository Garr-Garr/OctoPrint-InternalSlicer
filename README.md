# OctoPrint Slicer

<img src="/docs/screenshot1.png" width="600">

Slicer plugin offers useful features that OctoPrint's built-in slicer doesn't have:

- [PrusaSlicer](https://www.prusa3d.com/page/prusaslicer_424/) support
- Rotate, scale, and move STL models.
- Slice multiple STLs at a time. Split 1 STL into unconnected parts.
- Circular print bed support (do you have a delta printer?).
- High-light overhang areas. Automatically orient the model for better result ("lay flat").
- Slice based on PrusaSlicer profiles you upload to OctoPrint.
- Customizable slicing settings, including Basic (layer height, bed temperature ...) and Advanced (print speed, start/end G-code ...).
- More is coming...

## Setup
### Online:
Install via the bundled [Plugin Manager](https://github.com/foosel/OctoPrint/wiki/Plugin:-Plugin-Manager)
or manually using this URL:

    https://github.com/Garr-R/OctoPrint-Slicer/archive/refs/heads/master.zip

### Offline (Bundled with PruasSlicer v2.4.2): 
You'll need to download the following zip file on your computer / device and then upload it to OctoPrint using the bundled [Plugin Manager](https://github.com/foosel/OctoPrint/wiki/Plugin:-Plugin-Manager):

    https://github.com/Garr-R/OctoPrint-Slicer/archive/refs/heads/offline.zip

## Importing your printer's PrusaSlicer profile
add instructions

## Future plans

- [ ] Create a setup wizard that helps explain downloading PrusaSlicer and importing profiles
- [ ] Update Docker development support
- [ ] Make compatible with the latest version of PrusaSlicer (v2.6)
- [ ] Add more adjustable profile settings
- [ ] OctoPrint slicing profile overhaul (Use Print/Filament/Printer profiles from official vendor bundles)
  
## More Photos

<img src="/docs/screenshot2.png" width="600">
<img src="/docs/screenshot3.png" width="600">
<img src="/docs/screenshot4.png" width="600">

## Thank you to [Kenneth Jiang](https://github.com/kennethjiang/), [Foosel](https://github.com/foosel), [Eyal](https://github.com/eyal0), and many many others for building the original plugins and the OctoPrint Mixins! 
I'm standing on the shoulders of giants and doubt I would've been able to start this project without the exsisting code and infrastructure. 
