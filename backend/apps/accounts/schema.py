from drf_spectacular.extensions import OpenApiAuthenticationExtension


class AccessTokenAuthenticationScheme(OpenApiAuthenticationExtension):
    target_class = "apps.accounts.authentication.AccessTokenAuthentication"
    name = ["bearerAuth", "xTokenAuth"]

    def get_security_requirement(self, auto_schema):
        return [{"bearerAuth": []}, {"xTokenAuth": []}]

    def get_security_definition(self, auto_schema):
        return [
            {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
            },
            {
                "type": "apiKey",
                "in": "header",
                "name": "X-Token",
                "description": (
                    "Access Token compatibility header. When Authorization "
                    "is also present, both token values must match."
                ),
            },
        ]
