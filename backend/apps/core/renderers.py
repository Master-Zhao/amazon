from rest_framework.renderers import JSONRenderer

from apps.core.case_conversion import to_camel_case
from apps.core.serialization import SafeJSONEncoder


class CamelCaseJSONRenderer(JSONRenderer):
    encoder_class = SafeJSONEncoder

    def render(self, data, accepted_media_type=None, renderer_context=None):
        return super().render(
            to_camel_case(data),
            accepted_media_type=accepted_media_type,
            renderer_context=renderer_context,
        )
