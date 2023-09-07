"""Support for Nexia / Trane XL Thermostats."""
from __future__ import annotations

from nexia.const import UNIT_CELSIUS
from nexia.thermostat import NexiaThermostat

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import NexiaDataUpdateCoordinator
from .entity import (
    NexiaThermostatEntity,
    NexiaThermostatZoneEntity,
    NexiaThermostatIqEntity,
)
from .util import percent_conv


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensors for a Nexia device."""

    coordinator: NexiaDataUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    nexia_home = coordinator.nexia_home
    entities: list[NexiaThermostatEntity] = []

    # Thermostat / System Sensors
    for thermostat_id in nexia_home.get_thermostat_ids():
        thermostat: NexiaThermostat = nexia_home.get_thermostat_by_id(thermostat_id)

        entities.append(
            NexiaThermostatSensor(
                coordinator,
                thermostat,
                "get_system_status",
                "system_status",
                None,
                None,
                None,
            )
        )
        # Air cleaner
        entities.append(
            NexiaThermostatSensor(
                coordinator,
                thermostat,
                "get_air_cleaner_mode",
                "air_cleaner_mode",
                None,
                None,
                None,
            )
        )
        # Compressor Speed
        if thermostat.has_variable_speed_compressor():
            entities.append(
                NexiaThermostatSensor(
                    coordinator,
                    thermostat,
                    "get_current_compressor_speed",
                    "current_compressor_speed",
                    None,
                    PERCENTAGE,
                    SensorStateClass.MEASUREMENT,
                    percent_conv,
                )
            )
            entities.append(
                NexiaThermostatSensor(
                    coordinator,
                    thermostat,
                    "get_requested_compressor_speed",
                    "requested_compressor_speed",
                    None,
                    PERCENTAGE,
                    SensorStateClass.MEASUREMENT,
                    percent_conv,
                )
            )
        # Outdoor Temperature
        if thermostat.has_outdoor_temperature():
            entities.append(
                NexiaThermostatSensor(
                    coordinator,
                    thermostat,
                    "get_outdoor_temperature",
                    "outdoor_temperature",
                    SensorDeviceClass.TEMPERATURE,
                    _get_temperature_unit(thermostat),
                    SensorStateClass.MEASUREMENT,
                )
            )
        # Relative Humidity
        if thermostat.has_relative_humidity():
            entities.append(
                NexiaThermostatSensor(
                    coordinator,
                    thermostat,
                    "get_relative_humidity",
                    None,
                    SensorDeviceClass.HUMIDITY,
                    PERCENTAGE,
                    SensorStateClass.MEASUREMENT,
                    percent_conv,
                )
            )

        # Zone Sensors
        for zone_id in thermostat.get_zone_ids():
            zone = thermostat.get_zone_by_id(zone_id)

            # Temperature
            entities.append(
                NexiaThermostatZoneSensor(
                    coordinator,
                    zone,
                    "get_temperature",
                    None,
                    SensorDeviceClass.TEMPERATURE,
                    _get_temperature_unit(thermostat),
                    SensorStateClass.MEASUREMENT,
                    None,
                )
            )
            # Zone Status
            entities.append(
                NexiaThermostatZoneSensor(
                    coordinator, zone, "get_status", "zone_status", None, None, None
                )
            )
            # Setpoint Status
            entities.append(
                NexiaThermostatZoneSensor(
                    coordinator,
                    zone,
                    "get_setpoint_status",
                    "zone_setpoint_status",
                    None,
                    None,
                    None,
                )
            )

        # Room IQ sensors
        for room_iq_id in thermostat.get_room_iq_ids():
            iq = thermostat.get_room_iq_by_id(room_iq_id)

            if bool(iq.get_weight()):
                entities.append(
                    NexiaThermostatIqSensor(
                        coordinator,
                        iq,
                        "get_weight",
                        "room_iq_weight",
                        None,
                        PERCENTAGE,
                        SensorStateClass.MEASUREMENT,
                        percent_conv,
                    )
                )

            entities.append(
                NexiaThermostatIqSensor(
                    coordinator,
                    iq,
                    "get_temperature",
                    None,
                    SensorDeviceClass.TEMPERATURE,
                    _get_temperature_unit(thermostat),
                    SensorStateClass.MEASUREMENT,
                    None,
                )
            )

            if bool(iq.get_humidity()):
                entities.append(
                    NexiaThermostatIqSensor(
                        coordinator,
                        iq,
                        "get_humidity",
                        None,
                        SensorDeviceClass.HUMIDITY,
                        PERCENTAGE,
                        SensorStateClass.MEASUREMENT,
                    )
                )

            if bool(iq.get_battery_level()):
                entities.append(
                    NexiaThermostatIqSensor(
                        coordinator,
                        iq,
                        "get_battery_level",
                        "room_iq_battery",
                        None,
                        PERCENTAGE,
                        SensorStateClass.MEASUREMENT,
                    )
                )

    async_add_entities(entities)


def _get_temperature_unit(thermostat) -> UnitOfTemperature:
    """Gets the temperature unit the thermostat operates in."""
    if thermostat.get_unit() == UNIT_CELSIUS:
        return UnitOfTemperature.CELSIUS
    else:
        return UnitOfTemperature.FAHRENHEIT


class NexiaThermostatSensor(NexiaThermostatEntity, SensorEntity):
    """Provides Nexia thermostat sensor support."""

    def __init__(
        self,
        coordinator,
        thermostat,
        sensor_call,
        translation_key,
        sensor_class,
        sensor_unit,
        state_class,
        modifier=None,
    ):
        """Initialize the sensor."""
        super().__init__(
            coordinator,
            thermostat,
            unique_id=f"{thermostat.thermostat_id}_{sensor_call}",
        )
        self._call = sensor_call
        self._modifier = modifier
        self._attr_device_class = sensor_class
        self._attr_native_unit_of_measurement = sensor_unit
        self._attr_state_class = state_class
        if translation_key is not None:
            self._attr_translation_key = translation_key

    @property
    def native_value(self):
        """Return the state of the sensor."""
        val = getattr(self._thermostat, self._call)()
        if self._modifier:
            val = self._modifier(val)
        if isinstance(val, float):
            val = round(val, 1)
        return val


class NexiaThermostatZoneSensor(NexiaThermostatZoneEntity, SensorEntity):
    """Nexia Zone Sensor Support."""

    def __init__(
        self,
        coordinator,
        zone,
        sensor_call,
        translation_key,
        sensor_class,
        sensor_unit,
        state_class,
        modifier=None,
    ):
        """Create a zone sensor."""

        super().__init__(
            coordinator,
            zone,
            unique_id=f"{zone.zone_id}_{sensor_call}",
        )
        self._call = sensor_call
        self._modifier = modifier
        self._attr_device_class = sensor_class
        self._attr_native_unit_of_measurement = sensor_unit
        self._attr_state_class = state_class
        if translation_key is not None:
            self._attr_translation_key = translation_key

    @property
    def native_value(self):
        """Return the state of the sensor."""
        val = getattr(self._zone, self._call)()
        if self._modifier:
            val = self._modifier(val)
        if isinstance(val, float):
            val = round(val, 1)
        return val


class NexiaThermostatIqSensor(NexiaThermostatIqEntity, SensorEntity):
    """Nexia Room IQ Sensor Support."""

    def __init__(
        self,
        coordinator,
        iq,
        sensor_call,
        translation_key,
        sensor_class,
        sensor_unit,
        state_class,
        modifier=None,
    ):
        """Create an IQ sensor."""

        super().__init__(
            coordinator,
            iq,
            unique_id=f"{iq.iq_id}_{sensor_call}",
        )
        self._call = sensor_call
        self._modifier = modifier
        self._attr_device_class = sensor_class
        self._attr_native_unit_of_measurement = sensor_unit
        self._attr_state_class = state_class
        if translation_key is not None:
            self._attr_translation_key = translation_key

    @property
    def native_value(self):
        """Return the state of the sensor."""
        val = getattr(self._iq, self._call)()
        if self._modifier:
            val = self._modifier(val)
        if isinstance(val, float):
            val = round(val, 1)
        return val
