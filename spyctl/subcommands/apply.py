import spyctl.spyctl_lib as lib
import spyctl.config.secrets as secrets


def handle_apply(filename):
    resrc_data = lib.load_resource_file(filename)
    kind = resrc_data.get(lib.KIND_FIELD)
    if kind == secrets.SECRET_KIND:
        secrets.apply_secret(resrc_data)
