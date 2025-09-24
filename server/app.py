import json
import logging
import os
import re
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

try:
    from hdbcli import dbapi
except ImportError as exc:  # pragma: no cover
    raise RuntimeError(
        'hdbcli package is required. Install dependencies via `pip install -r server/requirements.txt`.'
    ) from exc

from sap_agents_api import PostAgentsAPI, SAPAgentAPIError

LOGGER = logging.getLogger('sap_joule_backend')
logging.basicConfig(level=logging.INFO)

CATALOG_SCHEMA = os.getenv('HANA_CATALOG_SCHEMA', 'AGENT_CATALOG')
SAP_AGENT_UI_BASE_URL = os.getenv(
    'SAP_AGENT_UI_BASE_URL',
    'https://agents-y0yj1uar.baf-dev.cfapps.eu12.hana.ondemand.com/ui/index.html#/agents',
)


class TableColumn(BaseModel):
    name: str
    type: str
    description: Optional[str] = None
    nullable: Optional[bool] = True
    isPrimaryKey: Optional[bool] = False


class TableDefinition(BaseModel):
    name: str
    desc: str
    columns: List[TableColumn]
    rows: List[Dict[str, Any]] = Field(default_factory=list)


class AgentPayload(BaseModel):
    name: str
    prompt: str
    customer: str
    useCase: str
    schemaName: str
    tables: List[TableDefinition]
    businessCaseCard: str


app = FastAPI(title='SAP Joule Make-a-Wish API')

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)


def hana_connect():
    host = os.getenv('HANA_HOST')
    port = int(os.getenv('HANA_PORT', '443'))
    user = os.getenv('HANA_USER')
    password = os.getenv('HANA_PASSWORD')

    if not all([host, port, user, password]):
        raise RuntimeError('Missing HANA connection details in environment variables.')

    LOGGER.info('Connecting to SAP HANA at %s:%s as %s', host, port, user)

    return dbapi.connect(
        address=host,
        port=port,
        user=user,
        password=password,
        encrypt='true',
        sslValidateCertificate='false',
    )


def sanitize_identifier(value: str, fallback: str = 'JOULE_SCHEMA') -> str:
    if not value:
        value = fallback
    clean = re.sub(r'[^A-Za-z0-9_]', '_', value)
    clean = clean.upper()
    if not clean:
        clean = fallback
    if clean[0].isdigit():
        clean = f'J_{clean}'
    return clean


def ensure_catalog(conn) -> None:
    cur = conn.cursor()
    cur.execute(f'CREATE SCHEMA IF NOT EXISTS "{CATALOG_SCHEMA}"')
    cur.execute(
        f'''
        CREATE TABLE IF NOT EXISTS "{CATALOG_SCHEMA}"."AGENTS" (
            "AGENT_ID" NVARCHAR(36) PRIMARY KEY,
            "AGENT_NAME" NVARCHAR(120) NOT NULL,
            "USE_CASE" NVARCHAR(120) NOT NULL,
            "CUSTOMER" NVARCHAR(120) NOT NULL,
            "CREATED_AT" TIMESTAMP DEFAULT CURRENT_UTCTIMESTAMP NOT NULL,
            "CREATED_BY" NVARCHAR(120) NOT NULL,
            "PROMPT" NCLOB NOT NULL,
            "BUSINESS_CASE_CARD" NCLOB NOT NULL,
            "SCHEMA_NAME" NVARCHAR(128) NOT NULL
        )
        '''
    )
    cur.execute(
        f'''
        CREATE TABLE IF NOT EXISTS "{CATALOG_SCHEMA}"."AGENT_ASSETS" (
            "AGENT_ID" NVARCHAR(36) NOT NULL,
            "ASSET_NAME" NVARCHAR(120) NOT NULL,
            "SCHEMA_NAME" NVARCHAR(128) NOT NULL,
            "TABLE_NAME" NVARCHAR(128) NOT NULL,
            "METADATA" NCLOB,
            PRIMARY KEY ("AGENT_ID", "ASSET_NAME"),
            FOREIGN KEY ("AGENT_ID") REFERENCES "{CATALOG_SCHEMA}"."AGENTS" ("AGENT_ID")
        )
        '''
    )
    conn.commit()


def create_schema_with_tables(conn, schema_name: str, tables: List[TableDefinition]) -> None:
    cur = conn.cursor()
    cur.execute(f'CREATE SCHEMA IF NOT EXISTS "{schema_name}"')

    for table in tables:
        table_name = sanitize_identifier(table.name)
        LOGGER.info('Creating table %s.%s', schema_name, table_name)

        # Drop existing table gracefully
        try:
            cur.execute(f'DROP TABLE "{schema_name}"."{table_name}"')
        except dbapi.Error:
            LOGGER.debug('Table %s.%s did not exist prior to creation.', schema_name, table_name)

        column_fragments = []
        primary_keys: List[str] = []

        for column in table.columns:
            col_name = sanitize_identifier(column.name, fallback='COL')
            col_type = column.type.upper() if column.type else 'NVARCHAR(255)'
            nullable = column.nullable if column.nullable is not None else True

            fragment = f'"{col_name}" {col_type}'
            if not nullable:
                fragment += ' NOT NULL'
            column_fragments.append(fragment)

            if column.isPrimaryKey:
                primary_keys.append(f'"{col_name}"')

        if primary_keys:
            column_fragments.append(f'PRIMARY KEY ({", ".join(primary_keys)})')

        ddl = f'CREATE TABLE "{schema_name}"."{table_name}" ({", ".join(column_fragments)})'
        cur.execute(ddl)

        if table.rows:
            column_info = []
            for index, column in enumerate(table.columns):
                original = column.name
                sanitized = sanitize_identifier(original, fallback=f'COL_{index}')
                column_info.append((original, sanitized))

            placeholders = ', '.join(['?'] * len(column_info))
            columns_joined = ', '.join([f'"{sanitized}"' for _, sanitized in column_info])
            insert_sql = f'INSERT INTO "{schema_name}"."{table_name}" ({columns_joined}) VALUES ({placeholders})'

            for row in table.rows:
                values = []
                for original, sanitized in column_info:
                    candidates = []
                    if isinstance(original, str):
                        candidates.extend(
                            [
                                original,
                                original.upper(),
                                original.lower(),
                                original.replace(' ', '_'),
                            ]
                        )
                    candidates.append(sanitized)

                    value = None
                    for key in candidates:
                        if key in row:
                            value = row[key]
                            break

                    values.append(serialize_value(value))

                cur.execute(insert_sql, values)

    conn.commit()


def serialize_value(value: Any) -> Any:
    if isinstance(value, bool):
        return 1 if value else 0
    if isinstance(value, (str, int, float)) or value is None:
        return value
    return json.dumps(value)


def register_agent_metadata(
    conn,
    *,
    agent_id: str,
    agent_name: str,
    use_case: str,
    customer: str,
    schema_name: str,
    prompt: str,
    business_case_card: str,
    tables: List[TableDefinition],
) -> None:
    cur = conn.cursor()
    cur.execute(
        f'''
        INSERT INTO "{CATALOG_SCHEMA}"."AGENTS"
            ("AGENT_ID", "AGENT_NAME", "USE_CASE", "CUSTOMER", "CREATED_AT", "CREATED_BY", "PROMPT", "BUSINESS_CASE_CARD", "SCHEMA_NAME")
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''',
        (
            agent_id,
            agent_name,
            use_case,
            customer,
            datetime.utcnow(),
            os.getenv('HANA_CREATED_BY', 'SAP_JOULE_APP'),
            prompt,
            business_case_card,
            schema_name,
        ),
    )

    for table in tables:
        table_name = sanitize_identifier(table.name)
        metadata = {
            'description': table.desc,
            'columns': [column.dict() for column in table.columns],
        }
        cur.execute(
            f'''
            INSERT INTO "{CATALOG_SCHEMA}"."AGENT_ASSETS"
                ("AGENT_ID", "ASSET_NAME", "SCHEMA_NAME", "TABLE_NAME", "METADATA")
            VALUES (?, ?, ?, ?, ?)
            ''',
            (
                agent_id,
                table.name,
                schema_name,
                table_name,
                json.dumps(metadata),
            ),
        )

    conn.commit()


@app.post('/api/agents')
def create_agent(payload: AgentPayload):
    LOGGER.info('Received agent creation request for %s', payload.name)

    schema_name = sanitize_identifier(payload.schemaName, fallback=f'{payload.customer}_{payload.useCase}')
    agent_id = str(uuid.uuid4())

    conn = hana_connect()
    try:
        ensure_catalog(conn)
        create_schema_with_tables(conn, schema_name, payload.tables)
        register_agent_metadata(
            conn,
            agent_id=agent_id,
            agent_name=payload.name,
            use_case=payload.useCase,
            customer=payload.customer,
            schema_name=schema_name,
            prompt=payload.prompt,
            business_case_card=payload.businessCaseCard,
            tables=payload.tables,
        )
    finally:
        conn.close()

    agent_payload = {
        'ID': agent_id,
        'name': payload.name,
        'prompt': payload.prompt,
        'description': payload.businessCaseCard.split('\n')[0] if payload.businessCaseCard else payload.useCase,
        'metadata': {
            'customer': payload.customer,
            'useCase': payload.useCase,
            'schemaName': schema_name,
            'businessCaseCard': payload.businessCaseCard,
        },
        'tools': [
            {
                'name': 'perplexity-search',
                'config': {
                    'apiKeyAlias': os.getenv('PPLX_API_KEY_ALIAS', 'PPLX_PRIMARY'),
                },
            }
        ],
    }

    try:
        agent_response = PostAgentsAPI('', agent_payload)
    except SAPAgentAPIError as exc:  # pragma: no cover - surface upstream for diagnostics
        LOGGER.error('SAP Agent API error: %s', exc)
        raise HTTPException(status_code=502, detail='Failed to create agent in SAP Agents service.') from exc

    agent_url = f"{SAP_AGENT_UI_BASE_URL}/{agent_id}"
    LOGGER.info('Agent %s created. Opening URL %s', agent_id, agent_url)

    return {
        'agentId': agent_id,
        'agentUrl': agent_url,
        'schemaName': schema_name,
        'sapAgentResponse': agent_response,
    }


@app.get('/healthz')
def healthcheck():
    return {'status': 'ok'}
