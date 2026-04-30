from .kyoto import KyotoEngine
from .okinawa import OkinawaEngine
from .osaka import OsakaEngine
from .tokyo import TokyoEngine
from .ginza import GinzaEngine

# Maps the Database Island ID to the Mathematics Engine
ENGINE_REGISTRY = {
    1: KyotoEngine,
    2: OkinawaEngine,
    3: OsakaEngine,
    4: TokyoEngine,
    5: GinzaEngine,
}

def get_engine(island_id):
    """Returns the requested engine class, defaulting to Kyoto if not found."""
    return ENGINE_REGISTRY.get(island_id, KyotoEngine)