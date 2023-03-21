"""
    Database convertor class

    Convertor for data types:
    SQL-Alchemy has it's own Type definitions: sqlalchemy.sql.sqltypes
    https://docs.sqlalchemy.org/en/20/core/type_basics.html#types-sqlstandard
    These are the types that are returned.
    The DMS requires a specific set of definitions differing from what sql-alchemy outputs, we define the convertion mappings here.
    
    Note. Mapping convertions for types. 
     -> SQL-Alchemy  >> _sqlalchemy_type_map

    class sqlalchemy.types.TypeEngine
    
"""

from typing import DefaultDict
import sqlalchemy
from sqlalchemy.sql import sqltypes

from mojap_metadata import Metadata
import mojap_metadata.converters.database_converter.database_functions as dbfun

from mojap_metadata.converters import BaseConverter

_sqlalchemy_type_map = {
    "BIGINT": "int64",
    "INT": "int32",
    "INTEGER": "int32",
    "SMALLINT": "int16",
    "REAL": 'float24',
    "DOUBLE": "float32",
    "DOUBLE_PRECISION": "float64",
    "NUMERIC": "float64",
    "DECIMAL": "decimal",
    "TEXT": "character",
    "UUID": "character",
    "NCHAR": "character",
    "CHAR": "character",
    "NVARCHAR": "character",
    "VARCHAR": "character",
    "JSON": "character",
    "DATE": "date64",
    "TIME": "timestamp(ms)",
    "TIMESTAMP": "timestamp(ms)",
    "DATETIME": "datetime",
    "BOOLEAN": "bool",
    "BOOL": "bool",
    "BLOB": "blob",
    "CLOB": "clob",
    "BINARY": "binary",
    "VARBINARY": "binary"
}

class DatabaseConverter(BaseConverter):
    def __init__(self, dialect):
        """
        Extracts and converts metadata to Metadata format
        """

        super().__init__()
        self._sqlalchemy_type_map = _sqlalchemy_type_map
        self.dialect= dialect


    def convert_to_mojap_type(self, col_type: str) -> str:
        """ Converts SQL-Alchemy datatypes to mojap-metadata types
            Args:       ct (str):   String representation of source column types
            Returns:    str:        String representation of metadata column types
        """

        output = (
            "string"
            if self._sqlalchemy_type_map.get(col_type) is None
            else self._sqlalchemy_type_map.get(col_type)
        )
        return output


    def get_object_meta(
        self, connection: sqlalchemy.engine.Engine, table: str, schema: str
    ) -> Metadata:
        """ for a table, get metadata and convert to mojap metadata format.
            
            Convert sqlalchemy inpector result.

        Args:
            connection: Database connection
            table: table name
            schema: schema name

        Returns:
            Metadata: Metadata object
        """

        rows = dbfun.list_meta_data(connection, table, schema)
        columns = []

        for col in rows[0]:
            dType=self._approx_dtype(str(col[1]))
            columnType = self.convert_to_mojap_type(dType)
            columnType=str(col[1])
            columns.append(
                {
                    "name": col[0].lower(),
                    "type": columnType,
                    "description": None if str(col[3]) is None else str(col[3]),
                    "nullable": True if col[2] == "YES" or col[2]==True or col[2] else False,
                }
            )

        d = {"name": table, "columns": columns}

        meta_output = Metadata.from_dict(d)
        return meta_output


    def generate_from_meta(self, connection: sqlalchemy.engine.Engine) -> dict():
        """ For all the schema and tables and returns a list of Metadata

        Args:
            connection: Database connection with database details

        Returns:
            Metadata: Metadata object
        """
        meta_list_per_schema = DefaultDict(list)
        
        schema_names = dbfun.list_schemas(
            connection, self.dialect
        )  # database name will be passed on in the connection

        for schema in sorted(schema_names):
            table_names = dbfun.list_tables(connection, schema)

            for table in table_names:
                meta_output = self.get_object_meta(connection, table, schema)
                meta_list_per_schema[f"schema: {schema}"].append(meta_output)

        return meta_list_per_schema


    def _approx_dtype(self, txt: str)-> str:
        """ Find approximate data type value of SQL-Alchemy data type, often supplied with precision value that can't be matched.
            Args:
                txt: SQL-Alchemy data type, with precision value
            Returns:
                string: mapped data type, from _sqlalchemy_type_map, default 'binary'
        """
        dtype='binary'
        for k in _sqlalchemy_type_map:
            if txt.find(k) >= 0:
                dtype=k
                break
        return dtype
