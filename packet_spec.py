"""
packet_spec.py

This file contains dataclass definitions of the packet header and packets from the packet specification, and methods to parse
byte streams into their respective classes
"""

from dataclasses import dataclass, asdict
from abc import ABC
from enum import Enum
import struct

from data_conversions import *

class PacketType(Enum):
    CONTROL = 0
    TELEMETRY = 1

class TelemetryPacketSubType(Enum):
    TEMPERATURE = 0
    PRESSURE = 1
    MASS = 2
    ARMING_STATE = 3
    ACT_STATE = 4
    WARNING = 5
    ACT_REQ = 6
    ACT_ACK = 7
    ARM_REQ = 8
    ARM_ACK = 9

class ActuationRequestStatus(Enum):
    ACT_OK = 0
    ACT_DENIED = 1
    ACT_DNE = 2
    ACT_INV = 3


class ArmingState(Enum):
    ARMED_PAD = 0
    ARMED_VALVES = 1
    ARMED_IGNITION = 2
    ARMED_DISCONNECTED = 3
    ARMED_LAUNCH = 4

class Warning(Enum):
    HIGH_PRESSURE = 0
    HIGH_TEMP = 1

class ActuatorState(Enum):
    OFF = 0
    ON = 1

class AcknowledgementStatus(Enum):
    ARM_OK = 0
    ARM_DENIED = 1
    ARM_INV = 2

@dataclass
class PacketHeader:
    type: PacketType
    sub_type: TelemetryPacketSubType

@dataclass
class PacketMessage(ABC):
    time_since_power: int

@dataclass
class ActuationRequest():
    id: int
    state: ActuatorState

@dataclass
class ActuationAcknowledgement():
    id: int
    status: ActuationRequestStatus

@dataclass
class ArmingRequest():
    level: ArmingState

@dataclass
class ArmingAcknowledgement():
    status: AcknowledgementStatus

@dataclass
class TemperaturePacket(PacketMessage):
    temperature: int
    id: int

@dataclass
class PressurePacket(PacketMessage):
    pressure: int
    id: int

@dataclass
class MassPacket(PacketMessage):
    mass: int
    id: int

@dataclass
class ArmingStatePacket(PacketMessage):
    state: ArmingState

@dataclass
class ActuatorStatePacket(PacketMessage):
    id: int
    state: ActuatorState

@dataclass
class WarningPacket(PacketMessage):
    type: Warning

@dataclass
class SerialDataPacket():
    m1: int
    m2: int
    p1: int
    p2: int
    p3: int
    p4: int
    t1: int
    t2: int
    t3: int
    status: int

def parse_packet_header(header_bytes: bytes) -> PacketHeader:
    packet_type: int
    packet_sub_type: int
    packet_type, packet_sub_type = struct.unpack("<BB", header_bytes)
    return PacketHeader(PacketType(packet_type), TelemetryPacketSubType(packet_sub_type))

def packet_message_bytes_length(header: PacketHeader) -> int:
    match header.type:
        case PacketType.TELEMETRY:
            match header.sub_type:
                case TelemetryPacketSubType.TEMPERATURE | TelemetryPacketSubType.PRESSURE | TelemetryPacketSubType.MASS:
                    return 9
                case TelemetryPacketSubType.ACT_STATE:
                    return 6
                case TelemetryPacketSubType.ARMING_STATE | TelemetryPacketSubType.WARNING:
                    return 5

def parse_packet_message(header: PacketHeader, message_bytes: bytes) -> PacketMessage:
    match header.type:
        case PacketType.CONTROL:
            match header.sub_type:
                case TelemetryPacketSubType.ACT_REQ:
                    id: int
                    state: int
                    id, state = struct.unpack("<BB". message_bytes)
                    return ActuationRequest(id=id, state=state)
                case TelemetryPacketSubType.ACT_ACK:
                    id: int
                    status: int
                    id, status = struct.unpack("<BB", message_bytes)
                    return ActuationAcknowledgement(id=id, status=status)
                case TelemetryPacketSubType.ARM_REQ:
                    level: int
                    level = struct.unpack("<B", message_bytes)
                    return ArmingRequest(level=level)
                case TelemetryPacketSubType.ARM_ACK:
                    status:int
                    status = struct.unpack("<B", message_bytes)
                    return ArmingAcknowledgement(status=status)

        case PacketType.TELEMETRY:
            match header.sub_type:
                case TelemetryPacketSubType.TEMPERATURE:
                    temperature: int
                    id: int
                    time: int
                    time, temperature, id = struct.unpack("<IIB", message_bytes)
                    return TemperaturePacket(temperature=temperature, id=id, time_since_power=time)
                case TelemetryPacketSubType.PRESSURE:
                    pressure: int
                    id: int
                    time: int
                    time, pressure, id = struct.unpack("<IIB", message_bytes)
                    return PressurePacket(pressure=pressure, id=id, time_since_power=time)
                case TelemetryPacketSubType.MASS:
                    time: int
                    mass: int
                    id: int
                    time, mass, id = struct.unpack("<IIB", message_bytes)
                    return MassPacket(mass=mass, id=id, time_since_power=time)
                case TelemetryPacketSubType.ARMING_STATE:
                    time:int
                    state:int
                    time, state = struct.unpack("<IB", message_bytes)
                    return ArmingStatePacket(state=ArmingState(state), time_since_power=time)
                case TelemetryPacketSubType.ACT_STATE:
                    time:int
                    state:int
                    id:int
                    time, id, state = struct.unpack("<IBB", message_bytes)
                    return ActuatorStatePacket(time_since_power=time, id=id, state=ActuatorState(state))
                case TelemetryPacketSubType.WARNING:
                    time:int
                    type:int
                    time, type = struct.unpack("<IB", message_bytes)
                    return WarningPacket(type=Warning(type), time_since_power=time)

def parse_serial_packet(data: bytes, timestamp: int, default_open_valves):
    m1: int
    m2: int
    p1: int
    p2: int
    p3: int
    p4: int
    t1: int
    t2: int
    t3: int
    status: int
    m2, m1, p1, p2, p3, p4, t1, t2, t3, status = struct.unpack_from("<HHHHHHHHHI", data, offset=4)
    parsed_packet = SerialDataPacket(
        m1=m1/1000, 
        m2=loadCell2Conversion(m2),
        p1=pressureConversion(p1),
        p2=pressureConversion(p2),
        p3=pressureConversion(p3),
        p4=pressureConversion(p4),
        t1=thermistorConversion(t1),
        t2=thermistor2Conversion(t2),
        t3=thermocouple3Conversion(t3),
        status='{:012b}'.format(status//pow(2,16))[::-1] # Converts status int into bit string
        # corresponding to switch status, easier to read
        # right-most 16 bits are removed since those don't correspond to valve status
    )
    packet_list: list[(PacketHeader, PacketMessage)] = []
    for field, val in asdict(parsed_packet).items():
        if field.startswith("m"):
            header = PacketHeader(PacketType.TELEMETRY, TelemetryPacketSubType.MASS)
            message = MassPacket(timestamp, val, int(field[-1]))
            packet_list.append((header, message))
        elif field.startswith("p"):
            header = PacketHeader(PacketType.TELEMETRY, TelemetryPacketSubType.PRESSURE)
            message = PressurePacket(timestamp, val, int(field[-1]))
            packet_list.append((header, message))
        elif field.startswith("t"):
            header = PacketHeader(PacketType.TELEMETRY, TelemetryPacketSubType.TEMPERATURE)
            message = TemperaturePacket(timestamp, val, int(field[-1]))
            packet_list.append((header, message))
        else:
            header = PacketHeader(PacketType.TELEMETRY, TelemetryPacketSubType.ACT_STATE)
            for index, bit in enumerate(val):
                if index in default_open_valves:
                    state = ActuatorState.ON if bit == "0" else ActuatorState.OFF
                else:
                    state = ActuatorState.OFF if bit == "0" else ActuatorState.ON
                message = ActuatorStatePacket(timestamp, index, state)
                packet_list.append((header, message))
    return parsed_packet, packet_list

            