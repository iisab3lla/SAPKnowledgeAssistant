import { type FormEvent, type KeyboardEvent, type ReactNode, useMemo, useRef, useState } from "react";

type Source = {
  file_name: string;
  document_type: string;
  page: number | null;
  record_number: number | null;
  line_number: number | null;
  chunk_id: string;
};

type ChatResponse = {
  answer: string;
  sources: Source[];
  used_ai: boolean;
};

type Message = {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: Source[];
  usedAi?: boolean;
};

const suggestions = [
  "O que é SAP S/4HANA?",
  "Como funciona o SAP Concur?",
  "Onde a SAP atua no Brasil?",
  "O que é SAP BTP?",
];

const recentQuestions = [
  "O que é SAP BTP?",
  "Principais recursos do SAP S/4HANA",
  "Módulos do SAP Concur",
  "Escritórios SAP no Brasil",
];

function ProductIcon() {
  return (
    <svg viewBox="0 0 32 32" aria-hidden="true">
      <path d="m16 4 10 6-10 6-10-6 10-6Z" />
      <path d="M6 10v12l10 6V16M26 10v12l-10 6" />
    </svg>
  );
}

function TechnologyIcon() {
  return (
    <svg viewBox="0 0 32 32" aria-hidden="true">
      <path d="M11 8h13v19H7V12l4-4Z" />
      <path d="M11 8v4H7M4 16h14M4 21h10M15 5h10" />
    </svg>
  );
}

function LocationIcon() {
  return (
    <svg viewBox="0 0 32 32" aria-hidden="true">
      <circle cx="16" cy="16" r="11" />
      <path d="M5 16h22M16 5c3 3 4 7 4 11s-1 8-4 11M16 5c-3 3-4 7-4 11s1 8 4 11" />
    </svg>
  );
}

function CompanyIcon() {
  return (
    <svg viewBox="0 0 32 32" aria-hidden="true">
      <path d="M6 27V9h12v18M18 27V4h8v23M3 27h26M10 13h4M10 18h4M10 23h4M21 9h3M21 14h3M21 19h3" />
    </svg>
  );
}

function SendIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="m21 3-7.3 18-3.2-7.5L3 10.3 21 3Z" />
      <path d="m10.5 13.5 4.2-4.2" />
    </svg>
  );
}

function PlusIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M12 5v14M5 12h14" />
    </svg>
  );
}

function TrashIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M5 7h14M10 4h4l1 3H9l1-3ZM8 10v8M12 10v8M16 10v8M6 7l1 14h10l1-14" />
    </svg>
  );
}

function App() {
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showClearConfirmation, setShowClearConfirmation] = useState(false);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const hasConversation = messages.length > 0;
  const visibleRecentQuestions = useMemo(
    () => (hasConversation ? messages.filter((message) => message.role === "user").slice(-4).reverse() : recentQuestions),
    [hasConversation, messages],
  );

  function selectSuggestion(value: string) {
    setQuestion(value);
    setError(null);
    inputRef.current?.focus();
  }

  function clearChat() {
    setMessages([]);
    setQuestion("");
    setError(null);
    setShowClearConfirmation(false);
  }

  async function submitQuestion(event?: FormEvent) {
    event?.preventDefault();
    const trimmedQuestion = question.trim();
    if (!trimmedQuestion || isLoading) return;

    const userMessage: Message = {
      id: `user-${Date.now()}`,
      role: "user",
      content: trimmedQuestion,
    };
    setMessages((current) => [...current, userMessage]);
    setQuestion("");
    setError(null);
    setIsLoading(true);

    try {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: trimmedQuestion }),
      });

      if (!response.ok) {
        throw new Error(
          response.status === 402 || response.status === 403
            ? "A IA está indisponível ou sem créditos no momento. Tente novamente mais tarde."
            : "Não foi possível consultar o assistente agora.",
        );
      }

      const data = (await response.json()) as ChatResponse;
      setMessages((current) => [
        ...current,
        {
          id: `assistant-${Date.now()}`,
          role: "assistant",
          content: data.answer,
          sources: data.sources,
          usedAi: data.used_ai,
        },
      ]);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Erro inesperado ao consultar o assistente.");
    } finally {
      setIsLoading(false);
    }
  }

  function handleInputKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      void submitQuestion();
    }
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand" aria-label="SAP Knowledge Assistant">
          <span className="brand-mark" aria-hidden="true" />
          <span>SAP Knowledge Assistant</span>
        </div>

        <button className="new-conversation" type="button" onClick={() => (hasConversation ? setShowClearConfirmation(true) : selectSuggestion(""))}>
          <PlusIcon />
          <span>Nova conversa</span>
        </button>

        <div className="sidebar-section">
          <h2>Conversas recentes</h2>
          <nav aria-label="Conversas recentes">
            {visibleRecentQuestions.map((item, index) => (
              <button
                className={`recent-conversation ${index === 0 ? "is-active" : ""}`}
                key={`${item}-${index}`}
                type="button"
                onClick={() => selectSuggestion(typeof item === "string" ? item : item.content)}
              >
                {typeof item === "string" ? item : item.content}
              </button>
            ))}
          </nav>
        </div>

        <button
          className="clear-chat-button"
          type="button"
          onClick={() => setShowClearConfirmation(true)}
          disabled={!hasConversation}
        >
          <TrashIcon />
          Apagar chat
        </button>
      </aside>

      <main className="main-content">
        <div className={`workspace ${hasConversation ? "workspace-conversation" : ""}`}>
          {!hasConversation ? (
            <section className="welcome-section" aria-labelledby="welcome-title">
              <p className="eyebrow">CONHECIMENTO SAP</p>
              <h1 id="welcome-title">Como posso ajudar hoje?</h1>
              <p className="welcome-copy">Faça perguntas sobre produtos, tecnologias, sistemas e informações da SAP.</p>

              <div className="category-grid">
                <CategoryCard icon={<ProductIcon />} tone="blue" title="Produtos" description="Explore produtos e soluções da SAP para sua empresa." />
                <CategoryCard icon={<TechnologyIcon />} tone="purple" title="Tecnologias e Sistemas" description="Conheça tecnologias, sistemas e integrações SAP." />
                <CategoryCard icon={<LocationIcon />} tone="green" title="Localizações" description="Encontre escritórios e operações da SAP no mundo." />
                <CategoryCard icon={<CompanyIcon />} tone="orange" title="Empresa" description="Saiba mais sobre a empresa, cultura e iniciativas da SAP." />
              </div>
            </section>
          ) : (
            <section className="conversation" aria-live="polite">
              <div className="conversation-heading">
                <p className="eyebrow">CONVERSA ATUAL</p>
                <h1>Conhecimento SAP</h1>
              </div>
              {messages.map((message) => (
                <article className={`message message-${message.role}`} key={message.id}>
                  <div className="message-label">{message.role === "user" ? "Você" : message.usedAi ? "Assistente SAP · IA + base local" : "Assistente SAP · base local"}</div>
                  <p>{message.content}</p>
                  {message.role === "assistant" && message.sources && message.sources.length > 0 && (
                    <div className="source-list">
                      <span className="source-heading">Fontes consultadas</span>
                      {message.sources.map((source) => (
                        <div className="source-item" key={source.chunk_id}>
                          <span className="source-file">{source.file_name}</span>
                          <span>{source.document_type.toUpperCase()}</span>
                          {source.page !== null && <span>p. {source.page}</span>}
                          {source.record_number !== null && <span>registro {source.record_number}</span>}
                          {source.line_number !== null && <span>linha {source.line_number}</span>}
                        </div>
                      ))}
                    </div>
                  )}
                </article>
              ))}
              {isLoading && <div className="loading-state"><span className="loading-dot" /> Consultando a base local...</div>}
            </section>
          )}

          <section className="composer-section" aria-label="Enviar pergunta">
            {error && <div className="error-banner" role="alert">{error}</div>}
            <form className="composer" onSubmit={submitQuestion}>
              <textarea
                ref={inputRef}
                value={question}
                onChange={(event) => setQuestion(event.target.value)}
                onKeyDown={handleInputKeyDown}
                placeholder="Digite sua pergunta sobre a SAP..."
                aria-label="Digite sua pergunta sobre a SAP"
                rows={1}
                disabled={isLoading}
              />
              <button type="submit" className="send-button" disabled={!question.trim() || isLoading}>
                <SendIcon />
                <span>{isLoading ? "Consultando" : "Enviar"}</span>
              </button>
            </form>
            {!hasConversation && (
              <div className="suggestion-row" aria-label="Perguntas sugeridas">
                {suggestions.map((suggestion) => (
                  <button type="button" className="suggestion-button" key={suggestion} onClick={() => selectSuggestion(suggestion)}>
                    {suggestion}
                  </button>
                ))}
              </div>
            )}
            <p className="disclaimer">As respostas são geradas com base na base de conhecimento SAP disponível.</p>
          </section>
        </div>
      </main>

      {showClearConfirmation && (
        <div className="modal-backdrop" role="presentation" onClick={() => setShowClearConfirmation(false)}>
          <div className="confirmation-modal" role="dialog" aria-modal="true" aria-labelledby="clear-title" onClick={(event) => event.stopPropagation()}>
            <div className="modal-icon"><TrashIcon /></div>
            <h2 id="clear-title">Apagar esta conversa?</h2>
            <p>As mensagens desta conversa serão removidas da tela.</p>
            <div className="modal-actions">
              <button type="button" className="secondary-button" onClick={() => setShowClearConfirmation(false)}>Cancelar</button>
              <button type="button" className="danger-button" onClick={clearChat}>Apagar chat</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function CategoryCard({ icon, tone, title, description }: { icon: ReactNode; tone: string; title: string; description: string }) {
  return (
    <button type="button" className="category-card" onClick={() => undefined}>
      <span className={`category-icon ${tone}`}>{icon}</span>
      <strong>{title}</strong>
      <span>{description}</span>
    </button>
  );
}

export default App;
