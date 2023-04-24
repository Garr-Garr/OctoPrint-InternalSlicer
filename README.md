*Note: This project is a work in progress and doesn't exactly work at the moment. 

I'm working on combining the (now abandoned) [OctoPrint-Slicer plugin](https://github.com/OctoPrint/OctoPrint-Slic3r) with the [OctoPrint-Slic3r plugin](https://github.com/OctoPrint/OctoPrint-Slic3r), and make everything compatible with the latest version of PrusaSlicer. My end-goal is to have built-in support for any existing PrusaSlicer vendor profile from the web interface, but I'm starting and testing with MakerGear printers since I only have access to those

*Currently only [PrusaSlicer ~v2.4.2 works](https://github.com/prusa3d/PrusaSlicer/releases/tag/version_2.4.2), but not v2.5+, and you have to manually download either the AppImage or the 'linux-armv7l-GTK2.tar.bz2' file. 

## Thank you to [Kenneth Jiang](https://github.com/kennethjiang/), [Foosel](https://github.com/foosel), [Eyal](https://github.com/eyal0), and many many others for building the original plugins and the OctoPrint Mixins! 
I'm standing on the shoulders of giants and doubt I would've been able to start this project without the exsisting code and infrastructure. 

# OctoPrint Slicer

Slicer plugin offers useful features that OctoPrint's built-in slicer doesn't have:

- Rotate, scale, and move STL models.
- Slice multiple STLs at a time. Split 1 STL into unconnected parts.
- Circular print bed support (do you have a delta printer?).
- High-light overhang areas. Automatically orient the model for better result ("lay flat").
- Slice based on Cura profiles you upload to OctoPrint.
- Customizable slicing settings, including Basic (layer height, bed temperature ...) and Advanced (print speed, start/end G-code ...).
- Slic3r support (when Slic3r plugin is installed).
- More is coming...

![Slicer plugin screenshot](/docs/screenshot1.png?raw=true "Slicer Screen Shot")
![Slicer plugin screenshot](/docs/screenshot2.png?raw=true "Slicer Screen Shot")
![Slicer plugin screenshot](/docs/screenshot3.png?raw=true "Slicer Screen Shot")
![Slicer plugin screenshot](/docs/screenshot4.png?raw=true "Slicer Screen Shot")


## Setup

Install via the bundled [Plugin Manager](https://github.com/foosel/OctoPrint/wiki/Plugin:-Plugin-Manager)
or manually using this URL:

    https://github.com/kennethjiang/OctoPrint-Slicer/archive/master.zip

## Contribute

Are you a proud developer? Do you want to pitch in? I have made it as easy as 1-2-3:

1. [Install Docker](https://docs.docker.com/engine/installation/). Make sure [Docker compose](https://docs.docker.com/compose/) is also installed.

1. Clone OctoPrint-Slicer and run it

```bash
git clone https://github.com/kennethjiang/OctoPrint-Slicer.git
cd OctoPrint-Slicer
docker-compose up
```

1. Open [http://localhost:5000/](http://localhost:5000/) in your browser

## Thanks
![BrowserStack](https://lh4.googleusercontent.com/wyCKLuED8i1E6mvA8Moiwd5VSq2jXHXPOel85bqnW-rUU_tXBr0c1aSIhY7SHH1jKTaf7AF7vA=s50-h50-e365 "BrowserStack") BrowserStack generously sponsors a free license so that I can test Slicer Plugin on different browsers/versions.

