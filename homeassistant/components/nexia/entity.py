"""The nexia integration base entity."""

from nexia.thermostat import NexiaThermostat
from nexia.zone import NexiaThermostatZone

from homeassistant.const import (
    ATTR_IDENTIFIERS,
    ATTR_NAME,
    ATTR_SUGGESTED_AREA,
    ATTR_VIA_DEVICE,
)
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import (
    async_dispatcher_connect,
    async_dispatcher_send,
)
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ATTRIBUTION,
    DOMAIN,
    MANUFACTURER,
    SIGNAL_THERMOSTAT_UPDATE,
    SIGNAL_ZONE_UPDATE,
    SIGNAL_IQ_UPDATE,
)
from .coordinator import NexiaDataUpdateCoordinator


class NexiaEntity(CoordinatorEntity[NexiaDataUpdateCoordinator]):
    """Base class for nexia entities."""

    _attr_attribution = ATTRIBUTION

    def __init__(self, coordinator: NexiaDataUpdateCoordinator, unique_id: str) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self._attr_unique_id = unique_id


class NexiaThermostatEntity(NexiaEntity):
    """Base class for nexia devices attached to a thermostat."""

    _attr_has_entity_name = True

    def __init__(self, coordinator, thermostat, unique_id):
        """Initialize the entity."""
        super().__init__(coordinator, unique_id)
        self._thermostat: NexiaThermostat = thermostat
        self._attr_device_info = DeviceInfo(
            configuration_url=self.coordinator.nexia_home.root_url,
            identifiers={(DOMAIN, self._thermostat.thermostat_id)},
            manufacturer=MANUFACTURER,
            model=self._thermostat.get_model(),
            name=self._thermostat.get_name(),
            sw_version=self._thermostat.get_firmware(),
        )

    async def async_added_to_hass(self):
        """Listen for signals for services."""
        await super().async_added_to_hass()
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                f"{SIGNAL_THERMOSTAT_UPDATE}-{self._thermostat.thermostat_id}",
                self.async_write_ha_state,
            )
        )

    def _signal_thermostat_update(self):
        """Signal a thermostat update.

        Whenever the underlying library does an action against
        a thermostat, the data for the thermostat and all
        connected zone is updated.

        Update all the zones on the thermostat.
        """
        async_dispatcher_send(
            self.hass, f"{SIGNAL_THERMOSTAT_UPDATE}-{self._thermostat.thermostat_id}"
        )

    @property
    def available(self) -> bool:
        """Return True if thermostat is available and data is available."""
        return super().available and self._thermostat.is_online


class NexiaThermostatZoneEntity(NexiaThermostatEntity):
    """Base class for nexia devices attached to a thermostat."""

    def __init__(self, coordinator, zone, unique_id):
        """Initialize the entity."""
        super().__init__(coordinator, zone.thermostat, unique_id)
        self._zone: NexiaThermostatZone = zone
        zone_name = self._zone.get_name()
        self._attr_device_info |= {
            ATTR_IDENTIFIERS: {(DOMAIN, self._zone.zone_id)},
            ATTR_NAME: zone_name,
            ATTR_SUGGESTED_AREA: zone_name,
            ATTR_VIA_DEVICE: (DOMAIN, self._zone.thermostat.thermostat_id),
        }

    async def async_added_to_hass(self):
        """Listen for signals for services."""
        await super().async_added_to_hass()
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                f"{SIGNAL_ZONE_UPDATE}-{self._zone.zone_id}",
                self.async_write_ha_state,
            )
        )

    def _signal_zone_update(self):
        """Signal a zone update.

        Whenever the underlying library does an action against
        a zone, the data for the zone is updated.

        Update a single zone.
        """
        async_dispatcher_send(self.hass, f"{SIGNAL_ZONE_UPDATE}-{self._zone.zone_id}")


class NexiaThermostatIqEntity(NexiaThermostatEntity):
    """Class for Room IQ sensors attached to a thermostat."""

    def __init__(self, coordinator, iq, unique_id):
        """Initialize the entity."""
        super().__init__(coordinator, iq.thermostat, unique_id)
        self._iq: NexiaThermostatRoomIq = iq

        # The sensor built into the thermostate has type "thermostat".
        # Put "builtin" in the name to distinguish it.
        is_builtin = self._iq.get_type() == "thermostat"
        name = "builtin" if is_builtin else self._iq.get_name()
        iq_name = f"{self._iq.thermostat.get_name()} {name}"

        # Suggest the name of the thermostate if built-in, otherwise use the sensor name.
        area = self._iq.thermostat.get_name() if is_builtin else self._iq.get_name()

        self._attr_device_info |= {
            ATTR_IDENTIFIERS: {(DOMAIN, self._iq.iq_id)},
            ATTR_NAME: iq_name,
            ATTR_SUGGESTED_AREA: area,
            ATTR_VIA_DEVICE: (DOMAIN, self._iq.thermostat.thermostat_id),
        }

    async def async_added_to_hass(self):
        """Listen for signals for services."""
        await super().async_added_to_hass()
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                f"{SIGNAL_IQ_UPDATE}-{self._iq.iq_id}",
                self.async_write_ha_state,
            )
        )

    def _signal_iq_update(self):
        """Signal an IQ update.

        Whenever the underlying library does an action against
        a zone, the data for the zone is updated.

        Update a single IQ sensor.
        """
        async_dispatcher_send(self.hass, f"{SIGNAL_IQ_UPDATE}-{self._iq.iq_id}")
