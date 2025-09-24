import type { DemoPackageResponse, DemoTable, DemoTableColumn, DemoTableRow } from './mock';

const PPLX_ENDPOINT = 'https://api.perplexity.ai/chat/completions';
const MODEL = 'pplx-70b-online';

interface PerplexityChoice {
  message?: {
    content?: string;
  };
}

interface PerplexityResponse {
  choices?: PerplexityChoice[];
}

const stripCodeFences = (content: string) =>
  content.replace(/^```json\s*/i, '').replace(/```$/i, '').trim();

const ensureColumns = (table: any): DemoTableColumn[] => {
  if (!Array.isArray(table.columns)) {
    throw new Error('Table columns missing');
  }

  return table.columns.map((col: any) => ({
    name: String(col.name ?? ''),
    type: String(col.type ?? 'NVARCHAR(255)'),
    description: col.description ? String(col.description) : undefined,
    nullable: col.nullable === undefined ? true : Boolean(col.nullable),
    isPrimaryKey: Boolean(col.isPrimaryKey ?? false),
  }));
};

const ensureRows = (table: any): DemoTableRow[] => {
  if (!Array.isArray(table.rows)) {
    return [];
  }

  return table.rows.map((row: any) => {
    if (row === null || typeof row !== 'object' || Array.isArray(row)) {
      throw new Error('Table row must be an object');
    }
    return row as DemoTableRow;
  });
};

const parseContent = (content: string): DemoPackageResponse => {
  const cleaned = stripCodeFences(content);
  const parsed = JSON.parse(cleaned);

  if (!parsed.tables || !Array.isArray(parsed.tables)) {
    throw new Error('Perplexity response missing tables array');
  }

  return {
    schemaName: String(parsed.schemaName ?? parsed.schema ?? 'JOULE_DEMO_SCHEMA'),
    tables: parsed.tables.slice(0, 10).map((table: any, index: number): DemoTable => ({
      name: String(table.name ?? `TABLE_${index + 1}`),
      desc: String(table.desc ?? table.description ?? 'No description provided by Joule.'),
      columns: ensureColumns(table),
      rows: ensureRows(table),
    })),
    agentPrompt: String(parsed.agentPrompt ?? parsed.prompt ?? ''),
    agentName: String(parsed.agentName ?? parsed.name ?? 'SAP Joule Agent'),
    businessCaseCard: String(parsed.businessCaseCard ?? parsed.businessCase ?? ''),
  };
};

const buildMessages = (customer: string, useCase: string) => [
  {
    role: 'system',
    content:
      'You are SAP Joule, an SAP BTP solution advisor. Respond ONLY with compact JSON (no markdown) matching {"agentName","agentPrompt","schemaName","tables":[{"name","desc","columns":[{"name","type","description","nullable","isPrimaryKey"}],"rows":[{...}]}],"businessCaseCard"}. Provide exactly 10 tables. schemaName must be uppercase alphanumeric with underscores, derived from customer + use case. Table column names must be uppercase with underscores, using SAP-relevant data types (NVARCHAR, DECIMAL, INTEGER, DATE, TIMESTAMP). Include at least 2 sample rows per table with keys matching the column names. businessCaseCard must use emoji headers (Problem, Solution, Benefits, ROI). agentPrompt must end with "Joule Tip: ...".',
  },
  {
    role: 'user',
    content: `Customer: ${customer}\nUse case: ${useCase}\nReturn exactly 10 tables focused on SAP data sources or work packages for this scenario, a compelling agentName, a system agentPrompt suitable for SAP BTP orchestration, and a businessCaseCard string with emoji sections (Problem, Solution, Benefits, ROI). agentPrompt must mention SAP Joule, SAP BTP, and Perplexity research boosts, and end with "Joule Tip: <insight>". Provide schemaName based on customer + use case (uppercase, underscores). For each table include detailed columns with SAP-aligned data types and 2-3 realistic sample rows aligned to the scenario.`,
  },
];

export const fetchJouleDemoFromPerplexity = async (
  customer: string,
  useCase: string,
): Promise<DemoPackageResponse> => {
  const apiKey = import.meta.env.VITE_PPLX_API_KEY;

  if (!apiKey) {
    throw new Error('Missing Perplexity API key in VITE_PPLX_API_KEY');
  }

  const response = await fetch(PPLX_ENDPOINT, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${apiKey}`,
    },
    body: JSON.stringify({
      model: MODEL,
      temperature: 0.2,
      max_tokens: 1800,
      messages: buildMessages(customer, useCase),
    }),
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Perplexity API error: ${response.status} ${errorText}`);
  }

  const data = (await response.json()) as PerplexityResponse;
  const content = data?.choices?.[0]?.message?.content;

  if (!content) {
    throw new Error('Perplexity response missing content');
  }

  try {
    const parsed = parseContent(content);

    if (!parsed.businessCaseCard) {
      throw new Error('Business case card missing');
    }

    return parsed;
  } catch (error) {
    console.error('Unable to parse Perplexity response', error);
    throw error;
  }
};
