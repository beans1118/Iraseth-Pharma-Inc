'use client';

import Link from 'next/link';
import { useEffect, useRef, useState, type FormEvent } from 'react';
import { useCart } from './CartProvider';
import { company } from '@/lib/content';

type FAQ = { question: string; answer: string; href?: string; action?: string; keywords: string[] };
type ChatMessage = { id: number; sender: 'assistant' | 'visitor'; text: string; href?: string; action?: string };

const faqs: FAQ[] = [
  {
    question: 'How can I request a quotation?',
    answer: 'Choose available products and add them to My Order. Online quotation submission is not connected yet; meanwhile, you can send an inquiry through Contact.',
    href: '/contact', action: 'Contact Iraseth', keywords: ['quotation', 'quote', 'order', 'request', 'pricing', 'price'],
  },
  {
    question: 'What products do you offer?',
    answer: 'Our catalog covers medical and diagnostic devices, laboratory supplies, and related healthcare products. You can browse currently published listings on the Products page.',
    href: '/products', action: 'Explore products', keywords: ['product', 'catalog', 'offer', 'equipment', 'supplies'],
  },
  {
    question: 'What if a product is out of stock?',
    answer: 'Out-of-stock products cannot be added to My Order. For information about a particular item, you can contact our team.',
    href: '/contact', action: 'Ask our team', keywords: ['out of stock', 'stock', 'available', 'availability'],
  },
  {
    question: 'Where is your office?',
    answer: `Our listed office address is ${company.address}`,
    href: '/contact', action: 'View contact details', keywords: ['office', 'address', 'where', 'location', 'map'],
  },
  {
    question: 'How do I contact your team?',
    answer: `You can contact Iraseth Pharma through our Contact page. Our listed numbers are ${company.phone} and ${company.mobile}.`,
    href: '/contact', action: 'Contact us', keywords: ['contact', 'phone', 'call', 'email', 'message', 'reach'],
  },
];

const greeting: ChatMessage = {
  id: 0,
  sender: 'assistant',
  text: 'Hello! Welcome to Iraseth Pharma. 👋 I can answer common questions about our products, quotation inquiries, and contact details. Choose a question below or type one.',
};

function faqForQuestion(question: string): FAQ | undefined {
  const normalized = question.toLowerCase().trim();
  return faqs.find(faq => faq.question.toLowerCase() === normalized) ??
    faqs.find(faq => faq.keywords.some(keyword => normalized.includes(keyword)));
}

export default function FloatingActions() {
  const cart = useCart();
  const count = cart.items.reduce((total, item) => total + item.quantity, 0);
  const [chatOpen, setChatOpen] = useState(false);
  const [draft, setDraft] = useState('');
  const [messages, setMessages] = useState<ChatMessage[]>([greeting]);
  const nextMessageId = useRef(1);
  const widgetRef = useRef<HTMLDivElement>(null);
  const closeRef = useRef<HTMLButtonElement>(null);
  const transcriptRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!chatOpen) return;
    closeRef.current?.focus();
    const onKey = (event: KeyboardEvent) => { if (event.key === 'Escape') setChatOpen(false); };
    const onOutsideClick = (event: MouseEvent) => {
      if (widgetRef.current && !widgetRef.current.contains(event.target as Node)) setChatOpen(false);
    };
    document.addEventListener('keydown', onKey);
    document.addEventListener('mousedown', onOutsideClick);
    return () => {
      document.removeEventListener('keydown', onKey);
      document.removeEventListener('mousedown', onOutsideClick);
    };
  }, [chatOpen]);

  useEffect(() => {
    if (chatOpen && transcriptRef.current) transcriptRef.current.scrollTop = transcriptRef.current.scrollHeight;
  }, [chatOpen, messages]);

  function sendQuestion(value: string) {
    const question = value.trim().slice(0, 400);
    if (!question) return;
    const faq = faqForQuestion(question);
    const response: ChatMessage = faq
      ? { id: nextMessageId.current++, sender: 'assistant', text: faq.answer, href: faq.href, action: faq.action }
      : { id: nextMessageId.current++, sender: 'assistant', text: 'I can help with our product catalog, quotation process, stock availability, office location, and contact details. For other questions, please reach our team using Contact.', href: '/contact', action: 'Contact our team' };
    const visitor: ChatMessage = { id: nextMessageId.current++, sender: 'visitor', text: question };
    setMessages(previous => [...previous, visitor, response]);
    setDraft('');
  }

  function submitQuestion(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    sendQuestion(draft);
  }

  return <div ref={widgetRef} className="floating-widget">
    {chatOpen && <section className="chat-panel" role="dialog" aria-modal="false" aria-label="Iraseth Pharma FAQ chat">
      <div className="chat-top">
        <span className="chat-avatar" aria-hidden="true">IP</span>
        <div className="chat-heading">
          <h2>Iraseth Help</h2>
          <p>Automated FAQ assistant · not live chat</p>
        </div>
        <button ref={closeRef} type="button" className="chat-close" aria-label="Close FAQ chat" onClick={() => setChatOpen(false)}>✕</button>
      </div>
      <div className="chat-transcript" ref={transcriptRef} aria-live="polite" aria-relevant="additions text">
        {messages.map(message => <div key={message.id} className={'chat-message-row ' + (message.sender === 'visitor' ? 'from-visitor' : 'from-assistant')}>
          {message.sender === 'assistant' && <span className="chat-small-avatar" aria-hidden="true">IP</span>}
          <div className="chat-bubble">
            <p>{message.text}</p>
            {message.href && <Link href={message.href} onClick={() => setChatOpen(false)}>{message.action ?? 'Learn more'} ↗</Link>}
          </div>
        </div>)}
      </div>
      <div className="chat-bottom">
        <p className="chat-suggestion-label">COMMON QUESTIONS</p>
        <div className="chat-suggestions" aria-label="Suggested questions">
          {faqs.map(faq => <button type="button" key={faq.question} onClick={() => sendQuestion(faq.question)}>{faq.question}</button>)}
        </div>
        <form className="chat-compose" onSubmit={submitQuestion}>
          <label htmlFor="iraseth-chat-question" className="sr-only">Ask a question</label>
          <input id="iraseth-chat-question" type="text" maxLength={400} autoComplete="off" placeholder="Type your question..." value={draft} onChange={event => setDraft(event.target.value)} />
          <button type="submit" disabled={!draft.trim()} aria-label="Send question">➤</button>
        </form>
        <p className="chat-note">Instant preset answers only. Please don't share private information here.</p>
      </div>
    </section>}
    <aside className="floating-actions" aria-label="Quick actions">
      <button type="button" className="floating-message" aria-label={chatOpen ? 'Close FAQ chat' : 'Open FAQ chat'} title="FAQ chat" aria-expanded={chatOpen} onClick={() => setChatOpen(value => !value)}>
        <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round"><path d="M20 11.5a7.8 7.8 0 0 1-8 7.5 9 9 0 0 1-4-.9L3.5 20l1.2-4.3A7.4 7.4 0 0 1 4 11.5 7.8 7.8 0 0 1 12 4a7.8 7.8 0 0 1 8 7.5Z"/><path d="M8.5 11.5h7"/></svg>
        <span className="floating-label">Ask Iraseth</span>
      </button>
      <button type="button" className="floating-cart" onClick={cart.open} aria-label={`Open My Order (${count} items)`} title="My Order">
        <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round"><circle cx="9" cy="20" r="1"/><circle cx="19" cy="20" r="1"/><path d="M2 3h2l2.7 12.2a2 2 0 0 0 2 1.6h9.5a2 2 0 0 0 2-1.6L22 7H5"/></svg>
        <span className="floating-label">My Order</span>
        {count > 0 && <span className="floating-count" aria-hidden="true">{count > 99 ? '99+' : count}</span>}
      </button>
    </aside>
  </div>;
}
