# coding=utf-8
from __future__ import absolute_import

from .vector import Vector

import os
import time
import flask
import re
import subprocess
import threading
import logging
import logging.handlers
from pkg_resources import parse_version

import octoprint.plugin
import octoprint.util
import octoprint.slicing
import octoprint.settings

from octoprint.util.commandline import CommandlineError
from octoprint.util.paths import normalize as normalize_path
from octoprint.events import Events

from .profile import Profile

class InternalSlicer(octoprint.plugin.SettingsPlugin,
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
		# cancel button testing
		self.p = None

	def get_update_information(self):
		return dict(
			internal_slicer=dict(
				displayName="OctoPrint Internal Slicer",
				displayVersion=self._plugin_version,

				# version check: github repository
				type="github_release",
				user="Garr-Garr",
				repo="OctoPrint-InternalSlicer",
				current=self._plugin_version,

				# update method: pip
				pip="https://github.com/Garr-Garr/OctoPrint-InternalSlicer/archive/{target_version}.zip"
			)
		)

	##~~ AssetPlugin mixin
	def get_assets(self):
		return dict(
			js=["js/stats.min.js", "js/octoprint_slicer.min.js", "js/slic3r.js"],
			css=["css/internal_slicer.css"],
			less=["less/internal_slicer.less"]
		)

	##~~ StartupPlugin mixin
	def on_startup(self, host, port):
		self._slicer_logger = self._logger
		# setup our custom logger
		slicer_logging_handler = logging.handlers.RotatingFileHandler(self._settings.get_plugin_logfile_path(postfix="engine"), maxBytes=2*1024*1024)
		slicer_logging_handler.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
		slicer_logging_handler.setLevel(logging.DEBUG)

		self._slicer_logger.addHandler(slicer_logging_handler)
		self._slicer_logger.setLevel(logging.DEBUG if self._settings.get_boolean(["debug_logging"]) else logging.INFO)
		self._slicer_logger.propagate = False

	def on_after_startup(self):
		# Check if CPU limit is installed
		try:
			subprocess.check_output(["which", "cpulimit"])
			self._settings.set_boolean(["cpuLimitInstalled"], True)
			self._settings.save()
			self._logger.info("CPU Limit is installed.")
		except subprocess.CalledProcessError:
			self._logger.info("CPU Limit is not installed.")
		

	##~~ SettingsPlugin mixin
	def get_settings_defaults(self):
		return dict(
			slicer_engine="$HOME/slicers/PrusaSlicer-version_2.6.1-armhf.AppImage",
			offline_mode=False,
			default_profile=None,
			debug_logging=True,
			disableGUI = False,
			enableAutoBedTemp = False,
			enableCpuLimit = False, 
			cpuLimitInstalled = False,
			cpuLimit_Value = 100,
			wizard_version=0
		)
	
	def on_settings_save(self, data):
		settings = [
        	{"name": "disableGUI", "log_msg": "GUI"},
        	{"name": "debug_logging", "log_msg": "Debug logging"},
        	{"name": "enableAutoBedTemp", "log_msg": "Auto bed temp"},
        	{"name": "enableCpuLimit", "log_msg": "CPU Limit"},
        	{"name": "cpuLimitInstalled", "log_msg": "CPU Limit is installed"},
    	]

		old_values = {setting["name"]: self._settings.get_boolean([setting["name"]]) for setting in settings}
		octoprint.plugin.SettingsPlugin.on_settings_save(self, data)

		for setting in settings:
			new_value = self._settings.get_boolean([setting["name"]])

			#debuging
			#self._logger.info(f"Old value of {setting['name']}: {old_values[setting['name']]}")
			#self._logger.info(f"New value of {setting['name']}: {new_value}")
			if old_values[setting['name']] != new_value:
				if new_value:
					self._logger.info(f"{setting['log_msg']} enabled.")
				else:
					self._logger.info(f"{setting['log_msg']} disabled.")


	##~~ SimpleApiPlugin mixin
	def get_api_commands(self):
		return dict(
			download_prusaslicer_script=[],
			#offline_installation=[],
			test_reset_wizard=[],
			cancel_slice=[],
			installCPULimit=[]
			)

	def on_api_command(self, command, data):
		if command == 'download_prusaslicer_script':
			self.downloadPrusaslicer()
		if command == 'cancel_slice':
			self.cancel_slicing()
		if command == 'test_reset_wizard':
			self.reset_wizard()
		if command == 'installCPULimit':
			self.installCPULimit()

	##~~ WizardPlugin mixin
	#def on_wizard_finish(self):
		#self._logger.info("Wizard finished :)")
		#self._settings.set(["wizard_version"], 1)

	#def is_wizard_required(self):
		#if self._settings.get_boolean(["setup_done"]) is False:
			#self._logger.info("Setup wizard is required, running now (?)")
			#self._settings.set_boolean(["setup_done"], True)
			#self._settings.save()
		#return True
	
	#def get_wizard_version(self):
		#slicer_wizard_version = self._settings.get(["wizard_version"])
		# Returns 1 for the current wizard version, iterate wizard_version if you make changes to the wizard
		#return slicer_wizard_version
	
	#def reset_wizard(self):
		#self._settings.set(["wizard_version"], 0)
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
	
	def is_blueprint_csrf_protected(self):
		return True
	

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


	##~~ SlicerPlugin mixin
	def is_slicer_configured(self):
		# Check if slicer engine path is configured
		slicer_engine = normalize_path(self._settings.get(["slicer_engine"]))
		return slicer_engine is not None and os.path.exists(slicer_engine)
	
	def get_slicer_properties(self):
		return dict(
			type="prusa",
			name="PrusaSlicer v2.6.1",
			same_device=True,
			progress_report=False,
		)

	def get_slicer_profile(self, path):
		profile_dict, display_name, description = self._load_profile(path)
		properties = self.get_slicer_properties()
		return octoprint.slicing.SlicingProfile(properties["type"], ["name"], profile_dict, display_name=display_name, description=description)
	
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
			posX = int(position["x"])
			posY = int(position["y"])
		elif printer_profile["volume"]["formFactor"] == "circular" or printer_profile["volume"]["origin"] == "center":
			posX = 0
			posY = 0
		else:
			posX = int(printer_profile["volume"]["width"] / 2.0)
			posY = int(printer_profile["volume"]["depth"] / 2.0)
		self._logger.info("### Slicing %s to %s using profile stored at %s" % (model_path, machinecode_path, profile_path))

		executable = normalize_path(self._settings.get(["slicer_engine"]))
		if not executable:
			return False, "Path to Slicer is not configured "

		args = ['"%s"' % executable, '--export-gcode', '--load', '"%s"' % profile_path, '-o', '"%s"' % machinecode_path, '"%s"' % model_path, '--center', '%s,%s' % (posX, posY)]
		env = {}

		import sarge
		import psutil
		working_dir, _ = os.path.split(executable)
		command = " ".join(args)
		self._logger.info("Running %r in %s" % (command, working_dir))
		
		try:
			if parse_version(sarge.__version__) >= parse_version('0.1.5'): # Because in version 0.1.5 the name was changed in sarge.
				async_kwarg = 'async_'
			else:
				async_kwarg = 'async'

			p = sarge.capture_both(command, cwd=working_dir, **{async_kwarg: True})
			p.wait_events()

			#throttle the process to prevent the raspberry pi from overheating			
			if self._settings.get(["enableCpuLimit"]) and self._settings.get(["cpuLimitInstalled"]) is True:
				try:
					time.sleep(5)
					# use pgrep to find the PID of the process "slic3r_main"
					command_pid = subprocess.Popen(["pgrep", "slic3r_main"], stdout=subprocess.PIPE).communicate()[0].decode('utf-8').strip()
					self._logger.info(f"PID of the process: {command_pid}")
					cpulimit_process = subprocess.Popen(["cpulimit", "-l", self._settings.get(["cpuLimit_Value"]), "-p", str(command_pid)])

				except subprocess.CalledProcessError:
					self._logger.info("CPU Limit is not installed")

			#open the profile_path file, locate the value of "first_layer_bed_temperature", and then set the bed temperature to that value
			if self._settings.get(["enableAutoBedTemp"]):
				with open(profile_path, "r") as f:
					for line in f:
						if "first_layer_bed_temperature =" in line:
							bed_temp = line.split("=")[1].strip()
							if int(bed_temp) > 0:
								self._logger.info(f"Bed temperature: {bed_temp}")
								self._printer.set_temperature("bed", int(bed_temp))
							else:
								self._logger.info("Bed temp: 0, not setting bed temperature")

			# custom alert testing
			# self._plugin_manager.send_plugin_message(self._identifier, dict(alert="popup", msg="This is a popup message"))
			# self._plugin_manager.send_plugin_message(self._identifier, dict(alert="warning", msg="Custom warning message"))

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

				if self._settings.get(["enableCpuLimit"]) and self._settings.get(["cpuLimitInstalled"]) is True:
					cpulimit_process.kill()

				with self._cancelled_jobs_mutex:
					if machinecode_path in self._cancelled_jobs:
						self._logger.info("### Cancelled")
						raise octoprint.slicing.SlicingCancelled()
					
				self._logger.info("### Finished, returncode %d" % p.returncode)

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

	def _load_profile(self, path):
		profile, display_name, description = Profile.from_slicer_ini(path)
		return profile, display_name, description

	def _save_profile(self, path, profile, allow_overwrite=True, display_name=None, description=None):
		if not allow_overwrite and os.path.exists(path):
			raise IOError("Cannot overwrite {path}".format(path=path))
		Profile.to_slicer_ini(profile, path, display_name=display_name, description=description)


	##~~ Custom Functions
	def installCPULimit(self):
		# Check if CPU Limit is installed
		if self._settings.get(["cpuLimitInstalled"]) is True:
			self._plugin_manager.send_plugin_message("internal_slicer", dict(slicerCommandResponse = "CPU Limit is already installed!"))
			self._logger.info("CPU Limit is already installed!")
			return
		
		try: 
			self._plugin_manager.send_plugin_message("internal_slicer", dict(slicerCommandResponse = "Installing CPU Limit"))
			self._logger.info("Installing CPU Limit")
			proc = subprocess.Popen(["sudo", "apt-get", "install", "cpulimt"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
			for line in proc.stdout:
				# Send the output to the logs
				self._logger.info(line)
				# Send the output to the client
				self._plugin_manager.send_plugin_message("internal_slicer", dict(slicerCommandResponse = line))

		except CommandlineError as err:
			self._plugin_manager.send_plugin_message("internal_slicer", dict(slicerCommandResponse = "Installation failed. You may need to log into the Pi via SSH first: https://github.com/Garr-Garr/OctoPrint-InternalSlicer/wiki/RPi-Slicing-Benchmarks"))
		#else:
			self._plugin_manager.send_plugin_message("internal_slicer", dict(slicerCommandResponse = "CPULimit installed successfully!"))
			self._settings.set_boolean(["cpuLimitInstalled"], True)
			self._settings.save()

	def cancel_slicing(self): # , machinecode_path?
		if self.p is not None:
			self.p.terminate()
		# with self._slicing_commands_mutex:
		# 	if machinecode_path in self._slicing_commands:
		# 		with self._cancelled_jobs_mutex:
		# 			self._cancelled_jobs.add(machinecode_path)
		# 		self._slicing_commands[machinecode_path].terminate()
		# 		self.p.terminate()
		# 		self._logger.info("Cancelled slicing of %s" % machinecode_path)

	def downloadPrusaslicer(self):
		self._logger.info("Starting PrusaSlicer v2.6.1 download")

		# If PrusaSlicer
		if os.access(os.path.expanduser("~/slicers/PrusaSlicer-version_2.6.1-armhf.AppImage"), os.X_OK):
			self._plugin_manager.send_plugin_message("internal_slicer", dict(slicerCommandResponse = "PrusaSlicer is already installed!"))
			self._logger.info("PrusaSlicer is already installed!")
			return
		
		# Get the path to the shell script
		script_path = (self._basefolder+"/static/scripts/downloadPrusaSlicer.sh")

		# Create a subprocess object
		proc = subprocess.Popen(["bash", script_path], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

		# Read all the lines of the output
		for line in proc.stdout:
			# Send the output to the logs
			self._logger.info(line)
			# Send the output to the client
			self._plugin_manager.send_plugin_message("internal_slicer", dict(slicerCommandResponse = line))

		# Wait for the process to finish
		if proc.poll() is not None and os.access(os.path.expanduser("~/slicers/PrusaSlicer-version_2.6.1-armhf.AppImage"), os.X_OK):
			self._plugin_manager.send_plugin_message("internal_slicer", dict(slicerCommandResponse = "PrusaSlicer has been installed!"))
			self._logger.info("PrusaSlicer has been installed!")
			self.is_slicer_configured()

		else:
			self._plugin_manager.send_plugin_message("internal_slicer", dict(slicerCommandResponse = "The PrusaSlicer installation has failed Maybe try downloading the offline installation?" + 
														   									" https://github.com/Garr-Garr/OctoPrint-InternalSlicer/archive/refs/heads/offline.zip"))
			self._logger.info("The PrusaSlicer installation has failed")	

	def slic3rProfileCleanup(self, input, output) :
		# Slic3r and PrusaSlicer profile cleanup

		# Create output
		output = open(output, "wb")

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
__plugin_name__ = "Internal Slicer"
__plugin_pythoncompat__ = ">=2.7,<4"

def __plugin_load__():
	global __plugin_implementation__
	__plugin_implementation__ = InternalSlicer()

	global __plugin_hooks__
	__plugin_hooks__ = {
		"octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information
	}
