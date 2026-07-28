from rest_framework.parsers import JSONParser

from apps.core.case_conversion import to_snake_case


class CamelCaseJSONParser(JSONParser):
    def parse(self, stream, media_type=None, parser_context=None):
        parsed = super().parse(
            stream,
            media_type=media_type,
            parser_context=parser_context,
        )
        return to_snake_case(parsed)
