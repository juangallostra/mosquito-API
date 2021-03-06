#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Authors: Juan Gallostra (jgallostra<at>bonadrone.com) and Pep Marti-Saumell (jmarti<at>bonadrone.com>)
# Date: 12-12-2018

import time
import math
import mosquito.msppg as msppg
from mosquito.coms import MosquitoComms
from mosquito.notify import publisher, Subscriber

class Mosquito(MosquitoComms):
	"""
	API implementation to communicate with a Mosquito
	via WiFi based on MSP messages.

	The laptop should be connected to the Mosquito's Wifi.
	MSP message handling is delegated to Simon D. Levy's
	Hackflight's MSP Parser.

	For further info about the MSP parser see:
		- https://github.com/simondlevy/Hackflight/tree/master/extras/parser
		- http://www.multiwii.com/wiki/index.php?title=Multiwii_Serial_Protocol
	"""

	def __init__(self):
		"""
		Initialize the API instance and create
		a WiFi communication channel between laptop
		and Mosquito
		"""
		super(Mosquito, self).__init__()

		# Create subscribers, which will be used in our public get methods to retrieve
		# the requested values. A subscriber will be notified when its respective publisher
		# is called.
		self.__position_board_connected_sub = Subscriber()
		self.__firmware_version_sub = Subscriber()
		self.__attitude_sub = Subscriber()
		self.__velocities_sub = Subscriber()
		self.__motors_sub = Subscriber()
		self.__voltage_sub = Subscriber()
		self.__PID_sub = Subscriber()
		# Create publishers. The publishers will be set as the handlers of the MSP
		# messages. This way, they will be called when the appropriate MSP message
		# is received. When this happens, the publisher will notify its subscriber
		# and deliver the new value
		self.__position_board_connected_pub = publisher(self.__position_board_connected_sub)
		self.__firmware_version_pub = publisher(self.__firmware_version_sub)
		self.__attitude_pub = publisher(self.__attitude_sub)
		self.__velocities_pub = publisher(self.__velocities_sub)
		self.__motors_pub = publisher(self.__motors_sub)
		self.__voltage_pub = publisher(self.__voltage_sub)
		self.__PID_pub = publisher(self.__PID_sub)
		# Set the publishers as the MSP message handlers
		# They will be triggered when the appropriate message is received
		self._parser.set_POSITION_BOARD_CONNECTED_Handler(self.__position_board_connected_pub)
		self._parser.set_FIRMWARE_VERSION_Handler(self.__firmware_version_pub)
		self._parser.set_ATTITUDE_RADIANS_Handler(self.__attitude_pub)
		self._parser.set_GET_VELOCITIES_Handler(self.__velocities_pub)
		self._parser.set_GET_MOTOR_NORMAL_Handler(self.__motors_pub)
		self._parser.set_GET_BATTERY_VOLTAGE_Handler(self.__voltage_pub)
		self._parser.set_GET_PID_CONSTANTS_Handler(self.__PID_pub)
		# Mosquito's status attributes
		self.__motor_values = tuple([0]*4)
		self.__led_status = tuple([0]*3)
		self.__voltage = 0.0
		# Mosquito's PID constants
		self.__controller_constants = tuple([0]*19)

	# Public methods
	def position_board_connected(self):
		"""
		Check if the position board is connected to the Mosquito.

		:return: The status of the position board. True if connected and False otherwise
		:rtype: bool
		"""
		self._send_data(msppg.serialize_POSITION_BOARD_CONNECTED_Request())
		return bool(self.__position_board_connected_sub.get_value())

	def get_firmware_version(self):
		"""
		Get the version of the firmware running on the Mosquito

		:return: Firmware version
		:rtype: int
		"""
		self._send_data(msppg.serialize_FIRMWARE_VERSION_Request())
		return self.__firmware_version_sub.get_value()[0]

	def get_attitude(self, degrees=False):
		"""
		Get the orientation of the Mosquito

		:return: Orientation of the Mosquito in radians
		:rtype: tuple
		"""
		self._send_data(msppg.serialize_ATTITUDE_RADIANS_Request())
		attitude = self.__attitude_sub.get_value()
		if not degrees:
			return attitude
		return tuple([angle*180/math.pi for angle in attitude])

	def get_velocities(self):
		"""
		Get the linear velocities of the Mosquito

		:return: Linear velocities of the Mosquito in meters per second
		:rtype: tuple
		"""
		self._send_data(msppg.serialize_GET_VELOCITIES_Request())
		return self.__velocities_sub.get_value()

	def get_voltage(self):
		"""
		Get the voltage of the battery in the Mosquito. 
		If not connected it returns 0.0

		:return: Battery voltage in V
		:rtype: float
		"""
		self._send_data(msppg.serialize_GET_BATTERY_VOLTAGE_Request())
		return self.__voltage_sub.get_value()[0]

	def get_motors(self):
		"""
		Get the values of all motors

		:return: current motor values in the range 0-1. The values are ordered
		so that the position in the tuple matches the motor index
		:trype: tuple
		"""
		self._send_data(msppg.serialize_GET_MOTOR_NORMAL_Request())
		return self.__motors_sub.get_value()

	def get_PID(self):
		"""
		Get the constants of every PID controller in Hackflight.

		:return: current values for PID controllers. See 'set_PID()' documentation for tuple details
		:trype: tuple
		"""
		self._send_data(msppg.serialize_GET_PID_CONSTANTS_Request())
		return self.__PID_sub.get_value()

	def arm(self):
		"""
		Arm the Mosquito

		:return: None
		:rtype: None
		"""
		self._send_data(msppg.serialize_WP_ARM_Request())

	def disarm(self):
		"""
		Disarm the Mosquito

		:return: None
		:rtype: None
		"""
		self._send_data(msppg.serialize_WP_DISARM_Request())

	def set_position_board(self, has_position_board):
		"""
		Set if the Mosquito has the positoning board

		:param has_positioning_board: Indicates wether the Mosquito is equipped with
		a position board or not.
		:type has_positioning_board: bool
		:return: None
		:rtype: None
		"""
		self._send_data(msppg.serialize_SET_POSITIONING_BOARD(has_position_board))

	def set_mosquito_version(self, is_mosquito_90):
		"""
		Set the version of the Mosquito (True meaning Mosquito 90 and False meaning
		Mosquito 150)

		:param is_mosquito_90: Indicates the version of the Mosquito
		:type is_mosquito_90: bool
		:return: None
		:rtype: None
		"""
		self._send_data(msppg.serialize_SET_MOSQUITO_VERSION(is_mosquito_90))

	def calibrate_ESCs(self):
		"""
		Calibrate ESCs with the MultiShot protocol. When this message is sent,
		the calibration will be performed after powering off and on the board.

		:return: None
		:rtype: None
		"""
		self._send_data(msppg.serialize_ESC_CALIBRATION(0))

	def calibrate_transmitter(self, stage):
		"""
		Trigger the different stages of the transmitter calibration

		:param stage: Calibration stage
		:type stage: int in the range 0-2
		:return: None
		:rtype: None
		"""
		self._send_data(msppg.serialize_RC_CALIBRATION(stage))

	def set_motor(self, motor, value):
		"""
		Set the value of a motor

		:param motor: Target motor number to set the value (integer in the range 1-4)
		:type data: int
		:param value: Desired motor value in the range 0-1 being 1 maximum speed and 0 motor stopped
		:type value: float
		:return: None
		:trype: None
		"""
		motor_idx = motor-1
		values = tuple([self.__motor_values[i] if i != motor_idx else value for i in range(4)])
		# Setting a motor to a specific value should not reset the rest of motor values.
		# Since currently the MSP message to set a motor value requires the values of the
		# four motors we store the already set values and send them along the new one.
		self.set_motors(values)

	def set_motors(self, values):
		"""
		Set the values of all motors in the specified order

		:param values: 4 value list with desired motor values in
		the range 0-1 being 1 maximum speed and 0 motor stopped.
		:type values: list
		:return: None
		:trype: None
		"""
		self.__motor_values = values
		self._send_data(msppg.serialize_SET_MOTOR_NORMAL(*values))

	def set_voltage(self, voltage):
		"""
		Set the voltage of the battery in the Mosquito.
		This MSP message is only used by the ESP32 in
		order to send the computed voltage to the STM32.
		This message in the API can be used to override.

		:param voltage: battery voltage in V
		:type voltage: float
		:return: None
		:trype: None
		"""
		self.__voltage = voltage
		self._send_data(msppg.serialize_SET_BATTERY_VOLTAGE(voltage))

	def get_motor(self, motor):
		"""
		Get the value of a specific motors

		:param motor: Motor number whose value is wanted
		:type motor: int
		:return: current motor value in the range 0-1
		:trype: float
		"""
		motor_values = self.get_motors()
		return motor_values[motor-1]

	def set_PID(self, gyro_roll_P, gyro_roll_I, gyro_roll_D, gyro_pitch_P, gyro_pitch_I, gyro_pitch_D,
		gyro_yaw_P, gyro_yaw_I, demands_to_rate, level_P, altHold_P, altHold_vel_P, altHold_vel_I,
		altHold_vel_D, min_altitude, posHold_vel_P, posHold_vel_I, posHold_vel_D, param9):
		"""
		Set the constants of every PID controller in Hackflight.

		:param gyro_roll_P: Rate Roll controller. Proportional constant.
		:type gyro_roll_P: float
		:param gyro_roll_I: Rate Roll controller. Integral constant.
		:type gyro_roll_I: float
		:param gyro_roll_D: Rate Roll controller. Derivative constant.
		:type gyro_roll_D: float
		:param gyro_pitch_P: Rate Pitch controller. Proportional constant.
		:type gyro_pitch_P: float
		:param gyro_pitch_I: Rate Pitch controller. Integral constant.
		:type gyro_pitch_I: float
		:param gyro_pitch_D: Rate Pitch controller. Derivative constant.
		:type gyro_pitch_D: float		
		:param gyro_yaw_P: Rate Yaw controller. Proportional constant.
		:type gyro_yaw_P: float
		:param gyro_yaw_I: Rate Yaw controller. Proportional constant.
		:type gyro_yaw_I: float
		:param demands_to_rate: In rate mode, demands from RC are multiplied by demandstoRate.
		:type demands_to_rate: float
		:param level_P: Level Pitch & Roll controller. Proportional constant.
		:type level_P: float
		:param altHold_P: Altitude controller. Proportional constant.
		:type altHold_P: float
		:param altHold_vel_P: Vertical velocity controller. Proportional constant.
		:type altHold_vel_P: float
		:param altHold_vel_I: Vertical velocity controller. Integral constant.
		:type altHold_vel_I: float
		:param altHold_vel_D: Vertical velocity controller. Derivative constant.
		:type altHold_vel_D: float
		:param min_altitude: Minimum altitude, in meters.
		:type min_altitude: float
		:param posHold_vel_P: Horizontal velocity controller. Proportional constant.
		:type posHold_vel_P: float
		:param posHold_vel_I: Horizontal velocity controller. Integral constant.
		:type posHold_vel_I: float
		:param posHold_vel_D: Horizontal velocity controller. Derivative constant.
		:type posHold_vel_D: float
		:param param9: Param9
		:type param9: float
		:return: None
		:trype: None
		"""
		self.__controller_constants = gyro_roll_P, gyro_roll_I, gyro_roll_D, gyro_pitch_P, gyro_pitch_I, gyro_pitch_D, gyro_yaw_P, gyro_yaw_I, demands_to_rate, level_P, altHold_P, altHold_vel_P, altHold_vel_I, altHold_vel_D, min_altitude, posHold_vel_P, posHold_vel_I, posHold_vel_D, param9
		self._send_data(msppg.serialize_SET_PID_CONSTANTS(gyro_roll_P, gyro_roll_I, gyro_roll_D, gyro_pitch_P, gyro_pitch_I, gyro_pitch_D, gyro_yaw_P, gyro_yaw_I, demands_to_rate, level_P, altHold_P, altHold_vel_P, altHold_vel_I, altHold_vel_D, min_altitude, posHold_vel_P, posHold_vel_I, posHold_vel_D, param9))

	def set_leds(self, red=None, green=None, blue=None):
		"""
		Set the on/off state of the LEDs. If any of the LEDs
		is omitted in the method call its current status is preserved.

		:param red: Status of red LED. A True/1 value will turn the LED on and a False/0 value off
		:type red: bool
		:param green: Status of green LED. A True/1 value will turn the LED on and a False/0 value off
		:type green: bool
		:param blue: Status of blue LED. A True/1 value will turn the LED on and a False/0 value off
		:type blue: bool
		:return: None
		:rtype: None
		"""
		self.__led_status = tuple([self.__led_status[idx] if value is None else value for idx, value in enumerate([red, green, blue])])
		self._send_data(msppg.serialize_SET_LEDS(*self.__led_status))

	def clear_EEPROM(self, section):
		"""
		Clear all or a specific section of the EEPROM

		:param section: Section to clear. 0 - Parameters, 1 - Mission, 2 - all
		:type section: int
		:return: None
		:rtype: None
		"""
		self._send_data(msppg.serialize_CLEAR_EEPROM(section))

	def stop(self):
		"""
		Trigger an emergency stop that will hault the Mosquito and stop any action
		being performed

		:return: None
		:rtype: None
		"""
		self._send_data(msppg.serialize_SET_EMERGENCY_STOP(0))

	def execute_mission(self):
		"""
		Begin the execution of a flight mission stored in the EEPROM

		:return: None
		:rtype: None
		"""
		self._send_data(msppg.serialize_WP_MISSION_BEGIN(1))

	def take_off(self, height=100):
		"""
		Take off and hover at the specified height

		:param height: Target take off height. By default, this height is 1m. When reached, the drone will start hovering
		:type height: int
		:return: None
		:rtype: None
		"""
		self._send_data(msppg.serialize_WP_TAKE_OFF(height, 0))

	def land(self):
		"""
		Land the drone

		:return: None
		:rtype: None
		"""
		self._send_data(msppg.serialize_WP_LAND(0))

	def hover(self, time):
		"""
		Hover at the current position for the specified amount of time
		
		:param time: Number of seconds that the hover action should last
		:type time: int
		:return: None
		:rtype: None
		"""
		self._send_data(msppg.serialize_WP_HOVER(time, 0))

	def change_height(self, height):
		"""
		Set the target height at which the Mosquito
		should hover.

		:param height: The desired altitude in centimeters
		:type height: int
		:return: None
		:rtype: None
		"""
		self._send_data(msppg.serialize_WP_CHANGE_ALTITUDE(height, 0))

	def move_forward(self, time):
		"""
		Move forward for the specified amount of time

		:param time: Number of seconds the action should last
		:type time: int
		:return: None
		:rtype: None
		"""
		self._send_data(msppg.serialize_WP_GO_FORWARD(time, 0))

	def move_backwards(self, time):
		"""
		Move backwards for the specified amount of time

		:param time: Number of seconds the action should last
		:type time: int
		:return: None
		:rtype: None
		"""
		self._send_data(msppg.serialize_WP_GO_BACKWARD(time, 0))

	def move_left(self, time):
		"""
		Move left for the specified amount of time

		:param time: Number of seconds the action should last
		:type time: int
		:return: None
		:rtype: None
		"""
		self._send_data(msppg.serialize_WP_GO_LEFT(time, 0))

	def move_right(self, time):
		"""
		Move right for the specified amount of time

		:param time: Number of seconds the action should last
		:type time: int
		:return: None
		:rtype: None
		"""
		self._send_data(msppg.serialize_WP_GO_RIGHT(time, 0))

	def turn(self, angle):
		"""
		Turn the specified angle. If the angle is greater than 0 
		the rotation will be counter clockwise, and clockwise otherwise

		:param angle: Number of degrees the drone should turn
		:type angle: int
		:return: None
		:rtype: None
		"""
		if angle > 0:
			self._send_data(msppg.serialize_WP_TURN_CCW(angle, 0))
		else:
			self._send_data(msppg.serialize_WP_TURN_CW(angle, 0))
