# coding=utf-8
from __future__ import absolute_import

from .vector import Vector

import uuid
import tempfile
import os
import time
import struct
import shutil
import sys
import math
import copy
import flask
import serial
import serial.tools.list_ports
import binascii
import re
import collections
import hashlib
import json
import imp
import glob
import ctypes
import _ctypes
import platform
import subprocess
import psutil
import socket
import threading
import yaml
import requests
import logging
import logging.handlers
from collections import defaultdict
from pkg_resources import parse_version

import octoprint.plugin
import octoprint.util
import octoprint.slicing
import octoprint.settings

from octoprint.util.paths import normalize as normalize_path
from octoprint.events import Events

from .profile import Profile

class NewSlicerPlugin(octoprint.plugin.SettingsPlugin,
                   octoprint.plugin.AssetPlugin,
		   		   octoprint.plugin.SlicerPlugin,
                   octoprint.plugin.TemplatePlugin,
		   		   octoprint.plugin.SimpleApiPlugin,
				   octoprint.plugin.BlueprintPlugin,
				   octoprint.plugin.StartupPlugin,
				   octoprint.plugin.EventHandlerPlugin,
				   octoprint.plugin.WizardPlugin):

	def __init__(self):
		# setup job tracking across threads
		self._slicing_commands = dict()
		self._slicing_commands_mutex = threading.Lock()
		self._cancelled_jobs = []
		self._cancelled_jobs_mutex = threading.Lock()

	def get_update_information(self):
		# Define the configuration for your plugin to use with the Software Update
		# Plugin here. See https://github.com/foosel/OctoPrint/wiki/Plugin:-Software-Update
		# for details.
		return dict(
			slicer=dict(
				displayName="New Slicer",
				displayVersion=self._plugin_version,

				# version check: github repository
				type="github_release",
				user="Garr-R",
				repo="OctoPrint-Slicer",
				current=self._plugin_version,

				# update method: pip
				pip="https://github.com/Garr-R/OctoPrint-Slicer/archive/{target_version}.zip"
			)
		)

	##~~ AssetPlugin mixin
	def get_assets(self):
		# Define your plugin's asset files to automatically include in the
		# core UI here.
		return dict(
			js=["js/stats.min.js", "js/octoprint_slicer.min.js", "js/slic3r.js"],
			css=["css/slicer.css", "css/slic3r.css"],
			less=["less/slicer.less"]
		)

	##~~ SettingsPlugin mixin
	def get_settings_defaults(self):
		return dict(
			slicer_engine="/home/pi/PrusaSlicer-2.4.2/prusa-slicer",
			default_profile=None,
			debug_logging=False
			#wizard_version=1
		)
	
	def on_settings_save(self, data):
		slicer_engine = self._settings.get([slicer_engine])
		
		old_debug_logging = self._settings.get_boolean(["debug_logging"])
		octoprint.plugin.SettingsPlugin.on_settings_save(self, data)

		new_debug_logging = self._settings.get_boolean(["debug_logging"])
		if old_debug_logging != new_debug_logging:
			if new_debug_logging:
				self._logger.setLevel(logging.DEBUG)
			else:
				self._logger.setLevel(logging.CRITICAL)

	##~~ StartupPlugin mixin
	# Copy PrusaSlicer download script to scripts folder on startup
	# TODO: use hashlib to compare files and only copy if different
	def on_startup(self, host, port):
		self._slicer_logger = self._logger
		# setup our custom logger
		slicer_logging_handler = logging.handlers.RotatingFileHandler(self._settings.get_plugin_logfile_path(postfix="engine"), maxBytes=2*1024*1024)
		slicer_logging_handler.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
		slicer_logging_handler.setLevel(logging.DEBUG)

		self._slicer_logger.addHandler(slicer_logging_handler)
		self._slicer_logger.setLevel(logging.DEBUG if self._settings.get_boolean(["debug_logging"]) else logging.CRITICAL)
		self._slicer_logger.propagate = False

	def on_after_startup(self):
		src_files = os.listdir(self._basefolder+"/static/scripts")
		src = (self._basefolder+"/static/scripts")
		dest = ("/home/pi/.octoprint/scripts")

		for file_name in src_files:
			full_src_name = os.path.join(src, file_name)
			full_dest_name = os.path.join(dest, file_name)
			if not (os.path.isfile(full_dest_name)):
				shutil.copy(full_src_name, dest)
				os.chmod(full_dest_name, 0o755)
				self._logger.info("Had to copy "+file_name+" to scripts folder.")
			else:
				if not self.hashMatches(full_src_name, full_dest_name):
					shutil.copy(full_src_name, dest)
					self._logger.info("Had to overwrite {} with new version.".format(file_name))
					os.chmod(full_dest_name, 0o755)

	##~~ SimpleApiPlugin mixin
	def get_api_commands(self):
		return dict(
			test_download_prusaslicer=[],
			test_reset_wizard=[]
			)

	def on_api_command(self, command, data):
		if command == 'test_download_prusaslicer':
			self.download_prusaslicer()
		if command == 'test_reset_wizard':
			self.reset_wizard()

	##~~ WizardPlugin mixin
	#def on_wizard_finish(self):
		#self._logger.info("Wizard finished :)")
		#self._settings.set(["wizard_version"], 2)

	#def is_wizard_required(self):
		#if self._settings.get_boolean(["setup_done"]) is False:
			#self._logger.info("Setup wizard is required, running now (?)")
			#self._settings.set_boolean(["setup_done"], True)
			#self._settings.save()
		#return True
	
	#ef get_wizard_version(self):
		#slicer_wizard_version = self._settings.get(["wizard_version"])
		# Returns 1 for the current wizard version, iterate wizard_version if you make changes to the wizard
		#return slicer_wizard_version
	
	#def reset_wizard(self):
		#self._settings.set(["wizard_version"], 1)
		#self._settings.save()

	##~~ BlueprintPlugin mixin
	@octoprint.plugin.BlueprintPlugin.route("/import", methods=["POST"])
	def importSlicerProfile(self):
		import datetime
		import tempfile
		input_name = "file"
		input_upload_name = input_name + "." + self._settings.global_get(["server", "uploads", "nameSuffix"])
		input_upload_path = input_name + "." + self._settings.global_get(["server", "uploads", "pathSuffix"])
		
		if input_upload_name in flask.request.values and input_upload_path in flask.request.values:
			filename = flask.request.values[input_upload_name]
			try:
				profile_dict, imported_name, imported_description = Profile.from_slicer_ini(flask.request.values[input_upload_path])
			except Exception as e:
				return flask.make_response("Something went wrong while converting imported profile: {message}".format(e.message), 500)

		elif input_name in flask.request.files:
			temp_file = tempfile.NamedTemporaryFile("wb", delete=False)
			try:
				temp_file.close()
				upload = flask.request.files[input_name]
				upload.save(temp_file.name)
				profile_dict, imported_name, imported_description = Profile.from_slicer_ini(temp_file.name)
			except Exception as e:
				return flask.make_response("Something went wrong while converting imported profile: {message}".format(e.message), 500)
			finally:
				os.remove(temp_file)
			filename = upload.filename

		else:
			return flask.make_response("No file included", 400)
		
		name, _ = os.path.splitext(filename)

		# default values for name, display name and description
		profile_name = name
		profile_display_name = imported_name if imported_name is not None else name
		profile_description = imported_description if imported_description is not None else "Imported from {filename} on {date}".format(filename=filename, date=octoprint.util.get_formatted_datetime(datetime.datetime.now()))
		profile_allow_overwrite = False

		# overrides
		if "name" in flask.request.values:
			profile_name = flask.request.values["name"]
		if "displayName" in flask.request.values:
			profile_display_name = flask.request.values["displayName"]
		if "description" in flask.request.values:
			profile_description = flask.request.values["description"]
		if "allowOverwrite" in flask.request.values:
			from octoprint.server.api import valid_boolean_trues
			profile_allow_overwrite = flask.request.values["allowOverwrite"] in valid_boolean_trues

		# Save profile
		self._slicing_manager.save_profile("prusa",
										profile_name,
										profile_dict,
										allow_overwrite=profile_allow_overwrite,
										display_name=profile_display_name,
										description=profile_description)

		result = dict(
			resource=flask.url_for("api.slicingGetSlicerProfile", slicer="prusa", name=profile_name, _external=True),
			displayName=profile_display_name,
			description=profile_description
		)
		r = flask.make_response(flask.jsonify(result), 201)
		r.headers["Location"] = result["resource"]
		return r

	# Upload 3D model event
	@octoprint.plugin.BlueprintPlugin.route("/upload", methods=["POST"])
	def upload(self) :
		# Check if uploading everything
		if "Slicer Profile Name" in flask.request.values and "Slicer Name" in flask.request.values and "Printer Profile Name" in flask.request.values and "Slicer Profile Content" in flask.request.values and "After Slicing Action" in flask.request.values :

			# Check if printing after slicing and a printer isn't connected
			if flask.request.values["After Slicing Action"] != "none" and self._printer.is_closed_or_error() :

				# Return error
				return flask.jsonify(dict(value = "Error"))

			# Set if model was modified
			modelModified = "Model Name" in flask.request.values and "Model Location" in flask.request.values and "Model Path" in flask.request.values and "Model Center X" in flask.request.values and "Model Center Y" in flask.request.values

			# Check if slicer profile, model name, or model path contain path traversal
			if "../" in flask.request.values["Slicer Profile Name"] or (modelModified and ("../" in flask.request.values["Model Name"] or "../" in flask.request.values["Model Path"])) :

				# Return error
				return flask.jsonify(dict(value = "Error"))

			# Check if model location is invalid
			if modelModified and (flask.request.values["Model Location"] != "local" and flask.request.values["Model Location"] != "sdcard") :

				# Return error
				return flask.jsonify(dict(value = "Error"))

			# Set model location
			if modelModified :

				if flask.request.values["Model Location"] == "local" :
					modelLocation = self._file_manager.path_on_disk(octoprint.filemanager.destinations.FileDestinations.LOCAL, flask.request.values["Model Path"] + flask.request.values["Model Name"]).replace('\\', '/')
				elif flask.request.values["Model Location"] == "sdcard" :
					modelLocation = self._file_manager.path_on_disk(octoprint.filemanager.destinations.FileDestinations.SDCARD, flask.request.values["Model Path"] + flask.request.values["Model Name"]).replace('\\', '/')

			# Check if slicer profile, model, or printer profile doesn't exist
			if (modelModified and not os.path.isfile(modelLocation)) or not self._printer_profile_manager.exists(flask.request.values["Printer Profile Name"]) :

				# Return error
				return flask.jsonify(dict(value = "Error"))

			# Move original model to temporary location
			if modelModified :
				fd, modelTemp = tempfile.mkstemp()
				os.close(fd)
				shutil.copy(modelLocation, modelTemp)

			fd, temp = tempfile.mkstemp()
			os.close(fd)

			output = open(temp, "wb")
			for character in flask.request.values["Slicer Profile Content"] :
				output.write(chr(ord(character)))
			output.close()

			self.tempProfileName = "temp-" + str(uuid.uuid1())
			if flask.request.values["Slicer Name"] == "prusa" :
				self.convertSlicerToProfile(temp, '', '', '')

			# Remove temporary file
			os.remove(temp)

			# Get printer profile
			printerProfile = self._printer_profile_manager.get(flask.request.values["Printer Profile Name"])

			# Save slicer changes
			self.slicerChanges = {
				"Printer Profile Content": copy.deepcopy(printerProfile)
			}

			# Otherwise check if slicer is Slic3r
			if flask.request.values["Slicer Name"] == "prusa" :

				# Change printer profile
				search = re.findall("bed_size\s*?=\s*?(\d+.?\d*)\s*?,\s*?(\d+.?\d*)", flask.request.values["Slicer Profile Content"])
				if len(search) :
					printerProfile["volume"]["width"] = float(search[0][0])
					printerProfile["volume"]["depth"] = float(search[0][1])

				search = re.findall("nozzle_diameter\s*?=\s*?(\d+.?\d*)", flask.request.values["Slicer Profile Content"])
				if len(search) :
					printerProfile["extruder"]["nozzleDiameter"] = float(search[0])

			# Check if modifying model
			if modelModified :

				# Save model locations
				self.slicerChanges["Model Location"] = modelLocation
				self.slicerChanges["Model Temporary"] = modelTemp

				# Adjust printer profile so that its center is equal to the model's center
				printerProfile["volume"]["width"] += float(flask.request.values["Model Center X"]) * 2
				printerProfile["volume"]["depth"] += float(flask.request.values["Model Center Y"]) * 2

			# Otherwise check if using a Micro 3D printer
			elif not self._settings.get_boolean(["NotUsingAMicro3DPrinter"]) :

				# Set extruder center
				extruderCenterX = (self.bedLowMaxX + self.bedLowMinX) / 2
				extruderCenterY = (self.bedLowMaxY + self.bedLowMinY + 14.0) / 2

				# Adjust printer profile so that its center is equal to the model's center
				printerProfile["volume"]["width"] += (-(extruderCenterX - (self.bedLowMaxX + self.bedLowMinX) / 2) + self.bedLowMinX) * 2
				printerProfile["volume"]["depth"] += (extruderCenterY - (self.bedLowMaxY + self.bedLowMinY) / 2 + self.bedLowMinY) * 2

			# Apply printer profile changes
			self._printer_profile_manager.save(printerProfile, True)

			fd, destFile = tempfile.mkstemp()
			os.close(fd)
			self._slicing_manager.slice(flask.request.values["Slicer Name"],
					modelLocation, #source path
					destFile,
					self.tempProfileName,
					self)

			# Return ok
			return flask.jsonify(dict(value = "OK"))

		# Return error
		return flask.jsonify(dict(value = "Error"))

	##~~ EventHandlerPlugin mixin
	def on_event(self, event, payload):
		# check if event is slicing started
		if event == octoprint.events.Events.SLICING_STARTED :

			# Set processing slice
			self.processingSlice = True

		# Otherwise check if event is slicing done, cancelled, or failed
		elif event == octoprint.events.Events.SLICING_DONE or event == octoprint.events.Events.SLICING_CANCELLED or event == octoprint.events.Events.SLICING_FAILED :

			# Clear processing slice
			self.processingSlice = False

			# Restore files
			self.restoreFiles()

	##~~ SlicerPlugin mixin
	def is_slicer_configured(self):
		# Check if slicer engine path is configured
		slicer_engine = normalize_path(self._settings.get(["slicer_engine"]))
		return slicer_engine is not None and os.path.exists(slicer_engine)
	
	def get_slicer_properties(self):
		return dict(
			type="prusa",
			name="PrusaSlicer v2.4.2",
			same_device=True,
			progress_report=False,
		)

	def get_slicer_default_profile(self):
		path = self._settings.get(["default_profile"])
		if not path:
			path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "profiles", "test_M2.ini")
		return self.get_slicer_profile(path)

	def get_slicer_profile(self, path):
		profile_dict, display_name, description = self._load_profile(path)
		properties = self.get_slicer_properties()
		return octoprint.slicing.SlicingProfile(properties["type"], "unknown", profile_dict, display_name=display_name, description=description)
	
	def save_slicer_profile(self, path, profile, allow_overwrite=True, overrides=None):
		from octoprint.util import dict_merge
		if overrides is not None:
			new_profile = dict_merge(profile.data, overrides)
		else:
			new_profile = profile.data
		if self._settings.get(["default_profile"]) is None:
			self._settings.set(["default_profile"], path)
			self._settings.save()
		self._save_profile(path, new_profile, allow_overwrite=allow_overwrite, display_name=profile.display_name, description=profile.description)

	# Slicing process
	def do_slice(self, model_path, printer_profile, machinecode_path=None, profile_path=None, position=None, on_progress=None, on_progress_args=None, on_progress_kwargs=None):
		if on_progress is not None:
			if on_progress_args is None:
				on_progress_args = ()
			if on_progress_kwargs is None:
				on_progress_kwargs = dict()
			on_progress_kwargs["_progress"] = 0
			on_progress(*on_progress_args, **on_progress_kwargs)

		if not profile_path:
			profile_path = self._settings.get(["default_profile"])
		
		if not machinecode_path:
			path, _ = os.path.splitext(model_path)
			machinecode_path = path + ".gcode"
    
		if position and isinstance(position, dict) and "x" in position and "y" in position:
			posX = position["x"]
			posY = position["y"]
		elif printer_profile["volume"]["formFactor"] == "circular" or printer_profile["volume"]["origin"] == "center" :
			posX = 0
			posY = 0
		else:
			posX = printer_profile["volume"]["width"] / 2.0
			posY = printer_profile["volume"]["depth"] / 2.0
    
		self._logger.info("### Slicing %s to %s using profile stored at %s" % (model_path, machinecode_path, profile_path))

		executable = normalize_path(self._settings.get(["slicer_engine"]))
		if not executable:
			return False, "Path to Slicer is not configured "

		args = ['"%s"' % executable, '--export-gcode', '--load', '"%s"' % profile_path,   '-o', '"%s"' % machinecode_path, '"%s"' % model_path]
		env = {}

		import sarge
		working_dir, _ = os.path.split(executable)
		command = " ".join(args)
		self._logger.info("Running %r in %s" % (command, working_dir))
		
		try:
			if parse_version(sarge.__version__) >= parse_version('0.1.5'): # Because in version 0.1.5 the name was changed in sarge.
				async_kwarg = 'async_'
			else:
				async_kwarg = 'async'
			p = sarge.run(command, cwd=working_dir, stdout=sarge.Capture(buffer_size=1), stderr=sarge.Capture(buffer_size=1), env=env, **{async_kwarg: True})
			p.wait_events()
			last_error=""
			
			try:
				with self._slicing_commands_mutex:
					self._slicing_commands[machinecode_path] = p.commands[0]

				stdout_buffer = b""
				stderr_buffer = b""
				total_layers = 1
				matched_lines = 0
				
				while p.returncode is None:
					p.commands[0].poll()
					# Can't use readline because it removes newlines and we can't tell if we have gotten a full line.
					stdout_buffer += p.stdout.read(block=False)
					stderr_buffer += p.stderr.read(block=False)

					stdout_lines = stdout_buffer.split(b'\n')
					stdout_buffer = stdout_lines[-1]
					stdout_lines = stdout_lines[0:-1]
					for stdout_line in stdout_lines:
						self._logger.debug("stdout: " + str(stdout_line))
						print(stdout_line.decode('utf-8'))
						m = re.search(r"\[trace\].*layer ([0-9]+)", stdout_line.decode('utf-8'))
						if m:
							matched_lines += 1
							current_layer = int(m.group(1))
							total_layers = max(total_layers, current_layer)
							if on_progress is not None:
								print("sending progress" + str(matched_lines / total_layers / 4))
								on_progress_kwargs["_progress"] = matched_lines / total_layers / 4
								on_progress(*on_progress_args, **on_progress_kwargs)

					stderr_lines = stderr_buffer.split(b'\n')
					stderr_buffer = stderr_lines[-1]
					stderr_lines = stderr_lines[0:-1]
					for stderr_line in stderr_lines:
						self._logger.debug("stderr: " + str(stderr_line))
						if len(stderr_line.strip()) > 0:
							last_error = stderr_line.strip()
			finally:
				if stdout_buffer:
					stdout_lines = stdout_buffer.split(b'\n')
					for stdout_line in stdout_lines:
						self._logger.debug("stdout: " + str(stdout_line))

				if stderr_buffer:
					stderr_lines = stderr_buffer.split(b'\n')
					for stderr_line in stderr_lines:
						self._logger.debug("stderr: " + str(stderr_line))
						if len(stderr_line.strip()) > 0:
							last_error = stderr_line.strip()
				p.close()

				with self._cancelled_jobs_mutex:
					if machinecode_path in self._cancelled_jobs:
						self._logger.info("### Cancelled")
						raise octoprint.slicing.SlicingCancelled()

				self._logger.info("### Finished, returncode %d" % p.returncode)
				
				#TODO: get analysis from gcode
				#if p.returncode == 0:
				#	analysis = get_analysis_from_gcode(machinecode_path)
				#	self._slic3r_logger.info("Analysis found in gcode: %s" % str(analysis))
				#	if analysis:
				#		analysis = {'analysis': analysis}
				#	return True, analysis
				#else:
				#	self._logger.warn("Could not slice via Slic3r, got return code %r" % p.returncode)
				#	self._logger.warn("Error was: %s" % last_error)
				#	return False, "Got returncode %r: %s" % (p.returncode, last_error)

		except octoprint.slicing.SlicingCancelled as e:
			raise e
		except:
			self._logger.exception("Could not slice via Slicer, got an unknown error")
			return False, "Unknown error, please consult the log file"

		finally:
			with self._cancelled_jobs_mutex:
				if machinecode_path in self._cancelled_jobs:
					self._cancelled_jobs.remove(machinecode_path)
			with self._slicing_commands_mutex:
				if machinecode_path in self._slicing_commands:
					del self._slicing_commands[machinecode_path]
			self._logger.info("-" * 40)

	def cancel_slicing(self, machinecode_path):
		with self._slicing_commands_mutex:
			if machinecode_path in self._slicing_commands:
				with self._cancelled_jobs_mutex:
					self._cancelled_jobs.add(machinecode_path)
				self._slicing_commands[machinecode_path].terminate()
				self._logger.info("Cancelled slicing of %s" % machinecode_path)

	def _load_profile(self, path):
		profile, display_name, description = Profile.from_slicer_ini(path)
		return profile, display_name, description

	def _save_profile(self, path, profile, allow_overwrite=True, display_name=None, description=None):
		if not allow_overwrite and os.path.exists(path):
			raise IOError("Cannot overwrite {path}".format(path=path))
		Profile.to_slicer_ini(profile, path, display_name=display_name, description=description)

	##~~ Move this to the bottom
	def download_prusaslicer(self):
		self._logger.info("Starting PrusaSlicer v2.4.2 download")

		# Get the path to the shell script
		script_path = "/home/pi/.octoprint/scripts/downloadPrusaSlicer.sh"

		# Create a subprocess object
		proc = subprocess.Popen(["bash", script_path], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
		
		# Read all the lines of the output
		for line in proc.stdout:
			# Send the output to the logs
			self._logger.info(line)
			# Send the output to the client
			self._plugin_manager.send_plugin_message("slicer", dict(slicerCommandResponse = line))

	def restoreFiles(self) :
		# Check if slicer was changed
		if self.slicerChanges is not None :

			# Move original files back
			os.remove(self.slicerChanges["Slicer Profile Location"])
			shutil.move(self.slicerChanges["Slicer Profile Temporary"], self.slicerChanges["Slicer Profile Location"])

			if "Model Temporary" in self.slicerChanges :
				os.remove(self.slicerChanges["Model Location"])
				shutil.move(self.slicerChanges["Model Temporary"], self.slicerChanges["Model Location"])

			# Restore printer profile
			self._printer_profile_manager.save(self.slicerChanges["Printer Profile Content"], True)

			# Clear slicer changes
			self.slicerChanges = None

	def hashMatches(self, fileA, fileB):
	# function to compare the MD5 hash of two files, returning True if they match, and False if they do not match;
	# this is close enough for our needs to confirming that the files are identical
		if ((hashlib.md5(open(fileA).read().encode()).hexdigest()) == (hashlib.md5(open(fileB).read().encode()).hexdigest())):
			return True
		else:
			return False
		
	#TODO: Re-enable this later (was originally named _sanitize_name)
	def sanitizeName(name):
		if name is None:
			return None
		
		if "/" in name or "\\" in name:
			raise ValueError("Name must not contain slashes")
		
		import string
		valid_chars = "-_.() {ascii}{digits}".format(ascii=string.ascii_letters, digits=string.digits)
		sanitized_name = ''.join(c for c in name if c in valid_chars)
		sanitized_name = sanitized_name.replace(" ", "_")
		return sanitized_name.lower()

	# Slic3r profile cleanup
	#TODO: I don't think this is needed anymore, disabled for now (4/13/2023)
	def slic3rProfileCleanUp(self, input, output) :
		# Create output
		output = open(output, "wb")

		# Go through all lines in input
		for line in open(input) :
			# Remove comments from input
			if ';' in line and "_gcode" not in line and line[0] != '\t' :
				output.write(line[0 : line.index(';')] + '\n')
			else :
				output.write(line)
		# Close output
		output.close()

# If you want your plugin to be registered within OctoPrint under a different name than what you defined in setup.py
# ("OctoPrint-PluginSkeleton"), you may define that here. Same goes for the other metadata derived from setup.py that
# can be overwritten via __plugin_xyz__ control properties. See the documentation for that.
__plugin_name__ = "Slicer"
__plugin_pythoncompat__ = ">=2.7,<4"

def __plugin_load__():
	global __plugin_implementation__
	__plugin_implementation__ = NewSlicerPlugin()

	global __plugin_hooks__
	__plugin_hooks__ = {
		"octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information
	}
