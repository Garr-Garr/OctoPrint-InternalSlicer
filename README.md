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

*Currently only [PrusaSlicer ~v2.4.2 works](https://github.com/prusa3d/PrusaSlicer/releases/tag/version_2.4.2) and older versions work, but profiles exported from PrusaSlicer v2.5+ still import correctly into this plugin :)

## Setup

Install via the bundled [Plugin Manager](https://github.com/foosel/OctoPrint/wiki/Plugin:-Plugin-Manager)
or manually using this URL:

    https://github.com/Garr-R/OctoPrint-Slicer/archive/refs/heads/master.zip

## Plans

- [x] Make PrusaSlicer the default slicer
- [x] Add a script to download PrusaSlicer v2.4.2 to a Raspberry Pi
- [x] Remove Cura support 
- [ ] Add a script to download PrusaSlicer to a Windows OctoPrint configuration
- [ ] Add a script to download PrusaSlicer to a Ubuntu OctoPrint configuration
- [ ] Fix Docker development support
- [ ] Add PrusaSlicer settings documentation hyperlinks to each slicer setting
- [ ] Create a setup wizard that helps explain downloading PrusaSlicer and importing profiles
  - [ ] Add all of the default vendor profiles and presets from PrusaSlicer so users can select them from the setup wizard and don't have to manually export/import their machine's profile

## More Photos

<img src="/docs/screenshot2.png" width="600">
<img src="/docs/screenshot3.png" width="600">
<img src="/docs/screenshot4.png" width="600">

## Thank you to [Kenneth Jiang](https://github.com/kennethjiang/), [Foosel](https://github.com/foosel), [Eyal](https://github.com/eyal0), and many many others for building the original plugins and the OctoPrint Mixins! 
I'm standing on the shoulders of giants and doubt I would've been able to start this project without the exsisting code and infrastructure. 
