export interface DemoTableColumn {
  name: string;
  type: string;
  description?: string;
  nullable?: boolean;
  isPrimaryKey?: boolean;
}

export type DemoTableRow = Record<string, string | number | boolean | null>;

export interface DemoTable {
  name: string;
  desc: string;
  columns: DemoTableColumn[];
  rows: DemoTableRow[];
}

export interface DemoPackageResponse {
  schemaName: string;
  tables: DemoTable[];
  agentPrompt: string;
  agentName: string;
  businessCaseCard: string;
}

const baseTables: DemoTable[] = [
  {
    name: 'CUS_MASTER_PROFILE',
    desc: 'Unified customer master data with segmentation attributes and consent flags.',
    columns: [
      { name: 'CUSTOMER_ID', type: 'NVARCHAR(40)', isPrimaryKey: true, nullable: false, description: 'Unique customer identifier' },
      { name: 'CUSTOMER_NAME', type: 'NVARCHAR(120)', description: 'Display name for the customer or account' },
      { name: 'INDUSTRY', type: 'NVARCHAR(60)', description: 'Industry classification' },
      { name: 'REGION', type: 'NVARCHAR(40)', description: 'Primary operating region' },
      { name: 'HEALTH_SCORE', type: 'DECIMAL(5,2)', description: 'Composite health score 0-100' },
    ],
    rows: [
      {
        CUSTOMER_ID: 'CUST-001',
        CUSTOMER_NAME: 'Launch Partner Holdings',
        INDUSTRY: 'Professional Services',
        REGION: 'EMEA',
        HEALTH_SCORE: 82.5,
      },
      {
        CUSTOMER_ID: 'CUST-002',
        CUSTOMER_NAME: 'Launch Partner Holdings',
        INDUSTRY: 'Professional Services',
        REGION: 'North America',
        HEALTH_SCORE: 77.3,
      },
    ],
  },
  {
    name: 'CUS_TOUCHPOINT_EVENTS',
    desc: 'Stream of omni-channel engagement events with sentiment scoring.',
    columns: [
      { name: 'EVENT_ID', type: 'NVARCHAR(40)', isPrimaryKey: true, nullable: false, description: 'Unique event id' },
      { name: 'CUSTOMER_ID', type: 'NVARCHAR(40)', description: 'Link to customer profile' },
      { name: 'CHANNEL', type: 'NVARCHAR(30)', description: 'Touchpoint channel name' },
      { name: 'EVENT_TS', type: 'TIMESTAMP', description: 'Event timestamp' },
      { name: 'SENTIMENT', type: 'DECIMAL(4,2)', description: 'Sentiment score -1 to 1' },
    ],
    rows: [
      {
        EVENT_ID: 'EVT-1001',
        CUSTOMER_ID: 'CUST-001',
        CHANNEL: 'SAP Build Workzone',
        EVENT_TS: '2024-07-25T09:30:00Z',
        SENTIMENT: 0.78,
      },
      {
        EVENT_ID: 'EVT-1002',
        CUSTOMER_ID: 'CUST-001',
        CHANNEL: 'SAP Store Chat',
        EVENT_TS: '2024-07-25T12:15:00Z',
        SENTIMENT: -0.12,
      },
    ],
  },
  {
    name: 'CUS_SUPPORT_CASES',
    desc: 'Ticket backlog enriched with priority, SLA timers, and resolution KPIs.',
    columns: [
      { name: 'CASE_ID', type: 'NVARCHAR(40)', isPrimaryKey: true, nullable: false, description: 'Support case identifier' },
      { name: 'CUSTOMER_ID', type: 'NVARCHAR(40)', description: 'Related customer' },
      { name: 'PRIORITY', type: 'NVARCHAR(20)', description: 'Ticket priority description' },
      { name: 'SLA_STATUS', type: 'NVARCHAR(20)', description: 'SLA met/at risk/breached state' },
      { name: 'RESOLUTION_HOURS', type: 'DECIMAL(6,2)', description: 'Resolution time in hours' },
    ],
    rows: [
      {
        CASE_ID: 'CASE-9001',
        CUSTOMER_ID: 'CUST-001',
        PRIORITY: 'High',
        SLA_STATUS: 'At Risk',
        RESOLUTION_HOURS: 32.5,
      },
    ],
  },
  {
    name: 'CUS_VALUE_METRICS',
    desc: 'Rolling 360° lifetime value metrics including churn propensity.',
    columns: [
      { name: 'CUSTOMER_ID', type: 'NVARCHAR(40)', isPrimaryKey: true, nullable: false },
      { name: 'ARR', type: 'DECIMAL(15,2)', description: 'Annual recurring revenue' },
      { name: 'NRR', type: 'DECIMAL(5,2)', description: 'Net revenue retention percentage' },
      { name: 'CHURN_PROPENSITY', type: 'DECIMAL(4,2)', description: 'Predicted churn probability' },
      { name: 'UPDATED_AT', type: 'DATE', description: 'Date of calculation' },
    ],
    rows: [
      {
        CUSTOMER_ID: 'CUST-001',
        ARR: 1280000.0,
        NRR: 114.5,
        CHURN_PROPENSITY: 0.18,
        UPDATED_AT: '2024-07-24',
      },
    ],
  },
  {
    name: 'CUS_INFLUENCERS',
    desc: 'Relationship graph data for buying centers and key influencers.',
    columns: [
      { name: 'NODE_ID', type: 'NVARCHAR(40)', isPrimaryKey: true, nullable: false },
      { name: 'CUSTOMER_ID', type: 'NVARCHAR(40)' },
      { name: 'CONTACT_NAME', type: 'NVARCHAR(120)' },
      { name: 'ROLE', type: 'NVARCHAR(80)' },
      { name: 'INFLUENCE_SCORE', type: 'DECIMAL(4,2)' },
    ],
    rows: [
      {
        NODE_ID: 'NODE-1',
        CUSTOMER_ID: 'CUST-001',
        CONTACT_NAME: 'Meera Ghose',
        ROLE: 'Executive Sponsor',
        INFLUENCE_SCORE: 0.92,
      },
    ],
  },
  {
    name: 'CUS_SUCCESS_PLANS',
    desc: 'Customer success plan milestones, owners, and success indicators.',
    columns: [
      { name: 'PLAN_ID', type: 'NVARCHAR(40)', isPrimaryKey: true, nullable: false },
      { name: 'CUSTOMER_ID', type: 'NVARCHAR(40)' },
      { name: 'MILESTONE', type: 'NVARCHAR(120)' },
      { name: 'OWNER', type: 'NVARCHAR(120)' },
      { name: 'TARGET_DATE', type: 'DATE' },
      { name: 'STATUS', type: 'NVARCHAR(30)' },
    ],
    rows: [
      {
        PLAN_ID: 'PLAN-2024-Q3',
        CUSTOMER_ID: 'CUST-001',
        MILESTONE: 'Launch Joule guided onboarding',
        OWNER: 'Iris Mayer',
        TARGET_DATE: '2024-09-15',
        STATUS: 'In Progress',
      },
    ],
  },
  {
    name: 'CUS_USAGE_HEATMAP',
    desc: 'Product usage telemetry aggregated by feature cluster and geography.',
    columns: [
      { name: 'FEATURE_CLUSTER', type: 'NVARCHAR(80)', isPrimaryKey: true, nullable: false },
      { name: 'REGION', type: 'NVARCHAR(40)', isPrimaryKey: true, nullable: false },
      { name: 'MONTH', type: 'NVARCHAR(7)', description: 'Year-month bucket' },
      { name: 'ACTIVE_USERS', type: 'INTEGER', description: 'Active seats during the period' },
      { name: 'USAGE_SCORE', type: 'DECIMAL(4,2)', description: 'Relative adoption score' },
    ],
    rows: [
      {
        FEATURE_CLUSTER: 'Process Automation',
        REGION: 'EMEA',
        MONTH: '2024-06',
        ACTIVE_USERS: 184,
        USAGE_SCORE: 0.81,
      },
    ],
  },
  {
    name: 'CUS_FINANCIAL_SUMMARY',
    desc: 'Commercial data with ARR, NRR, and upsell potential scoring.',
    columns: [
      { name: 'CUSTOMER_ID', type: 'NVARCHAR(40)', isPrimaryKey: true, nullable: false },
      { name: 'ANNUAL_SPEND', type: 'DECIMAL(15,2)' },
      { name: 'UPSELL_PIPELINE', type: 'DECIMAL(15,2)' },
      { name: 'RENEWAL_DATE', type: 'DATE' },
      { name: 'FINANCE_NOTES', type: 'NVARCHAR(255)' },
    ],
    rows: [
      {
        CUSTOMER_ID: 'CUST-001',
        ANNUAL_SPEND: 1580000.0,
        UPSELL_PIPELINE: 210000.0,
        RENEWAL_DATE: '2025-03-01',
        FINANCE_NOTES: 'Expansion forecast driven by SAP Joule guided workflows.',
      },
    ],
  },
  {
    name: 'CUS_ADOPTION_SIGNALS',
    desc: 'Leading indicators from enablement, training, and community activity.',
    columns: [
      { name: 'SIGNAL_ID', type: 'NVARCHAR(40)', isPrimaryKey: true, nullable: false },
      { name: 'CUSTOMER_ID', type: 'NVARCHAR(40)' },
      { name: 'SIGNAL_TYPE', type: 'NVARCHAR(80)' },
      { name: 'SIGNAL_TS', type: 'TIMESTAMP' },
      { name: 'SEVERITY', type: 'NVARCHAR(20)' },
    ],
    rows: [
      {
        SIGNAL_ID: 'SIG-7788',
        CUSTOMER_ID: 'CUST-001',
        SIGNAL_TYPE: 'Training Completion',
        SIGNAL_TS: '2024-07-20T08:00:00Z',
        SEVERITY: 'Positive',
      },
    ],
  },
  {
    name: 'CUS_HEALTH_INDEX',
    desc: 'Composite health score incorporating support, finance, and advocacy.',
    columns: [
      { name: 'CUSTOMER_ID', type: 'NVARCHAR(40)', isPrimaryKey: true, nullable: false },
      { name: 'OVERALL_HEALTH', type: 'DECIMAL(4,2)' },
      { name: 'SUPPORT_SCORE', type: 'DECIMAL(4,2)' },
      { name: 'ADOPTION_SCORE', type: 'DECIMAL(4,2)' },
      { name: 'ADVOCACY_SCORE', type: 'DECIMAL(4,2)' },
      { name: 'LAST_UPDATED', type: 'DATE' },
    ],
    rows: [
      {
        CUSTOMER_ID: 'CUST-001',
        OVERALL_HEALTH: 0.84,
        SUPPORT_SCORE: 0.76,
        ADOPTION_SCORE: 0.88,
        ADVOCACY_SCORE: 0.9,
        LAST_UPDATED: '2024-07-24',
      },
    ],
  },
];

/**
 * Generates a deterministic mock payload that mirrors the production API shape.
 * Keeps the UI demo-friendly while remaining easy to swap with a real fetch.
 */
export const getMockDemoPackage = (
  customer: string,
  useCase: string,
): DemoPackageResponse => {
  const safeCustomer = customer?.trim() || 'Launch Partner';
  const safeUseCase = useCase?.trim() || 'experience orchestration';

  return {
    schemaName: `JOULE_${safeCustomer.replace(/[^a-zA-Z0-9]/g, '').toUpperCase()}_${safeUseCase
      .replace(/[^a-zA-Z0-9]/g, '')
      .toUpperCase()}`.slice(0, 60) || 'JOULE_DEMO_SCHEMA',
    agentName: `SAP Joule ${safeCustomer} ${safeUseCase.split(' ')[0] ?? 'Insight'} Navigator`,
    agentPrompt: `You are SAP Joule, the Make-a-Wish demo agent named ${safeCustomer} ${safeUseCase
      .split(' ')[0]
      ?.toUpperCase()} Navigator. Craft an immersive story showing how SAP BTP, SAP Build, SAP Joule assistants, and SAP AI Core accelerate ${safeUseCase} for ${safeCustomer}. Blend SAP Fiori UX and Apple glass-inspired visuals while citing the curated 10-table dataset. Keep responses grounded in SAP terminology, compliance, and go-live readiness steps. End each hand-off with a Joule tip.`,
    tables: baseTables.map((table, index) => ({
      ...table,
      desc:
        index === 0
          ? `${table.desc} Tailored to ${safeCustomer}'s profile and ${safeUseCase} success criteria, stamped by SAP Joule.`
          : `${table.desc} Powered by Joule insights for ${safeCustomer}.`,
    })),
    businessCaseCard: `📊 Business Case Card\n🔎 Problem: ${safeCustomer} teams struggle to align on ${safeUseCase} KPIs across silos.\n💡 Solution: Deploy an event-driven SAP BTP cockpit with guided SAP Joule agents, Fiori workzones, and Perplexity research boosts.\n🎯 Benefits: Harmonised data flows, proactive adoption nudges, and faster value realization with Joule guardrails.\n💰 ROI: 28% lift in expansion revenue, 35% faster onboarding, and reduced support backlog thanks to Joule-assisted automation.`,
  };
};
