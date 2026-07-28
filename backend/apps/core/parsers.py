from rest_framework.parsers import DataAndFiles, JSONParser, MultiPartParser

from apps.core.case_conversion import to_snake_case, to_snake_key


class CamelCaseJSONParser(JSONParser):
    def parse(self, stream, media_type=None, parser_context=None):
        parsed = super().parse(
            stream,
            media_type=media_type,
            parser_context=parser_context,
        )
        return to_snake_case(parsed)


class CamelCaseMultiPartParser(MultiPartParser):
    def parse(self, stream, media_type=None, parser_context=None):
        parsed = super().parse(
            stream,
            media_type=media_type,
            parser_context=parser_context,
        )
        data = parsed.data.copy()
        files = parsed.files.copy()
        for collection in (data, files):
            for key in list(collection.keys()):
                snake_key = to_snake_key(str(key))
                if snake_key == key:
                    continue
                values = collection.getlist(key)
                del collection[key]
                collection.setlist(snake_key, values)
        return DataAndFiles(data, files)
