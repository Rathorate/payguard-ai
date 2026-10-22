"""Regenerate the tracked API/schema files after a schema change."""
import json
import sys
from pathlib import Path
from sqlalchemy.schema import CreateTable, CreateIndex
from sqlalchemy.dialects import postgresql
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.main import app
from app.models import Base

root=Path(__file__).resolve().parent
(root/'openapi.json').write_text(json.dumps(app.openapi(),indent=2)+'\n',encoding='utf-8')
dialect=postgresql.dialect()
ddl=['-- Initial PostgreSQL schema. Use app.manage init-db for a fresh MVP database.']
for table in Base.metadata.sorted_tables:
    ddl.append(str(CreateTable(table).compile(dialect=dialect)).strip()+';')
    ddl.extend(str(CreateIndex(index).compile(dialect=dialect))+';' for index in table.indexes)
(root/'schema.sql').write_text('\n'.join(line.rstrip() for line in '\n\n'.join(ddl).splitlines())+'\n',encoding='utf-8')
print('Exported OpenAPI and PostgreSQL DDL')
