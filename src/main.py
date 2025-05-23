import asyncio
from viam.module.module import Module
try:
    from models.fingerServo import Fingerservo
except ModuleNotFoundError:
    # when running as local module with run.sh
    from .models.fingerServo import Fingerservo


if __name__ == '__main__':
    asyncio.run(Module.run_from_registry())
