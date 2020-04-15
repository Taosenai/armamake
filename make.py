#!/usr/bin/env python
# vim: set fileencoding=utf-8 :

# Armamake (make.py)
"""An Arma 3 addon build system."""

###############################################################################

# The MIT License (MIT)

# Copyright (c) 2013-2020 Ryan Schultz

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

###############################################################################

__version__ = "0.6"
# "I shall return." edition

import sys
import os
import os.path
import shutil
import glob
import subprocess
import hashlib
import configparser
import json
import traceback

if sys.version_info[0] == 2:
	print("Python 3 is required.")
	sys.exit(1)
if sys.platform == "win32":
	import winreg

###############################################################################
# External code
###############################################################################

# http://akiscode.com/articles/sha-1directoryhash.shtml
# Copyright (c) 2009 Stephen Akiki
# MIT License (Means you can do whatever you want with this)
#  See http://www.opensource.org/licenses/mit-license.php
# Error Codes:
#   -1 -> Directory does not exist
#   -2 -> General error (see stack traceback)
def get_directory_hash(directory):
	"""Returns hash of target directory."""
	directory_hash = hashlib.sha1()
	if not os.path.exists (directory):
		return -1

	try:
		for root, _, files in os.walk(directory):
			for names in files:
				path = os.path.join(root, names)
				try:
					f = open(path, 'rb')
				except IOError:
					# You can't open the file for some reason
					f.close()
					continue

				while 1:
					# Read file in as little chunks
					buf = f.read(4096)
					if not buf:
						break
					new = hashlib.sha1(buf)
					directory_hash.update(new.digest())
				f.close()

	except IOError:
		# Print the stack traceback
		traceback.print_exc()
		return -2

	return directory_hash.hexdigest()

# Copyright (c) André Burgaud
# http://www.burgaud.com/bring-colors-to-the-windows-console-with-python/
if sys.platform == "win32":
	from ctypes import windll, Structure, c_short, c_ushort, byref

	SHORT = c_short
	WORD = c_ushort

	class COORD(Structure):
	  """struct in wincon.h."""
	  _fields_ = [("X", SHORT), ("Y", SHORT)]

	class SMALL_RECT(Structure):
	  """struct in wincon.h."""
	  _fields_ = [("Left", SHORT), ("Top", SHORT), ("Right", SHORT), ("Bottom", SHORT)]

	class CONSOLE_SCREEN_BUFFER_INFO(Structure):
	  """struct in wincon.h."""
	  _fields_ = [("dwSize", COORD), ("dwCursorPosition", COORD), ("wAttributes", WORD), ("srWindow", SMALL_RECT), ("dwMaximumWindowSize", COORD)]

	# winbase.h
	STD_INPUT_HANDLE = -10
	STD_OUTPUT_HANDLE = -11
	STD_ERROR_HANDLE = -12

	# wincon.h
	FOREGROUND_BLACK     = 0x0000
	FOREGROUND_BLUE      = 0x0001
	FOREGROUND_GREEN     = 0x0002
	FOREGROUND_CYAN      = 0x0003
	FOREGROUND_RED       = 0x0004
	FOREGROUND_MAGENTA   = 0x0005
	FOREGROUND_YELLOW    = 0x0006
	FOREGROUND_GREY      = 0x0007
	FOREGROUND_INTENSITY = 0x0008 # foreground color is intensified.

	BACKGROUND_BLACK     = 0x0000
	BACKGROUND_BLUE      = 0x0010
	BACKGROUND_GREEN     = 0x0020
	BACKGROUND_CYAN      = 0x0030
	BACKGROUND_RED       = 0x0040
	BACKGROUND_MAGENTA   = 0x0050
	BACKGROUND_YELLOW    = 0x0060
	BACKGROUND_GREY      = 0x0070
	BACKGROUND_INTENSITY = 0x0080 # background color is intensified.

	stdout_handle = windll.kernel32.GetStdHandle(STD_OUTPUT_HANDLE)
	SetConsoleTextAttribute = windll.kernel32.SetConsoleTextAttribute
	GetConsoleScreenBufferInfo = windll.kernel32.GetConsoleScreenBufferInfo

	def get_text_attr():
	  """Returns the character attributes (colors) of the console screen
	  buffer."""
	  csbi = CONSOLE_SCREEN_BUFFER_INFO()
	  GetConsoleScreenBufferInfo(stdout_handle, byref(csbi))
	  return csbi.wAttributes

	def set_text_attr(color):
	  """Sets the character attributes (colors) of the console screen
	  buffer. Color is a combination of foreground and background color,
	  foreground and background intensity."""
	  SetConsoleTextAttribute(stdout_handle, color)

###############################################################################

def color(color):
	"""Set the color. Works on Win32 and normal terminals."""
	if sys.platform == "win32":
		if color == "green":
			set_text_attr(FOREGROUND_GREEN | get_text_attr() & 0x0070 | FOREGROUND_INTENSITY)
		elif color == "red":
			set_text_attr(FOREGROUND_RED | get_text_attr() & 0x0070 | FOREGROUND_INTENSITY)
		elif color == "blue":
			set_text_attr(FOREGROUND_BLUE | get_text_attr() & 0x0070 | FOREGROUND_INTENSITY)
		elif color == "reset":
			set_text_attr(FOREGROUND_GREY | get_text_attr() & 0x0070)
		elif color == "grey":
			set_text_attr(FOREGROUND_GREY | get_text_attr() & 0x0070)
	else :
		if color == "green":
			sys.stdout.write('\033[92m')
		elif color == "red":
			sys.stdout.write('\033[91m')
		elif color == "blue":
			sys.stdout.write('\033[94m')
		elif color == "reset":
			sys.stdout.write('\033[0m')

def print_error(msg):
	"""Print error message."""
	color("red")
	print ("ERROR: " + msg)
	color("reset")

def print_green(msg):
	"""Print green message."""
	color("green")
	print(msg)
	color("reset")

def print_blue(msg):
	"""Print blue message."""
	color("blue")
	print(msg)
	color("reset")

def print_help():
	"""Prints help info on console usage of this program."""
	print ("""
make.py [help] [test] [force] [key <name>] [target <name>] [release <version>]
        [module names ...]

test -- Copy result to <Arma 3 location>\Mods folder.
release <version> -- Make archive with <version>.
force -- Ignore cache and build all.
target <name> -- Use rules in make.cfg under heading [<name>] rather than
   default [Make]
key <name> -- Use key in working directory with <name> to sign. If it does not
   exist, create key.

If module names are specified, only those modules will be built.

If a file called $NOBIN$ is found in the module directory, that module will not be binarized.
See the make.cfg file for additional build options.


Examples:
   make.py force test
      Build all modules (ignoring cache) and copy the mod folder to the Arma 3
      directory.
   make.py mymodule_gun
      Only build the module named 'mymodule_gun'.
   make.py force key MyNewKey release 1.0
      Build all modules (ignoring cache), sign them with NewKey, and pack them
      into a zip file for release with version 1.0.

""")

###############################################################################
###############################################################################
###############################################################################

class Make:
	"""Main class for building an Arma addon."""

	def __init__(self, root, target = "DEFAULT", modules = None, release = False, version = None, test = False, force = False, key = None, quiet = True):
		self.root = root

		# Constructor parameters
		self.target = target
		self.modules = modules
		self.release = release
		self.test = test
		self.force = force
		self.version = version
		self.key = key
		self.quiet = quiet

		self.find_tools()
		self.init_cache()

		self.parse_config()

		if self.module_autodetect:
			self.autodetect_modules()

	def parse_config(self):
		"""Parse make.cfg values."""
		cfg = configparser.ConfigParser()

		try:
			cfg.read(os.path.join(self.root, "make.cfg"))

			# Project name (with @ symbol)
			self.project = cfg.get(self.target, "project", fallback="@"+os.path.basename(os.getcwd()))
			# Project build root. Packing starts from this point for prefix creation. Default is make root.
			self.project_root = os.path.normpath(cfg.get(self.target, "project_root", fallback=self.root))
			self.project_root = os.path.abspath(self.project_root)
			# Module root. Location of addon folders. Default is project root.
			self.module_root = os.path.normpath(cfg.get(self.target, "module_root", fallback=self.project_root))
			self.module_root = os.path.abspath(self.module_root)
			# Private key path
			self.key = cfg.get(self.target, "key", fallback=None)
			# Should we autodetect modules on a complete build?
			self.module_autodetect = cfg.getboolean(self.target, "module_autodetect", fallback=True)
			# Manual list of modules to build for a complete build
			self.config_modules = cfg.get(self.target, "modules", fallback=None)
			# Parse it out and update self.modules if no modules were specified at init
			if self.config_modules and len(self.modules) == 0:
				self.modules = [x.strip() for x in self.config_modules.split(',')]
			# List of directories to ignore when detecting
			self.ignore = [x.strip() for x in cfg.get(self.target, "ignore",  fallback="release").split(',')]
			self.ignore += [".git", ".svn", ".cvs", ".darcs", ".DS_Store"]
			# BI Tools work drive on Windows
			self.work_drive = cfg.get(self.target, "work_drive",  fallback="P:\\")
			# Which build tool should we use?
			self.build_tool = cfg.get(self.target, "build_tool", fallback="addonbuilder")
			# Absolute path to output directory. Default is relative to working directory.
			self.release_dir = os.path.normpath(cfg.get(self.target, "release_dir", fallback=os.path.join(self.root, "release")))
			self.release_dir = os.path.abspath(self.release_dir)
			# Project PBO file prefix (files are renamed to prefix_name.pbo)
			self.pbo_name_prefix = cfg.get(self.target, "pbo_name_prefix", fallback=None)
			# Suppress BI Tools console output?
			self.quiet = cfg.getboolean(self.target, "quiet", fallback=False)

		except:
			print_error("make.cfg file is required.")

	def find_tools(self):
		"""Find tools needed to build modules."""

		reg = winreg.ConnectRegistry(None, winreg.HKEY_CURRENT_USER)
		try:
			k = winreg.OpenKey(reg, r"Software\bohemia interactive\arma 3 tools")
			arma3tools_path = winreg.QueryValueEx(k, "path")[0]
			winreg.CloseKey(k)
		except:
			color("red")
			print_error("Arma 3 Tools are not installed correctly or the P: drive has not been created.")
			raise

		addonbuilder_path = os.path.join(arma3tools_path, "AddonBuilder", "AddonBuilder.exe")
		dssignfile_path = os.path.join(arma3tools_path, "DSSignFile", "DSSignFile.exe")
		dscreatekey_path = os.path.join(arma3tools_path, "DSSignFile", "DSCreateKey.exe")

		if os.path.isfile(addonbuilder_path) and os.path.isfile(dssignfile_path) and os.path.isfile(dscreatekey_path):
			self.addonbuilder =addonbuilder_path
			self.dssignfile = dssignfile_path
			self.dscreatekey = dscreatekey_path
		else:
			color("red")
			print_error("Arma 3 Tools are not installed correctly or the P: drive has not been created.")
			raise Exception("Tools not found at %s %s %s" % (addonbuilder_path, dssignfile_path, dscreatekey_path))

	def init_cache(self):
		"""Read or initialize build cache file."""
		self.cache = {}
		try:
			with open(os.path.join(self.root, "make.cache"), 'r') as f:
				cache_raw = f.read()

			self.cache = json.loads(cache_raw)
		except IOError:
			pass

	def autodetect_modules(self):
		"""Autodetect what directories in the module_root are buildable modules and add them to the modules list."""
		modules = []

		# Look in module_root
		root, dirs, _ = next(os.walk(self.module_root))
		for d in dirs:
			if "config.cpp" in os.listdir(os.path.join(root, d)) and not d in self.ignore:
				modules.append(d)

		# Look in module_root\addons if it exists
		if os.path.isdir(os.path.join(self.module_root, "addons")):
			root, dirs, _ = next(os.walk(os.path.join(self.module_root, "addons")))
			for d in dirs:
				if "config.cpp" in os.listdir(os.path.join(root, d)) and not d in self.ignore:
					modules.append(os.path.join("addons", d))

		# Look in module_root\modules if it exists
		if os.path.isdir(os.path.join(self.module_root, "modules")):
			root, dirs, _ = next(os.walk(os.path.join(self.module_root, "modules")))
			for d in dirs:
				if "config.cpp" in os.listdir(os.path.join(root, d)) and not d in self.ignore:
					modules.append(os.path.join("modules", d))

		print_green("Auto-detected %d modules." % len(modules))

		# Adjust found module paths to start from the project_root
		adjusted_modules = []
		module_path_relpath = os.path.relpath(self.module_root, self.root)
		for module in modules:
			adjusted_modules.append(os.path.abspath(os.path.normpath(os.path.join(module_path_relpath, module))))

		self.modules = adjusted_modules

	def make_key(self):
		"""Create the signing key specified from command line if necessary."""
		if self.key:
			if not os.path.isfile(os.path.join(self.root, self.key + ".biprivatekey")):
				print_green("\nRequested key does not exist.")
				ret = subprocess.call([self.dscreatekey, self.key],  stdout = subprocess.DEVNULL if self.quiet else None, stderr = subprocess.DEVNULL if self.quiet else None) # Created in root
				if ret == 0:
					print_blue("Created: " + os.path.join(self.root, self.key + ".biprivatekey"))
				else:
					print_error("Failed to create key!")

				try:
					print_blue("Copying public key to release directory.\n")

					try:
						os.makedirs(os.path.join(self.release_dir, "Keys"))
					except IOError:
						pass

					shutil.copyfile(os.path.join(self.root, self.key + ".bikey"), os.path.join(self.release_dir, "Keys", self.key + ".bikey"))

				except:
					print_error("Could not copy key to release directory.\n")
					raise

			else:
				print_green("\nNOTE: Using key " + os.path.join(self.root, self.key + ".biprivatekey\n"))

			self.key = os.path.join(self.root, self.key + ".biprivatekey")

	def zip_release(self):
		"""Zip up a successful build."""
		if self.build_tool == "pboproject":
			try:
				shutil.rmtree(os.path.join(self.release_dir, self.project, "temp"), True)
			except IOError:
				print_error("Could not delete pboProject temp files.")

		print_blue("Zipping release: " + self.project + "-" + self.version + ".zip")

		try:
			# Delete all log files
			for root, _, files in os.walk(os.path.join(self.release_dir, self.project, "Addons")):
				for current_file in files:
					if current_file.lower().endswith("log"):
						os.remove(os.path.join(root, current_file))

			# Create a zip with the contents of release/ in it
			shutil.make_archive(self.project + "-" + self.version, "zip", os.path.join(self.release_dir))
		except IOError:
			print_error("Could not make release.")

	def copy_to_a3(self):
		"""Copy built modules to Arma 3 folder for testing."""
		print_blue("Copying addon to Arma 3 folder.")

		reg = winreg.ConnectRegistry(None, winreg.HKEY_LOCAL_MACHINE)
		try:
			k = winreg.OpenKey(reg, r"SOFTWARE\Wow6432Node\Bohemia Interactive\Arma 3")
			a3_path = winreg.EnumValue(k, 1)[1]
			winreg.CloseKey(k)
		except IOError:
			print_error("Could not find Arma 3's directory in the registry.")

		if os.path.exists(a3_path):
			try:
				shutil.rmtree(os.path.join(a3_path, "Mods", self.project), True)
				shutil.copytree(os.path.join(self.release_dir, self.project), os.path.join(a3_path, "Mods", self.project))
			except IOError:
				print_error("Could not copy files. Is Arma 3 running?")

	def make(self):
		"""Build."""

		# Prepare the signing key if needed
		self.make_key()

		failed_count = 0
		success_count = 0
		skipped_count = 0

		# For each module, prep files and then build.
		for module in self.modules:
			if os.path.isdir(os.path.join(self.project_root, module)):
				# Cache check if not force building
				if not self.force:
					if module in self.cache:
						old_sha = self.cache[module]
					else:
						old_sha = ""

					# Hash the module
					new_sha = get_directory_hash(os.path.join(self.project_root, module))

					# Check if it needs rebuilt
					# print ("Hash:", new_sha)
					if old_sha == new_sha:
							skipped_count += 1
							# Skip everything else
							continue

				print_green("Making " + module + " " + "-"*max(1, (71-len(module))))

				# Determine the name and (eventual) path of the output PBO, before prefixing
				pbo_name = module.split(os.sep)[-1]
				pbo = pbo_name + ".pbo"
				pbo_path = os.path.join(self.release_dir, self.project, "Addons", pbo)

				# Determine prefixed name and path
				if self.pbo_name_prefix:
					pbo_prefixed = self.pbo_name_prefix + pbo

				# Remove the old pbo, key, and log
				try:
					old = os.path.join(self.release_dir, self.project, "Addons", pbo) + "*"
					files = glob.glob(old)
					for f in files:
						os.remove(f)

					if self.pbo_name_prefix:
						old = os.path.join(self.release_dir, self.project, "Addons", pbo_prefixed) + "*"

						files = glob.glob(old)
						for f in files:
							os.remove(f)
				except IOError:

					print_error("Could not remove old files. Are they being used by another program?")
					input("Press Enter to continue...")
					print("Resuming build...")
					continue

				print_blue("Source: " + os.path.join(self.project_root, module))
				print_blue("Destination: " + os.path.join(self.release_dir, self.project, "Addons"))

				# Make destination folder (if needed)
				try:
					os.makedirs(os.path.join(self.release_dir, self.project, "Addons"))
				except IOError:
					pass

				# Run build tool
				try:
					if self.build_tool == "addonbuilder":
						# Create temporary file with include list to feed to Addon Builder
						include_list = "*.pac;*.paa;*.sqf;*.sqs;*.bikb;*.fsm;*.wss;*.ogg;*.wav;*.fxy;*.csv;*.html;*.lip;*.txt;*.wrp;*.bisurf;*.xml;*.hqf;*.rtm;*.rvmat;*.shp;"
						with open(os.path.join(self.root, "~make.includes"), "w") as include_file:
							include_file.write(include_list)
						include = "-include=%s" % (os.path.join(self.root, "~make.includes"))

						try:
							# Detect $NOBIN$ and only binarize if so
							if os.path.isfile(os.path.abspath(os.path.join(self.project_root, module, "$NOBIN$"))):
								print_green("$NOBIN$ file found in module, packing only.")
								cmd = [self.addonbuilder, include, "-packonly", os.path.abspath(os.path.join(self.project_root, module)), os.path.join(self.release_dir, self.project, "Addons")]
							else:
								cmd = [self.addonbuilder, include, os.path.abspath(os.path.join(self.project_root, module)), os.path.join(self.release_dir, self.project, "Addons")]

							color("grey")
							ret = subprocess.call(cmd,  stdout = subprocess.DEVNULL if self.quiet else None, stderr = subprocess.DEVNULL if self.quiet else None)
							color("reset")

							if ret == 0 and os.path.isfile(pbo_path):
								try:
									# Prettyprefix rename the PBO if requested.
									if self.pbo_name_prefix:
										try:
											os.rename(pbo_path, os.path.join(self.release_dir, self.project, "Addons", self.pbo_name_prefix + pbo))
										except:
											raise Exception("BadPBONamePrefix", "Could not rename PBO with prefix.")

									# Sign result
									if self.key:
										print("Signing with " + self.key + ".")
										if self.pbo_name_prefix:
											ret = subprocess.call([self.dssignfile, self.key, os.path.join(self.release_dir, self.project, "Addons", self.pbo_name_prefix + pbo)],  stdout = subprocess.DEVNULL if self.quiet else None, stderr = subprocess.DEVNULL if self.quiet else None)
										else:
											ret = subprocess.call([self.dssignfile, self.key, pbo_path],  stdout = subprocess.DEVNULL if self.quiet else None, stderr = subprocess.DEVNULL if self.quiet else None)

										if ret != 0:
											raise Exception("BadSign", "Could not sign PBO.")

									# Update the hash for a successfully built module
									if not self.force:
										self.cache[module] = new_sha

									success_count += 1
								except:
									raise
							else:
								if ret != 0:
									try:
										error_log = open(os.path.join(self.release_dir, self.project, "temp", pbo_name + "_packing.log"), 'r').readlines()

										print()
										print_error("Last 5 lines of build log %s:" % (os.path.join(self.release_dir, self.project, "temp", pbo_name + "_packing.log")))

										for line in error_log[-5:]:
											print(line, end="")
										print()
									except IOError:
										pass

								print_error("Module not successfully built/signed.")
								failed_count += 1
								input("Press Enter to continue...")
								print ("Resuming build...")
								continue
						except IOError:
							input("An error occurred. Press Enter to continue...")
							print ("Resuming build...")
							continue
					elif self.build_tool == "pboproject":
						print_error("pboProject is no longer supported as a build tool.")
					else:
						print_error("Unknown build tool %s." % self.build_tool)
				except:
					failed_count += 1
					raise

				finally:
					# Write out the cache state even if there was an exception
					cache_out = json.dumps(self.cache)
					with open(os.path.join(self.root, "make.cache"), 'w') as f:
						f.write(cache_out)
			else:
				print_error("Module %s does not exist." % module)
				failed_count += 1

		# Print report.
		if success_count + skipped_count > 0:
			print_green("Built %s modules. Skipped %s unchanged modules." % (success_count, skipped_count))
		if failed_count > 0:
			color("red")
			print("%s modules failed to build." % failed_count)
			color("reset")

		# Zip up the release dir if requested.
		if self.release:
			self.zip_release()

		# Copy the files to Arma 3 folder if requested.
		if self.test:
			self.copy_to_a3()

		# Clean up.
		try:
			os.remove(os.path.join(self.root, "~make.includes"))
		except IOError:
			pass

###############################################################################
###############################################################################
###############################################################################

def main(argv):
	"""Build an Arma addon suite in a directory from rules in a make.cfg file."""
	print_blue(("make for Arma 3, v%s" % __version__))

	if sys.platform != "win32":
		print_error("Non-Windows platform (Cygwin?). Please re-run from cmd.")
		sys.exit(1)

	# Get the directory the make script is in.
	root = os.path.dirname(os.path.realpath(__file__))
	os.chdir(root)

	# Parse command line switches
	if "help" in argv or "-h" in argv or "--help" in argv:
		print_help()
		sys.exit(0)

	target = "DEFAULT"
	force = False
	test = False
	release = False
	version = None

	if "force" in argv:
		force = True
		argv.remove("force")

	if "test" in argv:
		test = True
		argv.remove("test")

	if "release" in argv:
		release = True
		version = argv[argv.index("release") + 1]
		argv.remove(version)
		argv.remove("release")

	if "target" in argv:
		target = argv[argv.index("target") + 1]
		argv.remove("target")
		argv.remove(target)

	if "key" in argv:
		key = argv[argv.index("key") + 1]
		argv.remove("key")
		argv.remove(key)

	# Check for specific modules to build from command line (left over in argv).
	if len(argv) > 1:
		modules = argv[1:]

	# Create a new Make object and execute the build.
	try:
		make = Make(root, target = target, force = force, test = test, release = release, version = version)
		make.make()
	except:
		raise

if __name__ == "__main__":
	main(sys.argv)
