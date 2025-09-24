import { FormEvent, useMemo, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import ResultCard from './components/ResultCard';
import { DemoPackageResponse, getMockDemoPackage } from './api/mock';
import { fetchJouleDemoFromPerplexity } from './api/perplexity';

const SAP_AGENT_AUTH_URL = 'https://agents-y0yj1uar.authentication.eu12.hana.ondemand.com';
const SAP_AGENT_UI_BASE_URL =
  'https://agents-y0yj1uar.baf-dev.cfapps.eu12.hana.ondemand.com/ui/index.html#/agents';
const SAP_AGENT_CREATE_ENDPOINT = '/api/agents';

const generateDemoPackage = async (
  customer: string,
  useCase: string,
): Promise<DemoPackageResponse> => {
  try {
    return await fetchJouleDemoFromPerplexity(customer, useCase);
  } catch (error) {
    console.info('Falling back to mock data for demo purposes.', error);
    await new Promise((resolve) => setTimeout(resolve, 500));
    return getMockDemoPackage(customer, useCase);
  }
};

const parseBusinessCaseSections = (
  card: string,
): { icon: string; title: string; content: string }[] => {
  const sectionPattern = /^([\p{Extended_Pictographic}]+)\s*(.+?):\s*(.+)$/u;

  return card
    .split('\n')
    .map((line) => line.trim())
    .filter((line) => sectionPattern.test(line))
    .map((line) => {
      const match = line.match(sectionPattern);
      if (!match) {
        return null;
      }

      const [, icon, title, content] = match;
      return { icon, title, content };
    })
    .filter((value): value is { icon: string; title: string; content: string } => Boolean(value));
};

const App = () => {
  const [customerName, setCustomerName] = useState('');
  const [useCase, setUseCase] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<DemoPackageResponse | null>(null);
  const [isPromptOpen, setIsPromptOpen] = useState(true);
  const [isCreatingAgent, setIsCreatingAgent] = useState(false);
  const [agentCreationMessage, setAgentCreationMessage] = useState<string | null>(null);
  const [agentId, setAgentId] = useState<string | null>(null);
  const [agentCreationError, setAgentCreationError] = useState<string | null>(null);

  const businessCaseSections = useMemo(
    () => (result ? parseBusinessCaseSections(result.businessCaseCard) : []),
    [result],
  );

  const agentCreationPayload = useMemo(
    () =>
      result
        ? {
            name: result.agentName,
            prompt: result.agentPrompt,
            customer: customerName.trim(),
            useCase: useCase.trim(),
            schemaName: result.schemaName,
            tables: result.tables,
            businessCaseCard: result.businessCaseCard,
          }
        : null,
    [result, customerName, useCase],
  );

  const handleGenerate = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    if (!customerName.trim() || !useCase.trim()) {
      setError('Please provide both a customer name and use case.');
      return;
    }

    setError(null);
    setIsLoading(true);
    setAgentCreationMessage(null);
    setAgentCreationError(null);

    try {
      const data = await generateDemoPackage(customerName.trim(), useCase.trim());
      setResult(data);
      setIsPromptOpen(true);
    } catch (err) {
      console.error(err);
      setError('Unable to generate a demo package right now. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleCreateAgent = async () => {
    if (!agentCreationPayload) {
      return;
    }

    setIsCreatingAgent(true);
    setAgentCreationMessage(null);
    setAgentCreationError(null);

    try {
      const response = await fetch(SAP_AGENT_CREATE_ENDPOINT, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(agentCreationPayload),
      });

      if (!response.ok) {
        throw new Error(`Agent creation failed: ${response.status}`);
      }

      const data = await response.json();
      const newAgentId = data?.agentId || data?.id || data?.ID;
      const agentUrl = data?.agentUrl || (newAgentId ? `${SAP_AGENT_UI_BASE_URL}/${newAgentId}` : null);

      if (!newAgentId) {
        throw new Error('Agent ID missing from response');
      }

      setAgentId(newAgentId);
      if (agentUrl) {
        setAgentCreationMessage(`Agent created via SAP Joule workspace. Opening the console at ${agentUrl} …`);
        window.open(agentUrl, '_blank', 'noopener');
      } else {
        setAgentCreationMessage('Agent created via SAP Joule workspace. Opening the agent console...');
        window.open(`${SAP_AGENT_UI_BASE_URL}/${newAgentId}`, '_blank', 'noopener');
      }
    } catch (createError) {
      console.error(createError);
      const fallbackId = agentId ?? window.crypto?.randomUUID?.();
      setAgentId(fallbackId || null);
      setAgentCreationError(
        'Unable to auto-create the agent. Opening the SAP Joule workspace so you can finish the setup manually.',
      );
      window.open(SAP_AGENT_AUTH_URL, '_blank', 'noopener');
    } finally {
      setIsCreatingAgent(false);
    }
  };

  return (
    <div className="relative min-h-screen w-full overflow-hidden bg-gray-950">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top,rgba(10,110,209,0.25),transparent_60%),radial-gradient(circle_at_bottom,rgba(47,223,132,0.2),transparent_65%)]"
      />

      <main className="relative z-10 mx-auto flex min-h-screen w-full max-w-6xl flex-col items-center justify-center px-6 py-16">
        <motion.div
          className="glass-panel card-border w-full max-w-3xl rounded-[32px] bg-gradient-to-br from-white/15 via-white/5 to-white/0 p-10 shadow-glass"
          initial={{ opacity: 0, scale: 0.96, y: 24 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          transition={{ duration: 0.6, ease: 'easeOut' }}
        >
          <div className="flex flex-col gap-3 text-center">
            <motion.p
              className="inline-flex items-center justify-center gap-2 self-center rounded-full border border-white/15 bg-white/10 px-4 py-1 text-xs font-semibold uppercase tracking-[0.35em] text-sap-accent"
              initial={{ opacity: 0, y: -12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2, duration: 0.6, ease: 'easeOut' }}
            >
              <span role="img" aria-hidden>
                ✨
              </span>
              SAP Joule Wishes
            </motion.p>
            <motion.h1
              className="bg-gradient-to-r from-sap-primary via-cyan-400 to-sap-accent bg-clip-text text-4xl font-semibold text-transparent md:text-5xl"
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3, duration: 0.7, ease: 'easeOut' }}
            >
              SAP Joule Demo Package Builder
            </motion.h1>
            <motion.p
              className="text-base text-gray-400"
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.4, duration: 0.7, ease: 'easeOut' }}
            >
              Blend SAP Fiori patterns with immersive glassmorphism while SAP Joule 🤖 curates the storyline, data, and activation kit for your next customer hero moment.
            </motion.p>
            <motion.ul
              className="mt-2 flex flex-wrap justify-center gap-3 text-sm text-sap-accent"
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.5, duration: 0.6, ease: 'easeOut' }}
            >
              <li className="rounded-full border border-white/10 bg-white/5 px-3 py-1">
                🌐 SAP BTP ready in minutes
              </li>
              <li className="rounded-full border border-white/10 bg-white/5 px-3 py-1">
                🤖 Joule-guided agent prompts
              </li>
              <li className="rounded-full border border-white/10 bg-white/5 px-3 py-1">
                📊 Fiori dashboards bootstrapped
              </li>
            </motion.ul>
          </div>

          <form onSubmit={handleGenerate} className="mt-10 space-y-6">
            <div className="grid gap-4">
              <label className="text-left text-sm font-medium text-gray-300" htmlFor="customer">
                Customer Name
              </label>
              <input
                id="customer"
                type="text"
                value={customerName}
                onChange={(event) => setCustomerName(event.target.value)}
                placeholder="e.g. Sapphire Ventures"
                className="w-full rounded-2xl border border-white/10 bg-white/10 px-4 py-3 text-base text-gray-50 placeholder:text-gray-500 focus:border-sap-primary focus:outline-none focus:ring-2 focus:ring-sap-primary/40"
              />
            </div>

            <div className="grid gap-4">
              <label className="text-left text-sm font-medium text-gray-300" htmlFor="useCase">
                Use Case
              </label>
              <textarea
                id="useCase"
                value={useCase}
                onChange={(event) => setUseCase(event.target.value)}
                placeholder="Describe the scenario you want to spotlight for the customer."
                rows={4}
                className="w-full resize-none rounded-2xl border border-white/10 bg-white/10 px-4 py-3 text-base text-gray-50 placeholder:text-gray-500 focus:border-sap-primary focus:outline-none focus:ring-2 focus:ring-sap-primary/40"
              />
            </div>

            {error && <p className="text-sm text-rose-300">{error}</p>}

            <motion.button
              type="submit"
              className="flex w-full items-center justify-center gap-2 rounded-2xl bg-gradient-to-r from-sap-primary via-cyan-400 to-sap-accent px-6 py-3 text-base font-semibold text-gray-950 shadow-lg shadow-sap-primary/25 transition-transform duration-300 hover:scale-[1.02] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sap-primary"
              whileTap={{ scale: 0.98 }}
              disabled={isLoading}
            >
              <span role="img" aria-hidden>
                🤖
              </span>
              {isLoading ? 'Joule is composing…' : 'Ask SAP Joule to generate'}
            </motion.button>
            <p className="text-center text-xs text-gray-400">
              🪄 SAP Joule weaves SAP Fiori, BTP, and Perplexity insights into your personalized launch kit.
            </p>
          </form>
        </motion.div>

        <AnimatePresence mode="wait">
          {result && (
            <motion.section
              key={result.agentName}
              className="mt-12 w-full space-y-8"
              initial={{ opacity: 0, y: 32 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 32 }}
              transition={{ duration: 0.6, ease: 'easeOut' }}
            >
              <motion.div
                className="text-center"
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1, duration: 0.6, ease: 'easeOut' }}
              >
                <p className="text-sm uppercase tracking-[0.35em] text-gray-500">
                  Joule featured agent
                </p>
                <h2 className="mt-2 bg-gradient-to-r from-sap-primary via-cyan-400 to-sap-accent bg-clip-text text-4xl font-bold text-transparent md:text-5xl">
                  {result.agentName}
                </h2>
                <p className="mt-3 text-base text-gray-400">
                  Crafted by SAP Joule to delight {customerName || 'your customer'} with {useCase || 'a visionary story'}.
                </p>
                <p className="mt-2 inline-flex items-center justify-center gap-2 rounded-full border border-white/15 bg-white/10 px-4 py-1 text-xs font-semibold uppercase tracking-[0.25em] text-sap-accent">
                  <span role="img" aria-hidden>
                    🗄️
                  </span>
                  Schema: {result.schemaName}
                </p>
              </motion.div>

              <ResultCard
                title="Agent System Prompt"
                description="Plug this Joule-tuned prompt into SAP BTP, Python notebooks, or Node services."
                icon="🧠"
                delay={0.1}
              >
                <button
                  type="button"
                  onClick={() => setIsPromptOpen((value) => !value)}
                  className="mb-3 flex items-center gap-2 text-xs uppercase tracking-wide text-cyan-300"
                >
                  <span>{isPromptOpen ? 'Hide prompt' : 'Show prompt'}</span>
                </button>
                <AnimatePresence initial={false}>
                  {isPromptOpen && (
                    <motion.div
                      className="scrollbar-hidden max-h-72 overflow-y-auto rounded-2xl border border-white/10 bg-gray-900/80 p-4 text-left text-sm leading-relaxed text-slate-200 shadow-inner whitespace-pre-wrap"
                      initial={{ opacity: 0, y: -8 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -8 }}
                      transition={{ duration: 0.4, ease: 'easeOut' }}
                    >
                      {result.agentPrompt}
                    </motion.div>
                  )}
                </AnimatePresence>
              </ResultCard>

              <ResultCard
                title="Curated Data Tables"
                description="10-table launchpad that maps SAP BTP assets to your story, stitched by SAP Joule."
                icon="🗂️"
                delay={0.2}
              >
                <div className="grid gap-4 md:grid-cols-2">
                  {result.tables.map((table) => (
                    <motion.div
                      key={table.name}
                      className="rounded-2xl border border-white/10 bg-white/5 p-4 backdrop-blur"
                      initial={{ opacity: 0, y: 12 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ duration: 0.5, ease: 'easeOut' }}
                    >
                      <p className="font-semibold tracking-wide text-cyan-200">{table.name}</p>
                      <p className="mt-2 text-sm text-gray-300">{table.desc}</p>
                      <div className="mt-3 space-y-2">
                        <div>
                          <p className="text-xs font-semibold uppercase tracking-wide text-sap-accent/80">
                            📋 Columns
                          </p>
                          <ul className="mt-1 space-y-1 text-xs text-gray-300">
                            {table.columns.map((column) => (
                              <li key={`${table.name}-${column.name}`}>
                                <span className="font-semibold text-gray-100">{column.name}</span>
                                <span className="text-gray-500"> · {column.type}</span>
                                {column.description && <span className="text-gray-500"> — {column.description}</span>}
                                {column.nullable === false && <span className="text-sap-accent"> · NOT NULL</span>}
                                {column.isPrimaryKey && <span className="text-sap-accent"> · PK</span>}
                              </li>
                            ))}
                          </ul>
                        </div>
                        {table.rows.length > 0 && (
                          <div>
                            <p className="text-xs font-semibold uppercase tracking-wide text-sap-accent/80">
                              📦 Sample Rows
                            </p>
                            <ul className="mt-1 space-y-1 overflow-hidden text-xs text-gray-300">
                              {table.rows.slice(0, 2).map((row, index) => (
                                <li key={`${table.name}-row-${index}`} className="truncate">
                                  {Object.entries(row)
                                    .map(([key, value]) => `${key}: ${String(value)}`)
                                    .join(' · ')}
                                </li>
                              ))}
                              {table.rows.length > 2 && <li className="text-sap-accent/80">… {table.rows.length - 2} more rows</li>}
                            </ul>
                          </div>
                        )}
                      </div>
                    </motion.div>
                  ))}
                </div>
              </ResultCard>

              <ResultCard
                title="Business Case Narrative"
                description="Ready-to-share storyline for executives, solution engineers, and value teams — narrated by SAP Joule."
                icon="📈"
                delay={0.3}
              >
                <div className="grid gap-4">
                  {businessCaseSections.map((section) => (
                    <div
                      key={section.title}
                      className="rounded-2xl border border-white/10 bg-gradient-to-br from-white/10 via-white/5 to-transparent p-4"
                    >
                      <div className="flex items-start gap-3">
                        <span className="text-2xl leading-none">{section.icon}</span>
                        <div>
                          <h4 className="text-lg font-semibold text-gray-100">{section.title}</h4>
                          <p className="mt-1 text-sm text-gray-300">{section.content}</p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
                <p className="mt-6 text-sm text-gray-400">
                  🧭 Joule tip: export this narrative into SAP Build Apps or SAP Analytics Cloud for a guided value deck.
                </p>
              </ResultCard>
            </motion.section>
          )}
        </AnimatePresence>

        <motion.div
          className="mt-16 w-full max-w-4xl"
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4, duration: 0.6, ease: 'easeOut' }}
        >
          <div className="glass-panel card-border rounded-[28px] bg-gradient-to-br from-white/15 via-white/5 to-transparent p-8">
            <div className="flex flex-col items-center gap-4 text-center">
              <h3 className="text-2xl font-semibold text-gray-100">Bring this into SAP Joule Workspace</h3>
              <p className="text-sm text-gray-400">
                Ready to activate this story? We will hand off the agent blueprint, tables, and business case to the SAP Joule workspace at{' '}
                <span className="font-semibold text-sap-accent">{SAP_AGENT_AUTH_URL}</span>.
              </p>
              {result && (
                <p className="text-xs text-gray-500">
                  Target SAP HANA schema: <span className="text-sap-accent">{result.schemaName}</span>
                </p>
              )}
              {agentCreationMessage && <p className="text-sm text-sap-accent">{agentCreationMessage}</p>}
              {agentCreationError && <p className="text-sm text-rose-300">{agentCreationError}</p>}
              <motion.button
                type="button"
                className="flex items-center gap-2 rounded-2xl bg-gradient-to-r from-sap-primary via-cyan-400 to-sap-accent px-6 py-3 text-base font-semibold text-gray-950 shadow-lg shadow-sap-primary/30 transition-transform duration-300 hover:scale-[1.02] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sap-primary disabled:cursor-not-allowed disabled:opacity-60"
                whileTap={{ scale: 0.97 }}
                onClick={handleCreateAgent}
                disabled={!agentCreationPayload || isCreatingAgent}
              >
                <span role="img" aria-hidden>
                  🚀
                </span>
                {isCreatingAgent ? 'Syncing with SAP Joule…' : 'Create and open in SAP Joule'}
              </motion.button>
              <p className="text-xs text-gray-500">
                You will be redirected to the SAP Joule authentication domain and then to the agent console.
              </p>
            </div>
          </div>
        </motion.div>
      </main>
    </div>
  );
};

export default App;
