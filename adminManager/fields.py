
from django.db import models

from .geometry import WKBGeometry

import json

class GeometryField(models.Field):
    '''Custom geometry field that is set with WKBGeometry, 
    converts the WKBGeometry to the backend database's geometry type,
    and reads it back from the database as WKBGeometry.'''
    description = "Geometry as backend type"

    def db_type(self, connection):
        return "Geometry"

    def get_prep_value(self, value):
        """Used to standardize all values when storing on the model's attribute."""
        if value is None:
            return value

        if not isinstance(value, WKBGeometry):
            value = WKBGeometry(value)

        return value

    def get_db_prep_value(self, value, connection, prepared=False):
        """Used to convert the model's attribute value to a format required by the db."""
        value = super().get_db_prep_value(value, connection, prepared)
        
        # convert to wkb bytes
        if isinstance(value, WKBGeometry):
            value = value.wkb

        if value is not None:
            value = connection.Database.Binary(value)
            
        return value

    def get_placeholder(self, value, compiler, connection):
        """
        Return the placeholder for the spatial column for the
        given value.
        """
        sql = 'ST_GeomFromWKB(%s)'
        return sql

    def from_db_value(self, value, expression, connection):
        # used by db loading
        if value is None:
            return value

        value = value[4:] # ignore first 4 bytes used for srid code in db storage

        return WKBGeometry(value)

    def to_python(self, value):
        # used by deserialization and form cleaning
        if value is None:
            return value
        
        if not isinstance(value, WKBGeometry):
            value = WKBGeometry(value)

        return value

    # def value_to_string(self, obj):
    #     # used by serializer
    #     geom = self.value_from_object(obj)
    #     return geom

    # def select_format(self, compiler, sql, params):
    #     """
    #     Return the selection format string, depending on the requirements
    #     of the spatial backend. For example, Oracle and MySQL require custom
    #     selection formats in order to retrieve geometries in OGC WKB.
    #     """
    #     raise Exception(999)
    #     if not compiler.query.subquery:
    #         return compiler.connection.ops.select % sql, params
    #     return sql, params

