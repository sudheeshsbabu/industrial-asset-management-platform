from marshmallow import Schema, fields, validate


class AssetSchema(Schema):
    id = fields.Int(dump_only=True)
    name = fields.Str(required=True)
    site = fields.Str(required=True)
    status = fields.Str(required=True)
    