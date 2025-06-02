from typing import ClassVar, Mapping, Optional, Sequence, cast

from typing_extensions import Self
from viam.proto.app.robot import ComponentConfig
from viam.proto.common import ResourceName
from viam.resource.base import ResourceBase
from viam.resource.easy_resource import EasyResource
from viam.resource.types import Model, ModelFamily
from viam.services.generic import *
from viam.utils import ValueTypes, struct_to_dict

import asyncio
from threading import Event
from viam.logging import getLogger

from viam.components.board import Board
from viam.components.sensor import Sensor
from viam.components.servo import Servo

LOGGER = getLogger("fingerservo")

class Fingerservo(Generic, EasyResource):
    # To enable debug-level logging, either run viam-server with the --debug option,
    # or configure your resource/machine to display debug logs.
    MODEL: ClassVar[Model] = Model(
        ModelFamily("joyce", "control-access-fingerservo"), "fingerServo"
    )

    running = None
    task = None
    event = Event()

    @classmethod
    def new(
        cls, config: ComponentConfig, dependencies: Mapping[ResourceName, ResourceBase]
    ) -> Self:
        """This method creates a new instance of this Generic service.
        The default implementation sets the name from the `config` parameter and then calls `reconfigure`.

        Args:
            config (ComponentConfig): The configuration for this resource
            dependencies (Mapping[ResourceName, ResourceBase]): The dependencies (both implicit and explicit)

        Returns:
            Self: The resource
        """
        return super().new(config, dependencies)

    @classmethod
    def validate_config(cls, config: ComponentConfig) -> Sequence[str]:
        attrs = struct_to_dict(config.attributes)
        dependencies = []

        # Required
        for name in ["board", "servo", "sensor"]:
            if name not in attrs or not isinstance(attrs[name], str):
                raise ValueError(f"{name} is required and must be a string")
            dependencies.append(attrs[name])

        # Validate optional values
        if "leave_open_timeout" in attrs:
            try:
                timeout = float(attrs["leave_open_timeout"])
                if timeout < 0:
                    raise ValueError
            except ValueError:
                raise ValueError("leave_open_timeout must be a positive number")

        if "servo_open_angle" in attrs:
            try:
                angle = int(attrs["servo_open_angle"])
                if not (0 <= angle <= 180):
                    raise ValueError
            except ValueError:
                raise ValueError("servo_open_angle must be an integer between 0 and 180")

        if "servo_closed_angle" in attrs:
            try:
                angle = int(attrs["servo_closed_angle"])
                if not (0 <= angle <= 180):
                    raise ValueError
            except ValueError:
                raise ValueError("servo_closed_angle must be an integer between 0 and 180")

        # Optional dependencies
        for name in ["servo_open_angle", "servo_closed_angle", "leave_open_timeout"]:
            val = attrs.get(name)
            if val and isinstance(val, str):
                dependencies.append(val)

        return dependencies

    def reconfigure(
        self, config: ComponentConfig, dependencies: Mapping[ResourceName, ResourceBase]
    ):
        
        attrs = struct_to_dict(config.attributes)

        board_resource = dependencies.get(Board.get_resource_name(str(attrs.get("board"))))
        self.board = cast(Board, board_resource)
        servo_resource = dependencies.get(Servo.get_resource_name(str(attrs.get("servo"))))
        self.servo = cast(Servo, servo_resource)
        sensor_resource = dependencies.get(Sensor.get_resource_name(str(attrs.get("sensor"))))
        self.sensor= cast(Sensor, sensor_resource)
        self.leave_open_timeout = float(attrs.get("leave_open_timeout", 60))
        self.servo_open_angle = int(attrs.get("servo_open_angle", 180))
        self.servo_closed_angle = int(attrs.get("servo_closed_angle", 90))

        if self.running is None:
            self.start()
        else:
            LOGGER.info("Already running control logic.")

        return super().reconfigure(config, dependencies)

    async def do_command(
        self,
        command: Mapping[str, ValueTypes],
        *,
        timeout: Optional[float] = None,
        **kwargs
    ) -> Mapping[str, ValueTypes]:

        result = {key: False for key in command.keys()}
        for name, args in command.items():
            if name == "action" and args == "start":
                self.start()
                result[name] = True
            if name == "action" and args == "stop":
                self.stop()
                result[name] = True
        return result

    def start(self):
        loop = asyncio.get_event_loop()
        self.task = loop.create_task(self.control_loop())
        self.event.clear()

    def stop(self):
        self.event.set()
        if self.task is not None:
            self.task.cancel()

    async def control_loop(self):
        while not self.event.is_set():
            await self.on_loop()
            await asyncio.sleep(0)

    async def on_loop(self):
        try:
            readings = await self.sensor.get_readings()

            finger_detected = readings.get("finger_detected", False)
            matched = readings.get("matched", False)
            now = asyncio.get_event_loop().time()

            if finger_detected and matched:
                self.logger.info("Fingerprint match detected.")
                self.last_match_time = now
                if not hasattr(self, "servo_open") or not self.servo_open:
                    self.logger.info(f"Moving servo to {self.servo_open_angle}° to open access.")
                    await self.servo.move(self.servo_open_angle)
                    self.servo_open = True
            else:
                last = getattr(self, "last_match_time", now)
                timeout = getattr(self, "leave_open_timeout", 60)
                if now - last > timeout:
                    if not hasattr(self, "servo_open") or self.servo_open:
                        self.logger.info(f"Moving servo to {self.servo_closed_angle}° to close access.")
                        await self.servo.move(self.servo_closed_angle)
                        self.servo_open = False

        except Exception as err:
            self.logger.error(f"Error in fingerprint control logic: {err}")

        await asyncio.sleep(0.2)  # fast loop, debounce handles overreaction

    def __del__(self):
        self.stop()

    async def close(self):
        self.stop()
