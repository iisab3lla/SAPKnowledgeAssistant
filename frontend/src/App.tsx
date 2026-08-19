import { type FormEvent, type KeyboardEvent, type ReactNode, useEffect, useMemo, useRef, useState } from "react";

type Source = { file_name: string; document_type: string; page: number | null; record_number: number | null; line_number: number | null; chunk_id: string };
type ChatResponse = { answer: string; sources: Source[]; used_ai: boolean };
type Message = { id: string; role: "user" | "assistant"; content: string; sources?: Source[]; usedAi?: boolean };
type Conversation = { id: string; title: string; messages: Message[]; createdAt: string };
type CategoryId = "products" | "technology" | "locations" | "company";
type Category = { id: CategoryId; title: string; description: string; tone: string; icon: ReactNode; suggestions: string[] };

const STORAGE_KEY = "sap-knowledge-assistant-conversations";

function loadConversations(): Conversation[] {
  try {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    if (!stored) return [];
    const parsed: unknown = JSON.parse(stored);
    if (!Array.isArray(parsed)) return [];
    return parsed.filter((conversation): conversation is Conversation =>
      typeof conversation === "object" && conversation !== null &&
      typeof conversation.id === "string" && typeof conversation.title === "string" &&
      Array.isArray(conversation.messages) && typeof conversation.createdAt === "string",
    );
  } catch { return []; }
}

function ProductIcon() { return <svg viewBox="0 0 32 32" aria-hidden="true"><path d="m16 4 10 6-10 6-10-6 10-6Z" /><path d="M6 10v12l10 6V16M26 10v12l-10 6" /></svg>; }
function TechnologyIcon() { return <svg viewBox="0 0 32 32" aria-hidden="true"><path d="M11 8h13v19H7V12l4-4Z" /><path d="M11 8v4H7M4 16h14M4 21h10M15 5h10" /></svg>; }
function LocationIcon() { return <svg viewBox="0 0 32 32" aria-hidden="true"><circle cx="16" cy="16" r="11" /><path d="M5 16h22M16 5c3 3 4 7 4 11s-1 8-4 11M16 5c-3 3-4 7-4 11s1 8 4 11" /></svg>; }
function CompanyIcon() { return <svg viewBox="0 0 32 32" aria-hidden="true"><path d="M6 27V9h12v18M18 27V4h8v23M3 27h26M10 13h4M10 18h4M10 23h4M21 9h3M21 14h3M21 19h3" /></svg>; }
function SendIcon() { return <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m21 3-7.3 18-3.2-7.5L3 10.3 21 3Z" /><path d="m10.5 13.5 4.2-4.2" /></svg>; }
function PlusIcon() { return <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 5v14M5 12h14" /></svg>; }
function TrashIcon() { return <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 7h14M10 4h4l1 3H9l1-3ZM8 10v8M12 10v8M16 10v8M6 7l1 14h10l1-14" /></svg>; }
function CloseIcon() { return <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m6 6 12 12M18 6 6 18" /></svg>; }

const categories: Category[] = [
  { id: "products", title: "Produtos", description: "Explore produtos e soluções da SAP para sua empresa.", tone: "blue", icon: <ProductIcon />, suggestions: ["O que é o SAP S/4HANA?", "Como funciona o SAP Concur?", "Quais são os principais produtos da SAP?"] },
  { id: "technology", title: "Tecnologias e Sistemas", description: "Conheça tecnologias, sistemas e integrações SAP.", tone: "purple", icon: <TechnologyIcon />, suggestions: ["O que é SAP BTP?", "Quais tecnologias a SAP utiliza?", "Como os sistemas SAP se integram?"] },
  { id: "locations", title: "Localizações", description: "Encontre escritórios e operações da SAP no mundo.", tone: "green", icon: <LocationIcon />, suggestions: ["Onde a SAP possui escritórios?", "Aonde a SAP está localizada no Brasil?", "Em quais países a SAP atua?"] },
  { id: "company", title: "Empresa", description: "Saiba mais sobre a empresa, cultura e iniciativas da SAP.", tone: "orange", icon: <CompanyIcon />, suggestions: ["Como é a cultura da SAP?", "Quais são os valores da SAP?", "Quais iniciativas a SAP possui?"] },
];

function App() {
  const [conversations, setConversations] = useState<Conversation[]>(loadConversations);
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);
  const [question, setQuestion] = useState("");
  const [selectedCategoryId, setSelectedCategoryId] = useState<CategoryId>("products");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [conversationToDelete, setConversationToDelete] = useState<Conversation | null>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => { window.localStorage.setItem(STORAGE_KEY, JSON.stringify(conversations)); }, [conversations]);

  const activeConversation = useMemo(() => conversations.find((conversation) => conversation.id === activeConversationId) ?? null, [activeConversationId, conversations]);
  const selectedCategory = categories.find((category) => category.id === selectedCategoryId) ?? categories[0];
  const hasConversation = activeConversation !== null;

  function selectSuggestion(value: string) { setQuestion(value); setError(null); inputRef.current?.focus(); }
  function startNewConversation() { if (!isLoading) { setActiveConversationId(null); setQuestion(""); setError(null); inputRef.current?.focus(); } }
  function selectCategory(categoryId: CategoryId) { setSelectedCategoryId(categoryId); setError(null); }
  function requestConversationDeletion(conversation: Conversation) { if (!isLoading) setConversationToDelete(conversation); }
  function deleteConversation() {
    if (!conversationToDelete) return;
    setConversations((current) => current.filter((conversation) => conversation.id !== conversationToDelete.id));
    if (activeConversationId === conversationToDelete.id) { setActiveConversationId(null); setQuestion(""); setError(null); }
    setConversationToDelete(null);
  }

  async function submitQuestion(event?: FormEvent) {
    event?.preventDefault();
    const trimmedQuestion = question.trim();
    if (!trimmedQuestion || isLoading) return;
    const userMessage: Message = { id: `user-${Date.now()}`, role: "user", content: trimmedQuestion };
    const conversationId = activeConversationId ?? `conversation-${Date.now()}`;
    setConversations((current) => {
      const existingConversation = current.find((conversation) => conversation.id === conversationId);
      if (existingConversation) return current.map((conversation) => conversation.id === conversationId ? { ...conversation, messages: [...conversation.messages, userMessage] } : conversation);
      return [{ id: conversationId, title: trimmedQuestion, messages: [userMessage], createdAt: new Date().toISOString() }, ...current];
    });
    setActiveConversationId(conversationId); setQuestion(""); setError(null); setIsLoading(true);
    try {
      const response = await fetch("/api/chat", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ message: trimmedQuestion }) });
      if (!response.ok) throw new Error(response.status === 402 || response.status === 403 ? "A IA está indisponível ou sem créditos no momento. Tente novamente mais tarde." : "Não foi possível consultar o assistente agora.");
      const data = (await response.json()) as ChatResponse;
      const assistantMessage: Message = { id: `assistant-${Date.now()}`, role: "assistant", content: data.answer, sources: data.sources, usedAi: data.used_ai };
      setConversations((current) => current.map((conversation) => conversation.id === conversationId ? { ...conversation, messages: [...conversation.messages, assistantMessage] } : conversation));
    } catch (requestError) { setError(requestError instanceof Error ? requestError.message : "Erro inesperado ao consultar o assistente."); } finally { setIsLoading(false); }
  }

  function handleInputKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) { if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); void submitQuestion(); } }

  return <div className="app-shell">
    <aside className="sidebar">
      <div className="brand" aria-label="SAP Knowledge Assistant"><span className="brand-mark" aria-hidden="true" /><span>SAP Knowledge Assistant</span></div>
      <button className="new-conversation" type="button" onClick={startNewConversation} disabled={isLoading}><PlusIcon /><span>Nova conversa</span></button>
      <div className="sidebar-section"><h2>Conversas recentes</h2><nav aria-label="Conversas recentes">
        {conversations.map((conversation) => <div className={`recent-conversation ${conversation.id === activeConversationId ? "is-active" : ""}`} key={conversation.id}>
          <button className="recent-conversation-select" type="button" onClick={() => { setActiveConversationId(conversation.id); setError(null); }}>{conversation.title}</button>
          <button className="delete-conversation-icon" type="button" aria-label={`Excluir conversa: ${conversation.title}`} onClick={() => requestConversationDeletion(conversation)} disabled={isLoading}><CloseIcon /></button>
        </div>)}
      </nav></div>
    </aside>
    <main className="main-content"><div className={`workspace ${hasConversation ? "workspace-conversation" : ""}`}>
      {!hasConversation ? <section className="welcome-section" aria-labelledby="welcome-title"><p className="eyebrow">CONHECIMENTO SAP</p><h1 id="welcome-title">Como posso ajudar hoje?</h1><p className="welcome-copy">Faça perguntas sobre produtos, tecnologias, sistemas e informações da SAP.</p><div className="category-grid">{categories.map((category) => <CategoryCard key={category.id} category={category} selected={category.id === selectedCategoryId} onSelect={selectCategory} />)}</div></section> :
        <section className="conversation" aria-live="polite"><div className="conversation-heading"><div><p className="eyebrow">CONVERSA ATUAL</p><h1>Conhecimento SAP</h1></div><button className="delete-current-conversation" type="button" onClick={() => requestConversationDeletion(activeConversation)} disabled={isLoading}><TrashIcon /> Apagar conversa</button></div>
          {activeConversation.messages.map((message) => <article className={`message message-${message.role}`} key={message.id}><div className="message-label">{message.role === "user" ? "Você" : message.usedAi ? "Assistente SAP · IA + base local" : "Assistente SAP · base local"}</div><p>{message.content}</p>{message.role === "assistant" && message.sources && message.sources.length > 0 && <div className="source-list"><span className="source-heading">Fontes consultadas</span>{message.sources.map((source) => <div className="source-item" key={source.chunk_id}><span className="source-file">{source.file_name}</span><span>{source.document_type.toUpperCase()}</span>{source.page !== null && <span>p. {source.page}</span>}{source.record_number !== null && <span>registro {source.record_number}</span>}{source.line_number !== null && <span>linha {source.line_number}</span>}</div>)}</div>}</article>)}
          {isLoading && <div className="loading-state"><span className="loading-dot" /> Consultando a base local...</div>}
        </section>}
      <section className="composer-section" aria-label="Enviar pergunta">{error && <div className="error-banner" role="alert">{error}</div>}<form className="composer" onSubmit={submitQuestion}><textarea ref={inputRef} value={question} onChange={(event) => setQuestion(event.target.value)} onKeyDown={handleInputKeyDown} placeholder="Digite sua pergunta sobre a SAP..." aria-label="Digite sua pergunta sobre a SAP" rows={1} disabled={isLoading} /><button type="submit" className="send-button" disabled={!question.trim() || isLoading}><SendIcon /><span>{isLoading ? "Consultando" : "Enviar"}</span></button></form>
        {!hasConversation && <div className="suggestion-area"><p className="suggestion-label">Sugestões: {selectedCategory.title}</p><div className="suggestion-row" aria-label={`Perguntas sugeridas sobre ${selectedCategory.title}`}>{selectedCategory.suggestions.map((suggestion) => <button type="button" className="suggestion-button" key={suggestion} onClick={() => selectSuggestion(suggestion)}>{suggestion}</button>)}</div></div>}
        <p className="disclaimer">As respostas são geradas com base na base de conhecimento SAP disponível.</p></section>
    </div></main>
    {conversationToDelete && <div className="modal-backdrop" role="presentation" onClick={() => setConversationToDelete(null)}><div className="confirmation-modal" role="dialog" aria-modal="true" aria-labelledby="clear-title" onClick={(event) => event.stopPropagation()}><div className="modal-icon"><TrashIcon /></div><h2 id="clear-title">Apagar esta conversa?</h2><p>As mensagens desta conversa serão removidas deste navegador.</p><div className="modal-actions"><button type="button" className="secondary-button" onClick={() => setConversationToDelete(null)}>Cancelar</button><button type="button" className="danger-button" onClick={deleteConversation}>Apagar conversa</button></div></div></div>}
  </div>;
}

function CategoryCard({ category, selected, onSelect }: { category: Category; selected: boolean; onSelect: (categoryId: CategoryId) => void }) {
  return <button type="button" className={`category-card ${selected ? "is-selected" : ""}`} aria-pressed={selected} onClick={() => onSelect(category.id)}><span className={`category-icon ${category.tone}`}>{category.icon}</span><strong>{category.title}</strong><span>{category.description}</span></button>;
}

export default App;
