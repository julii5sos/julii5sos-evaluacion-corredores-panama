"""Estado de configuración de la preevaluación (sin importar Earth Engine)."""
import os


def estado():
    return dict(earth_engine=bool(os.environ.get('EE_PROJECT')),
                bosque_2021=os.environ.get('EE_ASSET_BOSQUE_2021', 'projects/ee-julissaguevaravega/assets/CBOTB_2021_BOSQUE'),
                cuenta_servicio=bool(os.environ.get('EE_SERVICE_ACCOUNT_JSON')))
