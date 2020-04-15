Armamake
===

Armamake is a build system for addons made for Arma 3. It is especially suited to large or modular projects which may need multiple build configurations, multiple subsets of modules signed with distinct keys, or other complex features. However, it works out of the box with no configuration needed for simple projects, even those intended to produce multiple PBOs. It relies on the official AddonBuilder from BI, included in Arma 3 Tools.

Armamake is written in **Python 3**.


HOWTO
===
Copy make.py and make.cfg into the root of your addon workspace. It should look something like this:

	workspace\
		| module1\
			|-- config.cpp
			|-- init.sqf
		| module2\
			|-- config.cpp
		|-- make.py
		|-- make.cfg

Open a command prompt here and run:
		`python make.py help`

To build your addon:
		`python make.py`

A directory called 'release' will be created with your addon and all modules built inside it.

You should look through the make.cfg file and customize it to suit your project. Each option is explained in the example file.

To build a single module only:
		`python make.py module1`

If you need to rebuild everything, use:
		`python make.py force`

If you want to copy the build result to your Arma directory:
		`python make.py test`

When everything is ready, you can run:
		`python make.py release 0.1`
to automatically build and pack your addon.

You can also stack command line options:
		`python make.py force test release 0.1`

If you have multiple build targets defined in make.cfg, specify them at build time:
		`python make.py target AlternateBuild force test`

---

The MIT License

Copyright (c) 2013-2020 Ryan Schultz.

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.

